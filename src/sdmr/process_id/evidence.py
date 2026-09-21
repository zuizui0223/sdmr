"""Occurrence-only paired process challenges for SDMR v3."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from ..process_information_closure import process_information_closure
from .hgb_profiles import get_hgb_profile
from .known_truth.worlds import KnownTruthWorld
from .states import apply_identical_closure_abstention, classify_process_state


@dataclass(frozen=True)
class OccurrenceProcessEvaluation:
    evidence: pd.DataFrame
    states: pd.DataFrame


def _balanced_log_score(y_true, probability):
    y = np.asarray(y_true, dtype=int)
    p = np.clip(np.asarray(probability, dtype=float), 1e-9, 1.0 - 1e-9)
    positive = y == 1
    negative = y == 0
    if not positive.any() or not negative.any():
        return float("nan")
    pos_score = float(np.mean(np.log(p[positive])))
    neg_score = float(np.mean(np.log1p(-p[negative])))
    return 0.5 * (pos_score + neg_score)


def _sem(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) >= 2:
        return float(np.std(x, ddof=1) / np.sqrt(len(x)))
    if len(x) == 1:
        return 0.0
    return float("nan")


def _hgb_balanced_sample_weight(y_train):
    """Balance class prior while preserving ordinary empirical loss scale."""
    y = np.asarray(y_train, dtype=int)
    n = int(len(y))
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    if n <= 0 or n_pos <= 0 or n_neg <= 0:
        raise ValueError("HGB balanced weights require both classes")
    return np.where(
        y == 1,
        n / (2.0 * n_pos),
        n / (2.0 * n_neg),
    )


def _finite_split_indices(sample, spatial_groups, *, n_splits, split_mode):
    """Return deterministic finite-sample CV indices.

    random_cell splits unique cell IDs rather than records, so duplicated
    resamples from one cell never appear in both train and test.
    """

    mode = str(split_mode)
    if mode not in {"spatial", "random_cell"}:
        raise ValueError("split_mode must be spatial or random_cell")
    if "cell_id" not in sample.columns:
        raise KeyError("sample missing cell_id")
    groups = np.asarray(spatial_groups)
    if len(groups) != len(sample):
        raise ValueError("spatial_groups must align with sample rows")
    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")

    if mode == "spatial":
        if len(np.unique(groups)) < int(n_splits):
            raise ValueError("insufficient spatial groups for occurrence challenge")
        splitter = GroupKFold(n_splits=int(n_splits))
        return list(
            splitter.split(
                np.arange(len(sample)),
                sample["label"].to_numpy(int),
                groups=groups,
            )
        )

    cell_ids = pd.to_numeric(sample["cell_id"], errors="raise").to_numpy(int)
    unique_cells = np.unique(cell_ids)
    if len(unique_cells) < int(n_splits):
        raise ValueError("insufficient unique cells for random_cell split")
    splitter = KFold(n_splits=int(n_splits), shuffle=True, random_state=0)
    splits = []
    for train_cell_idx, test_cell_idx in splitter.split(unique_cells):
        train_cells = set(unique_cells[train_cell_idx].tolist())
        test_cells = set(unique_cells[test_cell_idx].tolist())
        if train_cells & test_cells:
            raise AssertionError("random_cell split leaked cell IDs")
        train_idx = np.flatnonzero(np.isin(cell_ids, list(train_cells)))
        test_idx = np.flatnonzero(np.isin(cell_ids, list(test_cells)))
        splits.append((train_idx, test_idx))
    return splits


def _fit_probabilities(
    train, test, predictors, *, C, learner="linear", hgb_profile="current"
):
    """Fit one declared finite learner and return train/test probabilities."""

    if not predictors:
        return (
            np.full(len(train), np.nan, dtype=float),
            np.full(len(test), np.nan, dtype=float),
        )
    y_train = train["label"].to_numpy(int)
    y_test = test["label"].to_numpy(int)
    if len(np.unique(y_train)) != 2 or len(np.unique(y_test)) != 2:
        return (
            np.full(len(train), np.nan, dtype=float),
            np.full(len(test), np.nan, dtype=float),
        )
    x_train = train.loc[:, list(predictors)].apply(
        pd.to_numeric, errors="coerce"
    ).to_numpy(float)
    x_test = test.loc[:, list(predictors)].apply(
        pd.to_numeric, errors="coerce"
    ).to_numpy(float)
    if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
        return (
            np.full(len(train), np.nan, dtype=float),
            np.full(len(test), np.nan, dtype=float),
        )
    learner = str(learner)
    if learner not in {"linear", "quadratic", "hgb"}:
        raise ValueError("learner must be linear, quadratic, or hgb")
    hgb_profile = str(hgb_profile)
    if learner == "hgb":
        hgb_params = get_hgb_profile(hgb_profile)
    else:
        if hgb_profile != "current":
            raise ValueError("hgb_profile may only be changed for learner=hgb")
        hgb_params = None
    logistic = LogisticRegression(
        C=float(C),
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        random_state=0,
        class_weight="balanced",
    )
    if learner == "linear":
        model = logistic
        model.fit(x_train, y_train)
    elif learner == "quadratic":
        model = make_pipeline(
            PolynomialFeatures(degree=2, include_bias=False),
            StandardScaler(),
            logistic,
        )
        model.fit(x_train, y_train)
    else:
        model = HistGradientBoostingClassifier(
            loss="log_loss",
            random_state=0,
            **hgb_params,
        )
        model.fit(
            x_train,
            y_train,
            sample_weight=_hgb_balanced_sample_weight(y_train),
        )
    train_probability = np.asarray(model.predict_proba(x_train)[:, 1], dtype=float)
    test_probability = np.asarray(model.predict_proba(x_test)[:, 1], dtype=float)
    return train_probability, test_probability


def _fit_score(
    train, test, predictors, *, C, learner="linear", hgb_profile="current"
):
    _, probability = _fit_probabilities(
        train,
        test,
        predictors,
        C=C,
        learner=learner,
        hgb_profile=hgb_profile,
    )
    if not np.isfinite(probability).all():
        return float("nan")
    return _balanced_log_score(test["label"].to_numpy(int), probability)

def evaluate_occurrence_processes(
    world: KnownTruthWorld,
    *,
    n_splits: int = 5,
    margin: float = 0.01,
    adequacy_floor: float = -0.75,
    sem_multiplier: float = 1.0,
    C: float = 1.0,
    learner: str = "linear",
    split_mode: str = "spatial",
    hgb_profile: str = "current",
) -> OccurrenceProcessEvaluation:
    """Fit matched full/knockout occurrence models and classify each process.

    The score is a balanced presence/background Bernoulli log score used only
    as a relative density-ratio discrimination criterion. It is not an
    absolute occurrence-probability estimand.
    """

    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")
    if float(C) <= 0 or not math.isfinite(float(C)):
        raise ValueError("C must be finite and positive")
    split_mode = str(split_mode)
    if split_mode not in {"spatial", "random_cell"}:
        raise ValueError("split_mode must be spatial or random_cell")
    learner = str(learner)
    if learner not in {"linear", "quadratic", "hgb"}:
        raise ValueError("learner must be linear, quadratic, or hgb")
    hgb_profile = str(hgb_profile)
    if learner == "hgb":
        get_hgb_profile(hgb_profile)
    elif hgb_profile != "current":
        raise ValueError("hgb_profile may only be changed for learner=hgb")
    route_label = {
        "linear": "logistic",
        "quadratic": "logistic_quadratic",
        "hgb": "hgb",
    }[learner]

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
    split_indices = _finite_split_indices(
        sample,
        groups.to_numpy(),
        n_splits=int(n_splits),
        split_mode=split_mode,
    )
    full_predictors = tuple(world.predictor_universe)
    rows = []

    for fold, (train_idx, test_idx) in enumerate(split_indices):
        train = sample.iloc[train_idx].reset_index(drop=True)
        test = sample.iloc[test_idx].reset_index(drop=True)
        full_score = _fit_score(
            train, test, full_predictors, C=C, learner=learner, hgb_profile=hgb_profile
        )
        for process in world.process_universe:
            excluded = process_information_closure(world.process_registry, process)
            excluded_set = set(excluded)
            retained = tuple(p for p in full_predictors if p not in excluded_set)
            knockout_score = _fit_score(
                train, test, retained, C=C, learner=learner, hgb_profile=hgb_profile
            )
            complete = bool(np.isfinite(full_score) and np.isfinite(knockout_score))
            rows.append({
                "process": process,
                "fold": int(fold),
                "route": route_label,
                "split_mode": split_mode,
                "hgb_profile": hgb_profile if learner == "hgb" else "",
                "complete": complete,
                "full_log_score": float(full_score),
                "knockout_log_score": float(knockout_score),
                "delta": float(full_score - knockout_score) if complete else float("nan"),
                "excluded_predictors": ",".join(excluded),
                "retained_predictors": ",".join(retained),
            })

    evidence = pd.DataFrame(rows)
    state_rows = []
    for process in world.process_universe:
        group = evidence.loc[evidence["process"].eq(process)].copy()
        complete = bool(len(group) == int(n_splits) and group["complete"].astype(bool).all())
        if complete:
            full_mean = float(group["full_log_score"].mean())
            knockout_mean = float(group["knockout_log_score"].mean())
            delta_mean = float(group["delta"].mean())
            delta_sem = _sem(group["delta"].to_numpy(float))
        else:
            full_mean = float("nan")
            knockout_mean = float("nan")
            delta_mean = float("nan")
            delta_sem = float("nan")

        route_evidence = pd.DataFrame([
            {
                "route": route_label,
                "complete": complete,
                "full_adequate": bool(complete and full_mean >= float(adequacy_floor)),
                "knockout_adequate": bool(complete and knockout_mean >= float(adequacy_floor)),
                "delta_mean": delta_mean,
                "delta_sem": delta_sem,
            }
        ])
        state = classify_process_state(
            route_evidence,
            margin=float(margin),
            adequacy_floor=float(adequacy_floor),
            sem_multiplier=float(sem_multiplier),
        )
        reason = "interval_process_challenge"
        if process in set(world.observation_unresolved_processes):
            state = "unresolved"
            reason = "observation_process_not_separable"
        closure = process_information_closure(world.process_registry, process)
        state_rows.append({
            "process": process,
            "state": state,
            "reason": reason,
            "split_mode": split_mode,
            "hgb_profile": hgb_profile if learner == "hgb" else "",
            "closure_predictors": ",".join(closure),
            "complete": complete,
            "full_log_score": full_mean,
            "knockout_log_score": knockout_mean,
            "delta_mean": delta_mean,
            "delta_sem": delta_sem,
        })

    states = apply_identical_closure_abstention(pd.DataFrame(state_rows))
    return OccurrenceProcessEvaluation(
        evidence=evidence.reset_index(drop=True),
        states=states.reset_index(drop=True),
    )
