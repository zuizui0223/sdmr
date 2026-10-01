"""Permutation-calibrated full-system information authorization for SDMR v5."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from ..evidence import (
    _balanced_log_score,
    _finite_split_indices,
    _fit_probabilities,
)
from .worlds import KnownTruthWorld


NULL_BALANCED_LOG_SCORE = -math.log(2.0)


@dataclass(frozen=True)
class FullSystemPermutationEvaluation:
    oof_predictions: pd.DataFrame
    fold_scores: pd.DataFrame
    summary: dict[str, object]


def _sample_and_groups(world: KnownTruthWorld) -> tuple[pd.DataFrame, np.ndarray]:
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
    return sample, groups.to_numpy()


def _validate_oof_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"fold", "label", "probability"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"OOF prediction table missing columns: {missing}")
    if frame.empty:
        raise ValueError("OOF prediction table must be non-empty")

    data = frame.copy(deep=True)
    data["fold"] = pd.to_numeric(data["fold"], errors="raise").astype(int)
    data["label"] = pd.to_numeric(data["label"], errors="raise").astype(int)
    if not set(data["label"].unique()).issubset({0, 1}):
        raise ValueError("OOF labels must be binary")
    probability = pd.to_numeric(
        data["probability"], errors="coerce"
    ).to_numpy(float)
    if not np.isfinite(probability).all():
        raise ValueError("OOF probabilities must be finite")
    if ((probability < 0.0) | (probability > 1.0)).any():
        raise ValueError("OOF probabilities must lie in [0, 1]")
    data["probability"] = probability

    for fold, group in data.groupby("fold", sort=True):
        if set(group["label"].unique()) != {0, 1}:
            raise ValueError(
                f"fold {fold} must contain both classes for balanced log score"
            )
    return data


def permute_labels_within_folds(
    frame: pd.DataFrame,
    *,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Permute held-out labels independently inside each fold."""

    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    data = _validate_oof_predictions(frame)
    out = data.copy(deep=True)
    for _, index in out.groupby("fold", sort=True).groups.items():
        labels = out.loc[index, "label"].to_numpy(int)
        out.loc[index, "label"] = rng.permutation(labels)
    return out


def _fold_balanced_scores(frame: pd.DataFrame) -> pd.DataFrame:
    data = _validate_oof_predictions(frame)
    rows: list[dict[str, object]] = []
    for fold, group in data.groupby("fold", sort=True):
        score = _balanced_log_score(
            group["label"].to_numpy(int),
            group["probability"].to_numpy(float),
        )
        if not math.isfinite(float(score)):
            raise ValueError(f"non-finite balanced log score in fold {fold}")
        rows.append(
            {
                "fold": int(fold),
                "balanced_log_score": float(score),
                "gain_over_null": float(score - NULL_BALANCED_LOG_SCORE),
                "n_rows": int(len(group)),
                "n_positive": int(group["label"].sum()),
                "n_negative": int((1 - group["label"]).sum()),
            }
        )
    return pd.DataFrame(rows)


def evaluate_permutation_statistic(
    oof_predictions: pd.DataFrame,
    *,
    n_permutations: int = 999,
    permutation_seed: int = 0,
) -> dict[str, object]:
    """Evaluate the conditional held-out label-permutation null."""

    data = _validate_oof_predictions(oof_predictions)
    n_permutations = int(n_permutations)
    if n_permutations < 1:
        raise ValueError("n_permutations must be >= 1")
    permutation_seed = int(permutation_seed)

    observed_folds = _fold_balanced_scores(data)
    observed_mean = float(observed_folds["balanced_log_score"].mean())
    observed_gain = float(observed_mean - NULL_BALANCED_LOG_SCORE)

    rng = np.random.default_rng(permutation_seed)
    null_statistics = np.empty(n_permutations, dtype=float)

    # Predictions stay fixed. Only held-out labels are permuted inside each fold.
    fold_parts = [
        (
            group["label"].to_numpy(int),
            group["probability"].to_numpy(float),
        )
        for _, group in data.groupby("fold", sort=True)
    ]

    for permutation_index in range(n_permutations):
        fold_scores = []
        for labels, probability in fold_parts:
            permuted_labels = rng.permutation(labels)
            fold_scores.append(
                _balanced_log_score(permuted_labels, probability)
            )
        null_statistics[permutation_index] = float(np.mean(fold_scores))

    exceedance_count = int(np.sum(null_statistics >= observed_mean))
    p_value = float((1 + exceedance_count) / (n_permutations + 1))

    return {
        "observed_mean_score": observed_mean,
        "mean_gain_over_null": observed_gain,
        "null_balanced_log_score": NULL_BALANCED_LOG_SCORE,
        "p_value": p_value,
        "exceedance_count": exceedance_count,
        "n_permutations": n_permutations,
        "permutation_seed": permutation_seed,
        "null_mean_score": float(np.mean(null_statistics)),
        "null_max_score": float(np.max(null_statistics)),
        "null_q99_score": float(np.quantile(null_statistics, 0.99)),
    }


