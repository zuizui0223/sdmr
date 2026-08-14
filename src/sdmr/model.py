"""Model fitting helpers for relative-suitability SDMs.

The first implementation intentionally keeps the estimator family small. Product
A is about whether a tuning *procedure* transfers to sealed occurrences, so we
start with regularized logistic presence-vs-background models and tune both
regularization and response flexibility behind one reproducible interface.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from .metrics import boyce_index, presence_rank_score


@dataclass(frozen=True)
class ModelSpec:
    """A reproducible model-complexity and regularization setting.

    ``degree=1`` is a linear environmental response. ``degree=2`` adds squares
    and pairwise interactions, giving a deliberately simple analogue of a more
    flexible SDM response surface. ``C`` is inverse regularization strength.
    """

    C: float = 1.0
    degree: int = 1
    penalty: str = "l2"

    def __post_init__(self) -> None:
        if self.C <= 0:
            raise ValueError("C must be > 0.")
        if self.degree not in (1, 2):
            raise ValueError("degree must be 1 or 2.")
        if self.penalty not in {"l1", "l2"}:
            raise ValueError("penalty must be 'l1' or 'l2'.")

    @property
    def label(self) -> str:
        return f"logit_{self.penalty}_C{self.C:g}_degree{self.degree}"


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
    model = make_pipeline(
        PolynomialFeatures(degree=spec.degree, include_bias=False),
        StandardScaler(),
        LogisticRegression(
            C=spec.C,
            penalty=spec.penalty,
            solver="liblinear",
            class_weight="balanced",
            max_iter=4000,
        ),
    )
    model.fit(X, y)
    return model


def score_relative_suitability(
    model,
    frame: pd.DataFrame,
    predictors: Sequence[str],
) -> np.ndarray:
    """Return relative-suitability scores for complete rows; NaN otherwise."""

    cols = list(predictors)
    X = frame[cols]
    valid = X.notna().all(axis=1).to_numpy()
    scores = np.full(len(frame), np.nan, dtype=float)
    if np.any(valid):
        scores[valid] = model.predict_proba(X.loc[valid].to_numpy(float))[:, 1]
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
    """Fit on model rows and evaluate once on independent rows."""

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
        "n_test_presence": int(np.isfinite(p_scores).sum()),
        "n_test_background": int(np.isfinite(b_scores).sum()),
    }
