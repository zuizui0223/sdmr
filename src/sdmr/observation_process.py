"""Observation-process correction for ecological niche-recovery audits.

Presence records can be environmentally biased even after the fitted model's
observation covariates are marginalized from its ecological suitability surface.
The *held-out occurrence target* therefore also needs an observation-process
correction when explicit nuisance covariates are available.

The correction is candidate-independent. A separate classifier is fitted using
only the frozen observation-process covariates to distinguish training focal
records from training target-group background. With balanced class priors its
odds estimate a density ratio between focal-record and target-group observation
processes. Held-out focal records receive stabilized inverse-odds weights so their
nuisance-covariate distribution is transported toward the target-group reference.

No ecological predictor or candidate-model prediction enters these weights.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .model import ModelSpec, fit_relative_suitability_model, score_relative_suitability


@dataclass(frozen=True)
class ObservationWeightResult:
    weights: np.ndarray
    n_evaluation: int
    effective_sample_size: float
    maximum_normalized_weight: float
    truncation_cap: float


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

    When no observation predictors are declared the identity weights are returned.
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