def classify_full_system_permutation_gate(
    statistic: dict[str, object],
    *,
    adequacy_floor: float = -0.75,
    alpha: float = 0.001,
    minimum_gain_over_null: float = 0.0,
) -> dict[str, object]:
    """Apply the frozen permutation authorization conjunction.

    minimum_gain_over_null defaults to zero so SDMR v5 remains reproducible.
    SDMR v6 sets it to the existing process-information margin (0.01).
    """

    adequacy_floor = float(adequacy_floor)
    alpha = float(alpha)
    minimum_gain_over_null = float(minimum_gain_over_null)
    if not math.isfinite(adequacy_floor):
        raise ValueError("adequacy_floor must be finite")
    if not math.isfinite(alpha) or not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    if not math.isfinite(minimum_gain_over_null) or minimum_gain_over_null < 0.0:
        raise ValueError("minimum_gain_over_null must be finite and non-negative")

    required = {"observed_mean_score", "mean_gain_over_null", "p_value"}
    missing = sorted(required - set(statistic))
    if missing:
        raise KeyError(f"permutation statistic missing keys: {missing}")

    score = float(statistic["observed_mean_score"])
    gain = float(statistic["mean_gain_over_null"])
    p_value = float(statistic["p_value"])
    if not all(math.isfinite(x) for x in (score, gain, p_value)):
        raise ValueError("permutation gate statistics must be finite")
    if not 0.0 <= p_value <= 1.0:
        raise ValueError("p_value must be in [0, 1]")

    absolute_adequate = bool(score >= adequacy_floor)
    positive_gain = bool(gain > 0.0)
    minimum_gain_met = bool(gain >= minimum_gain_over_null)
    permutation_significant = bool(p_value <= alpha)
    authorized = bool(
        absolute_adequate
        and positive_gain
        and minimum_gain_met
        and permutation_significant
    )

    return {
        "authorized": authorized,
        "reason": (
            "full_system_information_authorized"
            if authorized
            else "full_system_not_informative"
        ),
        "absolute_adequate": absolute_adequate,
        "positive_gain": positive_gain,
        "minimum_gain_met": minimum_gain_met,
        "permutation_significant": permutation_significant,
        "adequacy_floor": adequacy_floor,
        "alpha": alpha,
        "minimum_gain_over_null": minimum_gain_over_null,
        "observed_mean_score": score,
        "mean_gain_over_null": gain,
        "p_value": p_value,
    }


def evaluate_full_system_permutation_gate(
    world: KnownTruthWorld,
    *,
    n_splits: int = 3,
    split_mode: str = "random_cell",
    learner: str = "hgb",
    hgb_profile: str = "shallow3",
    C: float = 1.0,
    adequacy_floor: float = -0.75,
    n_permutations: int = 999,
    alpha: float = 0.001,
    permutation_seed: int = 0,
    minimum_gain_over_null: float = 0.0,
) -> FullSystemPermutationEvaluation:
    """Fit the full system once per fold, then test held-out labels by permutation."""

    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")
    if not math.isfinite(float(C)) or float(C) <= 0:
        raise ValueError("C must be finite and positive")
    split_mode = str(split_mode)
    if split_mode not in {"spatial", "random_cell"}:
        raise ValueError("split_mode must be spatial or random_cell")

    sample, groups = _sample_and_groups(world)
    splits = _finite_split_indices(
        sample,
        groups,
        n_splits=int(n_splits),
        split_mode=split_mode,
    )
    predictors = tuple(world.predictor_universe)

    rows: list[pd.DataFrame] = []
    for fold, (train_index, test_index) in enumerate(splits):
        train = sample.iloc[train_index].reset_index(drop=True)
        test = sample.iloc[test_index].reset_index(drop=True)
        _, probability = _fit_probabilities(
            train,
            test,
            predictors,
            C=float(C),
            learner=str(learner),
            hgb_profile=str(hgb_profile),
        )
        if not np.isfinite(probability).all():
            raise ValueError(f"non-finite full-system prediction in fold {fold}")

        fold_frame = pd.DataFrame(
            {
                "fold": int(fold),
                "label": test["label"].to_numpy(int),
                "probability": probability,
                "cell_id": pd.to_numeric(
                    test["cell_id"], errors="raise"
                ).to_numpy(int),
            }
        )
        rows.append(fold_frame)

    oof_predictions = pd.concat(rows, ignore_index=True)
    fold_scores = _fold_balanced_scores(oof_predictions)
    statistic = evaluate_permutation_statistic(
        oof_predictions,
        n_permutations=int(n_permutations),
        permutation_seed=int(permutation_seed),
    )
    decision = classify_full_system_permutation_gate(
        statistic,
        adequacy_floor=float(adequacy_floor),
        alpha=float(alpha),
        minimum_gain_over_null=float(minimum_gain_over_null),
    )

    summary = {
        **statistic,
        **decision,
        "n_splits": int(n_splits),
        "split_mode": split_mode,
        "learner": str(learner),
        "hgb_profile": (
            str(hgb_profile) if str(learner) == "hgb" else ""
        ),
    }
    return FullSystemPermutationEvaluation(
        oof_predictions=oof_predictions,
        fold_scores=fold_scores,
        summary=summary,
    )
