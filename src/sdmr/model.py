"""Model fitting helpers.

The default model is intentionally simple and regularized. The benchmark is
about predictor information and transferability, not winning with one specific
algorithm. More estimators can be added behind the same scoring interface.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .metrics import boyce_index, presence_rank_score


def fit_relative_suitability_model(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    predictors: Sequence[str],
):
    """Fit a regularized presence-vs-background relative suitability model."""

    if not predictors:
        raise ValueError("At least one predictor is required to fit a model.")
    cols = list(predictors)
    p = presence[cols].dropna()
    b = background[cols].dropna()
    if len(p) < 2 or len(b) < 2:
        raise ValueError("Not enough complete presence/background rows to fit model.")

    X = np.vstack((p.to_numpy(float), b.to_numpy(float)))
    y = np.concatenate((np.ones(len(p), dtype=int), np.zeros(len(b), dtype=int)))
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            solver="lbfgs",
            class_weight="balanced",
            max_iter=2000,
        ),
    )
    model.fit(X, y)
    return model


def score_relative_suitability(model, frame: pd.DataFrame, predictors: Sequence[str]) -> np.ndarray:
    """Return relative suitability scores for complete rows; NaN otherwise."""

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
) -> dict[str, float]:
    """Fit on training regions and evaluate on held-out regions."""

    model = fit_relative_suitability_model(train_presence, train_background, predictors)
    p_scores = score_relative_suitability(model, test_presence, predictors)
    b_scores = score_relative_suitability(model, test_background, predictors)
    return {
        "presence_rank": presence_rank_score(p_scores, b_scores),
        "boyce": boyce_index(p_scores, b_scores),
        "n_test_presence": int(np.isfinite(p_scores).sum()),
        "n_test_background": int(np.isfinite(b_scores).sum()),
    }
