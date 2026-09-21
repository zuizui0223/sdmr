"""Development-only probability-quality audit for finite SDMR learners."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ..evidence import (
    _balanced_log_score,
    _finite_split_indices,
    _fit_probabilities,
)
from .worlds import KnownTruthWorld, simulate_process_world


def probability_quality_metrics(y_true, probability) -> dict[str, float]:
    """Return balanced probability-quality and discrimination diagnostics."""

    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probability, dtype=float)
    if len(y) != len(p) or len(y) == 0:
        raise ValueError("labels and probability must be non-empty and aligned")
    if not np.isfinite(p).all() or ((p < 0.0) | (p > 1.0)).any():
        raise ValueError("probability values must be finite and in [0, 1]")
    positive = y == 1
    negative = y == 0
    if not positive.any() or not negative.any():
        raise ValueError("probability audit requires both classes")

    clipped = np.clip(p, 1e-9, 1.0 - 1e-9)
    balanced_brier = 0.5 * float(np.mean((1.0 - p[positive]) ** 2))
    balanced_brier += 0.5 * float(np.mean(p[negative] ** 2))
    quantiles = np.quantile(p, [0.01, 0.05, 0.50, 0.95, 0.99])
    return {
        "balanced_log_score": float(_balanced_log_score(y, clipped)),
        "roc_auc": float(roc_auc_score(y, p)),
        "balanced_brier": float(balanced_brier),
        "mean_p_positive": float(np.mean(p[positive])),
        "mean_p_negative": float(np.mean(p[negative])),
        "q01": float(quantiles[0]),
        "q05": float(quantiles[1]),
        "q50": float(quantiles[2]),
        "q95": float(quantiles[3]),
        "q99": float(quantiles[4]),
        "extreme_fraction": float(np.mean((p < 0.01) | (p > 0.99))),
    }


def _sample_and_groups(world: KnownTruthWorld) -> tuple[pd.DataFrame, np.ndarray]:
    occurrence = world.occurrences.copy()
    background = world.background.copy()
    occurrence["label"] = 1
    background["label"] = 0
    sample = pd.concat([occurrence, background], ignore_index=True)
    group_lookup = dict(
        zip(
            world.environment["cell_id"].astype(int),
            np.asarray(world.spatial_groups),
            strict=True,
        )
    )
    groups = sample["cell_id"].astype(int).map(group_lookup)
    if groups.isna().any():
        raise ValueError("sample cell ids are not aligned with world spatial groups")
    return sample, groups.to_numpy()


def audit_world_probability_quality(
    world: KnownTruthWorld,
    *,
    learners: Sequence[str] = ("linear", "hgb"),
    split_modes: Sequence[str] = ("spatial", "random_cell"),
    n_splits: int = 3,
    C: float = 1.0,
) -> pd.DataFrame:
    """Audit full-model train/test probability quality for one known-truth world."""

    learner_tuple = tuple(str(x) for x in learners)
    split_tuple = tuple(str(x) for x in split_modes)
    if not learner_tuple or len(set(learner_tuple)) != len(learner_tuple):
        raise ValueError("learners must be non-empty and unique")
    unknown_learners = sorted(set(learner_tuple) - {"linear", "quadratic", "hgb"})
    if unknown_learners:
        raise ValueError(f"unknown learners: {unknown_learners}")
    if not split_tuple or len(set(split_tuple)) != len(split_tuple):
        raise ValueError("split_modes must be non-empty and unique")
    unknown_splits = sorted(set(split_tuple) - {"spatial", "random_cell"})
    if unknown_splits:
        raise ValueError(f"unknown split modes: {unknown_splits}")

    sample, groups = _sample_and_groups(world)
    predictors = tuple(world.predictor_universe)
    rows: list[dict[str, object]] = []

    for split_mode in split_tuple:
        splits = _finite_split_indices(
            sample,
            groups,
            n_splits=int(n_splits),
            split_mode=split_mode,
        )
        for learner in learner_tuple:
            for fold, (train_idx, test_idx) in enumerate(splits):
                train = sample.iloc[train_idx].reset_index(drop=True)
                test = sample.iloc[test_idx].reset_index(drop=True)
                train_p, test_p = _fit_probabilities(
                    train,
                    test,
                    predictors,
                    C=float(C),
                    learner=learner,
                )
                train_metrics = probability_quality_metrics(
                    train["label"].to_numpy(int), train_p
                )
                test_metrics = probability_quality_metrics(
                    test["label"].to_numpy(int), test_p
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
                            "learner": learner,
                            "split_mode": split_mode,
                            "fold": int(fold),
                            "dataset": dataset,
                            "n_rows": int(len(train) if dataset == "train" else len(test)),
                            "train_test_log_score_gap": gap,
                            **metrics,
                        }
                    )
    return pd.DataFrame(rows)


def run_probability_quality_audit(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = (
        "unique_process",
        "interaction",
        "geographic_shift",
    ),
    learners: Sequence[str] = ("linear", "hgb"),
    split_modes: Sequence[str] = ("spatial", "random_cell"),
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
    C: float = 1.0,
) -> pd.DataFrame:
    """Run the burned-development probability-quality audit deterministically."""

    seed_tuple = tuple(int(x) for x in seeds)
    world_tuple = tuple(str(x) for x in worlds)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be non-empty and unique")
    allowed = {"unique_process", "interaction", "geographic_shift"}
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be non-empty and unique")
    unknown = sorted(set(world_tuple) - allowed)
    if unknown:
        raise ValueError(f"probability audit only supports ODO-positive worlds: {unknown}")

    frames: list[pd.DataFrame] = []
    for world_name in world_tuple:
        for seed in seed_tuple:
            world = simulate_process_world(
                world_name,
                seed=seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            frame = audit_world_probability_quality(
                world,
                learners=learners,
                split_modes=split_modes,
                n_splits=int(n_splits),
                C=float(C),
            )
            frame.insert(0, "seed", int(seed))
            frame.insert(0, "world", world_name)
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
