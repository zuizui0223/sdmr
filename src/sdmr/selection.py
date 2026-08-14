"""Nested spatial predictor selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .model import evaluate_predictor_set


@dataclass(frozen=True)
class SelectionStep:
    step: int
    predictor: str
    score: float
    gain: float


def _cross_validated_score(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    predictors: Sequence[str],
    *,
    n_splits: int,
) -> float:
    groups = np.unique(presence_groups)
    folds = min(int(n_splits), len(groups))
    if folds < 2:
        raise ValueError("At least two training spatial blocks are required for inner CV.")

    splitter = GroupKFold(n_splits=folds)
    scores: list[float] = []
    dummy = np.zeros(len(presence), dtype=int)
    for train_idx, test_idx in splitter.split(dummy, groups=presence_groups):
        train_blocks = np.unique(presence_groups[train_idx])
        test_blocks = np.unique(presence_groups[test_idx])
        bg_train = np.isin(background_groups, train_blocks)
        bg_test = np.isin(background_groups, test_blocks)
        if bg_train.sum() < 2 or bg_test.sum() < 2:
            continue
        try:
            metrics = evaluate_predictor_set(
                presence.iloc[train_idx],
                background.loc[bg_train],
                presence.iloc[test_idx],
                background.loc[bg_test],
                predictors,
            )
        except ValueError:
            continue
        if np.isfinite(metrics["presence_rank"]):
            scores.append(float(metrics["presence_rank"]))
    if not scores:
        return float("nan")
    return float(np.mean(scores))


def forward_select_predictors(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    candidate_predictors: Sequence[str],
    *,
    inner_folds: int = 4,
    min_gain: float = 0.005,
    max_predictors: int | None = 8,
) -> tuple[list[str], list[SelectionStep], pd.DataFrame]:
    """Greedily select predictors using only inner spatial CV.

    No outer-holdout score is inspected while selecting variables. Each step
    adds the candidate that most improves mean held-out presence rank across
    inner spatial folds. Correlated variables are allowed to compete rather
    than being deleted up front by a VIF threshold.
    """

    candidates = list(dict.fromkeys(candidate_predictors))
    missing = [c for c in candidates if c not in presence or c not in background]
    if missing:
        raise KeyError(f"Missing predictor columns: {missing}")
    if not candidates:
        raise ValueError("No candidate predictors supplied.")

    selected: list[str] = []
    trace: list[SelectionStep] = []
    candidate_rows: list[dict[str, float | int | str]] = []
    current_score = 0.5
    limit = len(candidates) if max_predictors is None else min(max_predictors, len(candidates))

    for step in range(1, limit + 1):
        best_predictor: str | None = None
        best_score = float("-inf")
        for predictor in candidates:
            if predictor in selected:
                continue
            test_set = selected + [predictor]
            score = _cross_validated_score(
                presence,
                background,
                presence_groups,
                background_groups,
                test_set,
                n_splits=inner_folds,
            )
            gain = score - current_score if np.isfinite(score) else float("nan")
            candidate_rows.append(
                {
                    "step": step,
                    "predictor": predictor,
                    "score": score,
                    "gain_vs_current": gain,
                }
            )
            if np.isfinite(score) and score > best_score:
                best_score = score
                best_predictor = predictor

        if best_predictor is None:
            break
        gain = best_score - current_score
        if step > 1 and gain < min_gain:
            break
        selected.append(best_predictor)
        trace.append(SelectionStep(step, best_predictor, best_score, gain))
        current_score = best_score

    if not selected:
        raise ValueError("No predictor could be evaluated in inner spatial CV.")

    return selected, trace, pd.DataFrame(candidate_rows)
