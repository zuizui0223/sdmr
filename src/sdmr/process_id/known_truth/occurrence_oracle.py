"""Occurrence-distribution identifiability oracle for SDMR v3 known truth."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold, KFold

from ...process_information_closure import process_information_closure
from ..states import apply_identical_closure_abstention, classify_process_state
from .worlds import KnownTruthWorld


@dataclass(frozen=True)
class OccurrenceDistribution:
    q_occurrence: np.ndarray
    q_background: np.ndarray
    posterior: np.ndarray
    mixture: np.ndarray


@dataclass(frozen=True)
class OccurrenceOracleEvaluation:
    evidence: pd.DataFrame
    states: pd.DataFrame


def _sem(values) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) >= 2:
        return float(np.std(x, ddof=1) / np.sqrt(len(x)))
    if len(x) == 1:
        return 0.0
    return float("nan")


def occurrence_distribution_components(world: KnownTruthWorld) -> OccurrenceDistribution:
    """Return exact focal-occurrence and background cell distributions."""

    env = world.environment
    for column in ("true_suitability", "sampling_effort"):
        if column not in env.columns:
            raise KeyError(f"world environment missing {column!r}")
    suitability = pd.to_numeric(env["true_suitability"], errors="coerce").to_numpy(float)
    effort = pd.to_numeric(env["sampling_effort"], errors="coerce").to_numpy(float)
    if not np.isfinite(suitability).all() or not np.isfinite(effort).all():
        raise ValueError("suitability and effort must be finite")
    if (suitability < 0).any() or (effort <= 0).any():
        raise ValueError("suitability must be non-negative and effort strictly positive")
    q1 = suitability * effort
    q0 = effort.copy()
    if float(q1.sum()) <= 0 or float(q0.sum()) <= 0:
        raise ValueError("occurrence/background distribution mass must be positive")
    q1 = q1 / float(q1.sum())
    q0 = q0 / float(q0.sum())
    denominator = q1 + q0
    posterior = q1 / denominator
    mixture = 0.5 * denominator
    return OccurrenceDistribution(
        q_occurrence=q1,
        q_background=q0,
        posterior=posterior,
        mixture=mixture,
    )


def _conditional_components(q1, q0, indices):
    q1_part = np.asarray(q1, dtype=float)[indices].copy()
    q0_part = np.asarray(q0, dtype=float)[indices].copy()
    if float(q1_part.sum()) <= 0 or float(q0_part.sum()) <= 0:
        raise ValueError("spatial fold has zero class mass")
    q1_part /= float(q1_part.sum())
    q0_part /= float(q0_part.sum())
    posterior = q1_part / (q1_part + q0_part)
    mixture = 0.5 * (q1_part + q0_part)
    return q1_part, q0_part, posterior, mixture


def _fit_posterior(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: np.ndarray,
    weights: np.ndarray,
    predictors: tuple[str, ...],
    *,
    max_iter: int,
    max_leaf_nodes: int,
    min_samples_leaf: int,
    learning_rate: float,
    l2_regularization: float,
) -> np.ndarray:
    if not predictors:
        constant = float(np.average(target, weights=weights))
        return np.full(len(test), np.clip(constant, 1e-6, 1.0 - 1e-6))
    x_train = train.loc[:, list(predictors)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    x_test = test.loc[:, list(predictors)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
        raise ValueError("oracle predictors must be finite")
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=float(learning_rate),
        max_iter=int(max_iter),
        max_leaf_nodes=int(max_leaf_nodes),
        min_samples_leaf=int(min_samples_leaf),
        l2_regularization=float(l2_regularization),
        early_stopping=False,
        random_state=0,
    )
    scale = max(float(len(train)), 1.0) / float(np.sum(weights))
    model.fit(x_train, target, sample_weight=weights * scale)
    pred = np.asarray(model.predict(x_test), dtype=float)
    return np.clip(pred, 1e-6, 1.0 - 1e-6)


def _balanced_expected_log_score(q1, q0, probability) -> float:
    p = np.clip(np.asarray(probability, dtype=float), 1e-6, 1.0 - 1e-6)
    return float(
        0.5 * np.sum(np.asarray(q1, dtype=float) * np.log(p))
        + 0.5 * np.sum(np.asarray(q0, dtype=float) * np.log1p(-p))
    )


def evaluate_occurrence_oracle_states(
    world: KnownTruthWorld,
    *,
    n_splits: int = 5,
    margin: float = 0.01,
    sem_multiplier: float = 1.0,
    adequacy_floor: float = -0.75,
    approximation_tolerance: float = 0.01,
    max_iter: int = 250,
    max_leaf_nodes: int = 31,
    min_samples_leaf: int = 20,
    learning_rate: float = 0.08,
    l2_regularization: float = 1e-3,
    split_mode: str = "spatial",
) -> OccurrenceOracleEvaluation:
    """Evaluate process identifiability in the complete observation distribution."""

    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")
    for value, name in (
        (margin, "margin"),
        (sem_multiplier, "sem_multiplier"),
        (approximation_tolerance, "approximation_tolerance"),
    ):
        if not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if not math.isfinite(float(adequacy_floor)):
        raise ValueError("adequacy_floor must be finite")
    split_mode = str(split_mode)
    if split_mode not in {"spatial", "random"}:
        raise ValueError("split_mode must be spatial or random")

    distribution = occurrence_distribution_components(world)
    groups = np.asarray(world.spatial_groups)
    if len(groups) != len(world.environment):
        raise ValueError("spatial_groups must align with environment rows")
    if len(np.unique(groups)) < int(n_splits):
        raise ValueError("insufficient spatial groups for occurrence oracle")

    index = np.arange(len(world.environment))
    if split_mode == "spatial":
        splitter = GroupKFold(n_splits=int(n_splits))
        split_indices = splitter.split(index, groups=groups)
    else:
        splitter = KFold(n_splits=int(n_splits), shuffle=True, random_state=0)
        split_indices = splitter.split(index)

    full_predictors = tuple(world.predictor_universe)
    rows: list[dict[str, object]] = []

    for fold, (train_idx, test_idx) in enumerate(split_indices):
        train = world.environment.iloc[train_idx].reset_index(drop=True)
        test = world.environment.iloc[test_idx].reset_index(drop=True)
        q1_train, q0_train, posterior_train, mixture_train = _conditional_components(
            distribution.q_occurrence, distribution.q_background, train_idx
        )
        q1_test, q0_test, posterior_test, _ = _conditional_components(
            distribution.q_occurrence, distribution.q_background, test_idx
        )
        bayes_score = _balanced_expected_log_score(q1_test, q0_test, posterior_test)
        full_pred = _fit_posterior(
            train, test, posterior_train, mixture_train, full_predictors,
            max_iter=max_iter, max_leaf_nodes=max_leaf_nodes,
            min_samples_leaf=min_samples_leaf, learning_rate=learning_rate,
            l2_regularization=l2_regularization,
        )
        full_score = _balanced_expected_log_score(q1_test, q0_test, full_pred)
        full_regret = float(max(bayes_score - full_score, 0.0))

        for process in world.process_universe:
            closure = process_information_closure(world.process_registry, process)
            excluded = set(closure)
            retained = tuple(p for p in full_predictors if p not in excluded)
            reduced_pred = _fit_posterior(
                train, test, posterior_train, mixture_train, retained,
                max_iter=max_iter, max_leaf_nodes=max_leaf_nodes,
                min_samples_leaf=min_samples_leaf, learning_rate=learning_rate,
                l2_regularization=l2_regularization,
            )
            reduced_score = _balanced_expected_log_score(q1_test, q0_test, reduced_pred)
            rows.append({
                "fold": int(fold),
                "split_mode": split_mode,
                "process": str(process),
                "complete": True,
                "bayes_score": bayes_score,
                "full_score": full_score,
                "process_free_score": reduced_score,
                "delta": float(full_score - reduced_score),
                "full_regret": full_regret,
                "closure_predictors": ",".join(closure),
                "retained_predictors": ",".join(retained),
            })

    evidence = pd.DataFrame(rows)
    state_rows: list[dict[str, object]] = []
    for process in world.process_universe:
        group = evidence.loc[evidence["process"].eq(process)].copy()
        complete = bool(
            len(group) == int(n_splits)
            and group["complete"].astype(bool).all()
            and np.isfinite(group[["bayes_score", "full_score", "process_free_score", "delta", "full_regret"]].to_numpy(float)).all()
        )
        if complete:
            mean_bayes = float(group["bayes_score"].mean())
            mean_full = float(group["full_score"].mean())
            mean_reduced = float(group["process_free_score"].mean())
            mean_delta = float(group["delta"].mean())
            delta_sem = _sem(group["delta"].to_numpy(float))
            mean_regret = float(group["full_regret"].mean())
            regret_sem = _sem(group["full_regret"].to_numpy(float))
            upper_regret = mean_regret + float(sem_multiplier) * regret_sem
            full_adequate = bool(upper_regret <= float(approximation_tolerance))
        else:
            mean_bayes = mean_full = mean_reduced = float("nan")
            mean_delta = delta_sem = mean_regret = regret_sem = upper_regret = float("nan")
            full_adequate = False

        route_evidence = pd.DataFrame([{
            "route": "occurrence_distribution_oracle",
            "complete": complete,
            "full_adequate": full_adequate,
            "knockout_adequate": bool(complete and mean_reduced >= float(adequacy_floor)),
            "delta_mean": mean_delta,
            "delta_sem": delta_sem,
        }])
        state = classify_process_state(
            route_evidence,
            margin=float(margin),
            adequacy_floor=float(adequacy_floor),
            sem_multiplier=float(sem_multiplier),
        )
        reason = (
            "occurrence_distribution_oracle"
            if state != "unavailable"
            else "full_oracle_regret_exceeds_tolerance"
        )
        closure = process_information_closure(world.process_registry, process)
        state_rows.append({
            "process": str(process),
            "state": state,
            "reason": reason,
            "closure_predictors": ",".join(closure),
            "complete": complete,
            "mean_bayes_score": mean_bayes,
            "mean_full_score": mean_full,
            "mean_process_free_score": mean_reduced,
            "mean_delta": mean_delta,
            "delta_sem": delta_sem,
            "lower_delta": mean_delta - float(sem_multiplier) * delta_sem if complete else float("nan"),
            "upper_delta": mean_delta + float(sem_multiplier) * delta_sem if complete else float("nan"),
            "mean_full_regret": mean_regret,
            "full_regret_sem": regret_sem,
            "upper_full_regret": upper_regret,
            "full_numerically_adequate": full_adequate,
        })

    states = apply_identical_closure_abstention(pd.DataFrame(state_rows))
    unresolved = set(world.observation_unresolved_processes)
    if unresolved:
        mask = states["process"].astype(str).isin(unresolved)
        states.loc[mask, "state"] = "unresolved"
        states.loc[mask, "reason"] = "observation_process_not_separable"
    return OccurrenceOracleEvaluation(
        evidence=evidence.reset_index(drop=True),
        states=states.reset_index(drop=True),
    )
