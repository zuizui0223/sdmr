"""Model fitting helpers for relative-suitability SDMs.

Product A separates two model outputs when explicit observation-process
covariates are present:

- the full observation-aware score is used to evaluate whether records transfer;
- the ecological score marginalizes declared observation-process covariates and
  is used for niche interpretation/recovery.

This keeps sampling/detectability structure from being silently interpreted as an
environmental niche driver.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import inspect

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from .metrics import boyce_index, continuous_boyce_index, presence_rank_score


@dataclass(frozen=True)
class ModelSpec:
    """A reproducible model-complexity and regularization setting.

    ``degree=1`` is a linear environmental response. ``degree=2`` adds squares
    and pairwise interactions, giving a deliberately simple analogue of a more
    flexible SDM response surface. ``C`` is inverse regularization strength.

    ``random_state`` is optional so historical frozen Product-A versions retain
    their original estimator identity when it is omitted. Successor contracts
    that require process-independent reproducibility must set it explicitly.
    """

    C: float = 1.0
    degree: int = 1
    penalty: str = "l2"
    random_state: int | None = None

    def __post_init__(self) -> None:
        if self.C <= 0:
            raise ValueError("C must be > 0.")
        if self.degree not in (1, 2):
            raise ValueError("degree must be 1 or 2.")
        if self.penalty not in {"l1", "l2"}:
            raise ValueError("penalty must be 'l1' or 'l2'.")
        if self.random_state is not None and not isinstance(self.random_state, (int, np.integer)):
            raise TypeError("random_state must be an integer or None.")

    @property
    def label(self) -> str:
        base = f"logit_{self.penalty}_C{self.C:g}_degree{self.degree}"
        if self.random_state is None:
            return base
        return f"{base}_rs{int(self.random_state)}"


def fit_relative_suitability_model(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    predictors: Sequence[str],
    *,
    model_spec: ModelSpec | None = None,
):
    """Fit a regularized presence-vs-background relative-suitability model."""

    if not predictors:
        raise ValueError("At least one predictor is required to fit a model.")

    spec = model_spec or ModelSpec()
    cols = list(predictors)
    p = presence[cols].dropna()
    b = background[cols].dropna()
    if len(p) < 2 or len(b) < 2:
        raise ValueError("Not enough complete presence/background rows to fit model.")

    X = np.vstack((p.to_numpy(float), b.to_numpy(float)))
    y = np.concatenate((np.ones(len(p), dtype=int), np.zeros(len(b), dtype=int)))
    logit_kwargs = {
        "C": spec.C,
        "solver": "liblinear",
        "class_weight": "balanced",
        "max_iter": 4000,
        "random_state": spec.random_state,
    }
    penalty_default = inspect.signature(LogisticRegression).parameters["penalty"].default
    if penalty_default == "deprecated":
        logit_kwargs["l1_ratio"] = 1.0 if spec.penalty == "l1" else 0.0
    else:
        logit_kwargs["penalty"] = spec.penalty

    model = make_pipeline(
        PolynomialFeatures(degree=spec.degree, include_bias=False),
        StandardScaler(),
        LogisticRegression(**logit_kwargs),
    )
    model.fit(X, y)
    return model


def score_relative_suitability(
    model,
    frame: pd.DataFrame,
    predictors: Sequence[str],
) -> np.ndarray:
    """Return full observation-aware relative-suitability scores."""

    cols = list(predictors)
    X = frame[cols]
    valid = X.notna().all(axis=1).to_numpy()
    scores = np.full(len(frame), np.nan, dtype=float)
    if np.any(valid):
        scores[valid] = model.predict_proba(X.loc[valid].to_numpy(float))[:, 1]
    return scores


def score_ecological_suitability(
    model,
    frame: pd.DataFrame,
    predictors: Sequence[str],
    *,
    observation_predictors: Sequence[str] = (),
    observation_reference: pd.DataFrame | None = None,
    max_reference_rows: int = 64,
) -> np.ndarray:
    """Return suitability after marginalizing declared observation covariates.

    Declared observation-process variables may be used during fitting because
    they can absorb sampling/detectability structure. They are not allowed to
    define the ecological niche surface. For each evaluation environment this
    function therefore averages model predictions over a deterministic sample of
    observation-covariate combinations from ``observation_reference`` (a partial-
    dependence/marginal prediction).

    Environmental predictors retain the row-specific values from ``frame``.
    Interactions with observation variables are automatically marginalized because
    predictions are recomputed through the full fitted pipeline for every
    reference combination.

    If no observation predictors are declared, this is exactly
    :func:`score_relative_suitability`.
    """

    cols = list(predictors)
    if not cols:
        raise ValueError("predictors must not be empty")
    observation = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    unknown = sorted(set(observation) - set(cols))
    if unknown:
        raise ValueError(f"observation predictors are not in model predictors: {unknown}")
    if not observation:
        return score_relative_suitability(model, frame, cols)
    if observation_reference is None:
        raise ValueError("observation_reference is required when observation predictors are declared")
    if max_reference_rows < 1:
        raise ValueError("max_reference_rows must be >= 1")

    ecological = [c for c in cols if c not in observation]
    missing_ecological = sorted(set(ecological) - set(frame.columns))
    missing_observation = sorted(set(observation) - set(observation_reference.columns))
    if missing_ecological:
        raise KeyError(f"evaluation frame missing ecological predictors: {missing_ecological}")
    if missing_observation:
        raise KeyError(f"observation reference missing predictors: {missing_observation}")

    if ecological:
        ecological_values = frame[ecological].apply(pd.to_numeric, errors="coerce")
        valid = ecological_values.notna().all(axis=1).to_numpy()
    else:
        ecological_values = pd.DataFrame(index=frame.index)
        valid = np.ones(len(frame), dtype=bool)
    scores = np.full(len(frame), np.nan, dtype=float)
    if not np.any(valid):
        return scores

    reference = observation_reference[list(observation)].apply(pd.to_numeric, errors="coerce").dropna()
    if reference.empty:
        return scores
    n_ref = min(int(max_reference_rows), len(reference))
    if n_ref < len(reference):
        idx = np.unique(np.rint(np.linspace(0, len(reference) - 1, n_ref)).astype(int))
        reference = reference.iloc[idx]

    valid_index = np.flatnonzero(valid)
    ecological_arrays = {
        col: pd.to_numeric(frame.loc[valid, col], errors="coerce").to_numpy(float)
        for col in ecological
    }
    accumulated = np.zeros(len(valid_index), dtype=float)
    n_predictions = 0
    for _, ref_row in reference.iterrows():
        X = np.empty((len(valid_index), len(cols)), dtype=float)
        for j, col in enumerate(cols):
            if col in observation:
                X[:, j] = float(ref_row[col])
            else:
                X[:, j] = ecological_arrays[col]
        prediction = model.predict_proba(X)[:, 1]
        if np.isfinite(prediction).all():
            accumulated += prediction
            n_predictions += 1
    if n_predictions:
        scores[valid_index] = accumulated / n_predictions
    return scores


def evaluate_predictor_set(
    train_presence: pd.DataFrame,
    train_background: pd.DataFrame,
    test_presence: pd.DataFrame,
    test_background: pd.DataFrame,
    predictors: Sequence[str],
    *,
    model_spec: ModelSpec | None = None,
) -> dict[str, float]:
    """Fit on model rows and evaluate once on independent rows.

    This legacy/v1 helper remains observation-score only. Product-A v2 ecological
    recovery uses the explicit role-aware scoring path in ``niche_recovery_cv``.
    """

    model = fit_relative_suitability_model(
        train_presence,
        train_background,
        predictors,
        model_spec=model_spec,
    )
    p_scores = score_relative_suitability(model, test_presence, predictors)
    b_scores = score_relative_suitability(model, test_background, predictors)
    return {
        "presence_rank": presence_rank_score(p_scores, b_scores),
        "boyce": boyce_index(p_scores, b_scores),
        "continuous_boyce": continuous_boyce_index(p_scores, b_scores),
        "n_test_presence": int(np.isfinite(p_scores).sum()),
        "n_test_background": int(np.isfinite(b_scores).sum()),
    }
