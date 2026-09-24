"""Full-system information adequacy gate for finite SDMR inference."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from ..evidence import _balanced_log_score, _finite_split_indices, _fit_score, _sem
from .worlds import KnownTruthWorld


@dataclass(frozen=True)
class FullSystemInformationEvaluation:
    fold_scores: pd.DataFrame
    summary: dict[str, object]


def summarize_full_system_gain(
    full_scores,
    *,
    sem_multiplier: float = 1.0,
    adequacy_floor: float = -0.75,
) -> dict[str, object]:
    """Summarize full-model information above the equal-prior null."""

    scores = np.asarray(full_scores, dtype=float)
    if scores.ndim != 1 or len(scores) == 0 or not np.isfinite(scores).all():
        raise ValueError("full_scores must be a non-empty finite vector")
    sem_multiplier = float(sem_multiplier)
    adequacy_floor = float(adequacy_floor)
    if not math.isfinite(sem_multiplier) or sem_multiplier < 0:
        raise ValueError("sem_multiplier must be finite and non-negative")
    if not math.isfinite(adequacy_floor):
        raise ValueError("adequacy_floor must be finite")

    null_score = -math.log(2.0)
    gains = scores - null_score
    mean_score = float(np.mean(scores))
    mean_gain = float(np.mean(gains))
    gain_sem = float(_sem(gains))
    lower_gain = mean_gain - sem_multiplier * gain_sem

    absolute_adequate = bool(mean_score >= adequacy_floor)
    information_adequate = bool(lower_gain > 0.0)
    return {
        "null_score": float(null_score),
        "mean_full_log_score": mean_score,
        "mean_gain_over_null": mean_gain,
        "gain_sem": gain_sem,
        "lower_gain_over_null": float(lower_gain),
        "absolute_adequate": absolute_adequate,
        "information_adequate": information_adequate,
        "full_system_adequate": bool(absolute_adequate and information_adequate),
    }


def evaluate_full_system_information(
    world: KnownTruthWorld,
    *,
    n_splits: int = 3,
    learner: str = "hgb",
    hgb_profile: str = "shallow3",
    split_mode: str = "random_cell",
    C: float = 1.0,
    sem_multiplier: float = 1.0,
    adequacy_floor: float = -0.75,
) -> FullSystemInformationEvaluation:
    """Evaluate held-out information carried by the complete declared predictor system."""

    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")
    split_mode = str(split_mode)
    if split_mode not in {"spatial", "random_cell"}:
        raise ValueError("split_mode must be spatial or random_cell")

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

    splits = _finite_split_indices(
        sample,
        groups.to_numpy(),
        n_splits=int(n_splits),
        split_mode=split_mode,
    )
    predictors = tuple(world.predictor_universe)
    rows = []
    for fold, (train_idx, test_idx) in enumerate(splits):
        train = sample.iloc[train_idx].reset_index(drop=True)
        test = sample.iloc[test_idx].reset_index(drop=True)
        full_score = _fit_score(
            train,
            test,
            predictors,
            C=float(C),
            learner=str(learner),
            hgb_profile=str(hgb_profile),
        )
        y_test = test["label"].to_numpy(int)
        null_probability = np.full(len(test), 0.5, dtype=float)
        null_score = _balanced_log_score(y_test, null_probability)
        rows.append(
            {
                "fold": int(fold),
                "split_mode": split_mode,
                "learner": str(learner),
                "hgb_profile": str(hgb_profile) if str(learner) == "hgb" else "",
                "full_log_score": float(full_score),
                "null_log_score": float(null_score),
                "gain_over_null": float(full_score - null_score),
            }
        )

    fold_scores = pd.DataFrame(rows)
    summary = summarize_full_system_gain(
        fold_scores["full_log_score"].to_numpy(float),
        sem_multiplier=float(sem_multiplier),
        adequacy_floor=float(adequacy_floor),
    )
    summary.update(
        {
            "split_mode": split_mode,
            "learner": str(learner),
            "hgb_profile": str(hgb_profile) if str(learner) == "hgb" else "",
            "n_splits": int(n_splits),
        }
    )
    return FullSystemInformationEvaluation(
        fold_scores=fold_scores,
        summary=summary,
    )
