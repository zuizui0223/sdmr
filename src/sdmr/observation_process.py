"""Observation-process diagnostics and correction for niche-recovery audits.

Presence records can be environmentally biased even after the fitted model's
observation covariates are marginalized from its ecological suitability surface.
The held-out occurrence target can therefore require an observation-process
correction too. But correction must not be switched on merely because a nuisance
column exists: finite-sample noise in an irrelevant observation covariate can
itself distort the ecological target.

This module therefore separates two candidate-independent operations:

1. **training-only spatial evidence gate** — using only the frozen observation
   covariates, ask whether focal records can be distinguished from target-group
   background in held-out training spatial blocks above random ranking;
2. **inverse density-ratio correction** — only when that gate is active, fit the
   nuisance model on training focal/background rows and transport held-out focal
   records toward the target-group observation reference with stabilized inverse
   odds.

No ecological predictor, candidate-model prediction, or hidden ecological truth
enters either operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import presence_rank_score
from .model import ModelSpec, fit_relative_suitability_model, score_relative_suitability


@dataclass(frozen=True)
class ObservationSignalEvidence:
    correction_active: bool
    mean_auc: float
    sem_auc: float
    lower_evidence_bound: float
    auc_gate_floor: float
    chance_auc: float
    n_folds: int


@dataclass(frozen=True)
class ObservationWeightResult:
    weights: np.ndarray
    n_evaluation: int
    effective_sample_size: float
    maximum_normalized_weight: float
    truncation_cap: float


def observation_process_signal_evidence(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: Sequence[int] | np.ndarray,
    background_groups: Sequence[int] | np.ndarray,
    observation_predictors: Sequence[str],
    *,
    n_splits: int = 3,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    model_spec: ModelSpec | None = None,
) -> ObservationSignalEvidence:
    """Decide from training-only spatial CV whether nuisance correction is needed.

    A correction is activated only when the observation-only classifier satisfies
    both of the same interpretable adequacy conditions used elsewhere in Product A:

    - mean held-out AUC >= ``chance_auc + minimum_auc_margin``; and
    - mean AUC - ``auc_sem_multiplier`` × SEM >= ``chance_auc``.

    For presence/background ranking, 0.5 is the random-ranking reference. The
    +0.01 default margin is an operational development guardrail, not a biological
    effect-size threshold.

    If no observation predictors are declared, the gate is explicitly inactive
    and returns the random-ranking reference rather than fitting a model.
    """

    chance_auc = float(chance_auc)
    minimum_auc_margin = float(minimum_auc_margin)
    auc_sem_multiplier = float(auc_sem_multiplier)
    if not 0 <= chance_auc < 1:
        raise ValueError("chance_auc must lie in [0, 1)")
    if minimum_auc_margin < 0 or chance_auc + minimum_auc_margin > 1:
        raise ValueError("minimum_auc_margin must keep the AUC floor in [0, 1]")
    if auc_sem_multiplier < 0:
        raise ValueError("auc_sem_multiplier must be >= 0")

    predictors = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    floor = chance_auc + minimum_auc_margin
    if not predictors:
        return ObservationSignalEvidence(
            correction_active=False,
            mean_auc=chance_auc,
            sem_auc=0.0,
            lower_evidence_bound=chance_auc,
            auc_gate_floor=floor,
            chance_auc=chance_auc,
            n_folds=0,
        )

    required = set(predictors)
    for label, frame in (("presence", presence), ("background", background)):
        missing = required - set(frame.columns)
        if missing:
            raise KeyError(f"{label} missing observation predictors: {sorted(missing)}")

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("observation-process group arrays must align with rows")
    unique_groups = np.unique(p_groups)
    folds = min(int(n_splits), len(unique_groups))
    if folds < 2:
        raise ValueError("at least two training spatial blocks are required for observation evidence")

    spec = model_spec or ModelSpec(C=1.0, degree=1, penalty="l2")
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    auc_values: list[float] = []
    for train_idx, test_idx in splitter.split(dummy, groups=p_groups):
        train_blocks = np.unique(p_groups[train_idx])
        test_blocks = np.unique(p_groups[test_idx])
        b_train_mask = np.isin(b_groups, train_blocks)
        b_test_mask = np.isin(b_groups, test_blocks)
        if b_train_mask.sum() < 5 or b_test_mask.sum() < 5 or len(test_idx) < 2:
            continue
        try:
            nuisance_model = fit_relative_suitability_model(
                presence.iloc[train_idx].reset_index(drop=True),
                background.loc[b_train_mask].reset_index(drop=True),
                predictors,
                model_spec=spec,
            )
            p_scores = score_relative_suitability(
                nuisance_model,
                presence.iloc[test_idx].reset_index(drop=True),
                predictors,
            )
            b_scores = score_relative_suitability(
                nuisance_model,
                background.loc[b_test_mask].reset_index(drop=True),
                predictors,
            )
            auc = presence_rank_score(p_scores, b_scores)
        except (ValueError, np.linalg.LinAlgError):
            continue
        if np.isfinite(auc):
            auc_values.append(float(auc))

    if not auc_values:
        raise ValueError("observation-process CV produced no finite held-out AUC")
    values = np.asarray(auc_values, dtype=float)
    mean_auc = float(values.mean())
    sem_auc = (
        float(values.std(ddof=1) / np.sqrt(len(values)))
        if len(values) >= 2
        else 0.0
    )
    lower = mean_auc - auc_sem_multiplier * sem_auc
    active = bool(mean_auc >= floor - 1e-12 and lower >= chance_auc - 1e-12)
    return ObservationSignalEvidence(
        correction_active=active,
        mean_auc=mean_auc,
        sem_auc=sem_auc,
        lower_evidence_bound=lower,
        auc_gate_floor=floor,
        chance_auc=chance_auc,
        n_folds=int(len(values)),
    )


def _inverse_odds(probability: np.ndarray, *, epsilon: float) -> np.ndarray:
    p = np.asarray(probability, dtype=float)
    p = np.clip(p, float(epsilon), 1.0 - float(epsilon))
    return (1.0 - p) / p


def inverse_observation_propensity_weights(
    train_presence: pd.DataFrame,
    train_background: pd.DataFrame,
    evaluation_presence: pd.DataFrame,
    observation_predictors: Sequence[str],
    *,
    model_spec: ModelSpec | None = None,
    truncation_quantile: float = 0.99,
    probability_epsilon: float = 1e-4,
) -> ObservationWeightResult:
    """Return candidate-independent weights for held-out occurrence environments.

    The nuisance classifier is fitted only on training rows. The truncation cap is
    also estimated from training focal records, never from the held-out target.
    Weights are finally normalized to mean one over finite evaluation records.

    When no observation predictors are supplied, identity weights are returned;
    callers use this path when the training-only observation-signal gate is
    inactive.
    """

    predictors = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    if not 0 < float(truncation_quantile) <= 1:
        raise ValueError("truncation_quantile must lie in (0, 1]")
    if not 0 < float(probability_epsilon) < 0.5:
        raise ValueError("probability_epsilon must lie in (0, 0.5)")
    if not predictors:
        weights = np.ones(len(evaluation_presence), dtype=float)
        return ObservationWeightResult(
            weights=weights,
            n_evaluation=len(weights),
            effective_sample_size=float(len(weights)),
            maximum_normalized_weight=1.0 if len(weights) else float("nan"),
            truncation_cap=1.0,
        )

    required = set(predictors)
    for label, frame in (
        ("train_presence", train_presence),
        ("train_background", train_background),
        ("evaluation_presence", evaluation_presence),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise KeyError(f"{label} missing observation predictors: {sorted(missing)}")

    spec = model_spec or ModelSpec(C=1.0, degree=1, penalty="l2")
    model = fit_relative_suitability_model(
        train_presence,
        train_background,
        predictors,
        model_spec=spec,
    )
    train_scores = score_relative_suitability(model, train_presence, predictors)
    evaluation_scores = score_relative_suitability(model, evaluation_presence, predictors)

    train_inverse = _inverse_odds(train_scores, epsilon=probability_epsilon)
    train_inverse = train_inverse[np.isfinite(train_inverse) & (train_inverse > 0)]
    if not len(train_inverse):
        raise ValueError("observation propensity model produced no finite training weights")
    cap = float(np.quantile(train_inverse, float(truncation_quantile)))
    if not np.isfinite(cap) or cap <= 0:
        raise ValueError("observation propensity truncation cap is invalid")

    raw = _inverse_odds(evaluation_scores, epsilon=probability_epsilon)
    valid = np.isfinite(raw) & (raw > 0)
    weights = np.full(len(evaluation_presence), np.nan, dtype=float)
    if not np.any(valid):
        raise ValueError("observation propensity model produced no finite evaluation weights")
    clipped = np.minimum(raw[valid], cap)
    mean = float(np.mean(clipped))
    if not mean > 0:
        raise ValueError("observation propensity weights have non-positive mean")
    clipped = clipped / mean
    weights[valid] = clipped
    ess = float((clipped.sum() ** 2) / np.sum(clipped**2)) if np.sum(clipped**2) > 0 else 0.0
    return ObservationWeightResult(
        weights=weights,
        n_evaluation=int(np.sum(valid)),
        effective_sample_size=ess,
        maximum_normalized_weight=float(np.max(clipped)),
        truncation_cap=cap,
    )
