"""Out-of-sample predictor importance for the ecological synthesis layer."""

from __future__ import annotations
from collections.abc import Sequence
import pandas as pd
from .model import ModelSpec, evaluate_predictor_set


def drop_one_importance(
    train_presence: pd.DataFrame,
    train_background: pd.DataFrame,
    test_presence: pd.DataFrame,
    test_background: pd.DataFrame,
    predictors: Sequence[str],
    *,
    model_spec: ModelSpec | None = None,
) -> pd.DataFrame:
    """Measure necessity as sealed performance loss after removing one raster."""
    predictors = list(predictors)
    if not predictors:
        return pd.DataFrame(columns=["predictor", "full_presence_rank", "drop_presence_rank", "loss"])
    full_score = float(evaluate_predictor_set(
        train_presence, train_background, test_presence, test_background,
        predictors, model_spec=model_spec,
    )["presence_rank"])
    rows = []
    for predictor in predictors:
        reduced = [p for p in predictors if p != predictor]
        reduced_score = 0.5 if not reduced else float(evaluate_predictor_set(
            train_presence, train_background, test_presence, test_background,
            reduced, model_spec=model_spec,
        )["presence_rank"])
        rows.append({
            "predictor": predictor,
            "full_presence_rank": full_score,
            "drop_presence_rank": reduced_score,
            "loss": full_score - reduced_score,
        })
    return pd.DataFrame(rows).sort_values("loss", ascending=False, kind="mergesort").reset_index(drop=True)
