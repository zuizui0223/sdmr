"""Exploratory HGB regularization screen using probability quality only."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from ..evidence import (
    _finite_split_indices,
    _hgb_balanced_sample_weight,
)
from .probability_audit import (
    _sample_and_groups,
    probability_quality_metrics,
)
from .worlds import simulate_process_world


HGB_PROFILES = {
    "current": {
        "learning_rate": 0.08,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 20,
        "l2_regularization": 1e-3,
        "early_stopping": False,
    },
    "shallow7": {
        "learning_rate": 0.05,
        "max_iter": 100,
        "max_leaf_nodes": 7,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "early_stopping": False,
    },
    "shallow3": {
        "learning_rate": 0.05,
        "max_iter": 100,
        "max_leaf_nodes": 3,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "early_stopping": False,
    },
    "early7": {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 7,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "early_stopping": True,
        "validation_fraction": 0.2,
        "n_iter_no_change": 10,
    },
}


def _fit_profile(train, test, predictors, *, profile: str):
    profile = str(profile)
    if profile not in HGB_PROFILES:
        raise ValueError(f"unknown HGB profile: {profile!r}")
    y_train = train["label"].to_numpy(int)
    y_test = test["label"].to_numpy(int)
    if len(np.unique(y_train)) != 2 or len(np.unique(y_test)) != 2:
        raise ValueError("HGB screen requires both classes in train and test")
    x_train = train.loc[:, list(predictors)].apply(
        pd.to_numeric, errors="coerce"
    ).to_numpy(float)
    x_test = test.loc[:, list(predictors)].apply(
        pd.to_numeric, errors="coerce"
    ).to_numpy(float)
    if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
        raise ValueError("HGB screen predictors must be finite")

    model = HistGradientBoostingClassifier(
        loss="log_loss",
        random_state=0,
        **HGB_PROFILES[profile],
    )
    model.fit(
        x_train,
        y_train,
        sample_weight=_hgb_balanced_sample_weight(y_train),
    )
    return (
        np.asarray(model.predict_proba(x_train)[:, 1], dtype=float),
        np.asarray(model.predict_proba(x_test)[:, 1], dtype=float),
    )


def run_hgb_regularization_screen(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = (
        "unique_process",
        "interaction",
        "geographic_shift",
    ),
    split_modes: Sequence[str] = ("spatial", "random_cell"),
    profiles: Sequence[str] = tuple(HGB_PROFILES),
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
) -> pd.DataFrame:
    """Run the burned-development HGB probability-quality screen."""

    seed_tuple = tuple(int(x) for x in seeds)
    world_tuple = tuple(str(x) for x in worlds)
    split_tuple = tuple(str(x) for x in split_modes)
    profile_tuple = tuple(str(x) for x in profiles)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be non-empty and unique")
    allowed_worlds = {"unique_process", "interaction", "geographic_shift"}
    unknown_worlds = sorted(set(world_tuple) - allowed_worlds)
    if not world_tuple or unknown_worlds:
        raise ValueError(f"invalid screen worlds: {unknown_worlds}")
    if len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be unique")
    unknown_splits = sorted(set(split_tuple) - {"spatial", "random_cell"})
    if not split_tuple or unknown_splits:
        raise ValueError(f"invalid split modes: {unknown_splits}")
    if len(set(split_tuple)) != len(split_tuple):
        raise ValueError("split_modes must be unique")
    unknown_profiles = sorted(set(profile_tuple) - set(HGB_PROFILES))
    if not profile_tuple or unknown_profiles:
        raise ValueError(f"invalid HGB profiles: {unknown_profiles}")
    if len(set(profile_tuple)) != len(profile_tuple):
        raise ValueError("profiles must be unique")

    rows: list[dict[str, object]] = []
    for world_name in world_tuple:
        for seed in seed_tuple:
            world = simulate_process_world(
                world_name,
                seed=seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            sample, groups = _sample_and_groups(world)
            predictors = tuple(world.predictor_universe)
            for split_mode in split_tuple:
                splits = _finite_split_indices(
                    sample,
                    groups,
                    n_splits=int(n_splits),
                    split_mode=split_mode,
                )
                for profile in profile_tuple:
                    for fold, (train_idx, test_idx) in enumerate(splits):
                        train = sample.iloc[train_idx].reset_index(drop=True)
                        test = sample.iloc[test_idx].reset_index(drop=True)
                        train_p, test_p = _fit_profile(
                            train,
                            test,
                            predictors,
                            profile=profile,
                        )
                        train_metrics = probability_quality_metrics(
                            train["label"].to_numpy(int),
                            train_p,
                        )
                        test_metrics = probability_quality_metrics(
                            test["label"].to_numpy(int),
                            test_p,
                        )
                        gap = (
                            float(train_metrics["balanced_log_score"])
                            - float(test_metrics["balanced_log_score"])
                        )
                        for dataset, metrics in (
                            ("train", train_metrics),
                            ("test", test_metrics),
                        ):
                            rows.append(
                                {
                                    "world": world_name,
                                    "seed": int(seed),
                                    "split_mode": split_mode,
                                    "profile": profile,
                                    "fold": int(fold),
                                    "dataset": dataset,
                                    "train_test_log_score_gap": gap,
                                    **metrics,
                                }
                            )
    return pd.DataFrame(rows)


def select_hgb_profile(
    rows: pd.DataFrame,
    *,
    adequacy_floor: float = -0.75,
    tie_margin: float = 0.005,
) -> dict[str, object]:
    """Select an HGB profile without consulting any process-recovery outcome."""

    required = {"profile", "world", "split_mode", "dataset", "balanced_log_score"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"HGB screen rows missing columns: {missing}")
    if float(tie_margin) < 0:
        raise ValueError("tie_margin must be non-negative")
    test = rows.loc[rows["dataset"].astype(str).eq("test")].copy()
    if test.empty:
        raise ValueError("HGB screen requires test rows")

    world_split = (
        test.groupby(["profile", "world", "split_mode"], sort=True)[
            "balanced_log_score"
        ]
        .mean()
        .reset_index()
    )
    profile_scores = (
        test.groupby("profile", sort=True)["balanced_log_score"]
        .mean()
        .to_dict()
    )
    eligible = []
    for profile, group in world_split.groupby("profile", sort=True):
        if bool((group["balanced_log_score"] >= float(adequacy_floor)).all()):
            eligible.append(str(profile))
    if not eligible:
        return {
            "selected_profile": None,
            "eligible_profiles": tuple(),
            "profile_scores": {str(k): float(v) for k, v in profile_scores.items()},
        }

    best_score = max(float(profile_scores[p]) for p in eligible)
    tied = [
        p for p in eligible
        if best_score - float(profile_scores[p]) < float(tie_margin)
    ]
    selected = min(
        tied,
        key=lambda p: (
            int(HGB_PROFILES[p]["max_leaf_nodes"]),
            int(HGB_PROFILES[p]["max_iter"]),
            p,
        ),
    )
    return {
        "selected_profile": selected,
        "eligible_profiles": tuple(eligible),
        "profile_scores": {str(k): float(v) for k, v in profile_scores.items()},
    }
