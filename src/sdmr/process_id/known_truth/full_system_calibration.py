"""SDMR v4 full-system information-gate calibration.

This module calibrates only whether the complete declared predictor system
contains finite-sample information above the equal-prior null. It never opens
process knockouts and never changes process-state definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..evidence import _finite_split_indices, _fit_score
from .worlds import KnownTruthWorld


NULL_BALANCED_LOG_SCORE = -math.log(2.0)

INFORMATIVE_CONTROL_WORLDS = (
    "unique_process",
    "redundant_representation",
    "shared_carrier",
    "null_correlated",
    "interaction",
    "geographic_shift",
)

REPORT_ONLY_WORLD = "observation_confounded"
NULL_WORLD = "omitted_driver"

REQUIRED_CALIBRATION_WORLDS = (
    *INFORMATIVE_CONTROL_WORLDS,
    REPORT_ONLY_WORLD,
    NULL_WORLD,
)


@dataclass(frozen=True)
class FullSystemInformationEvaluation:
    fold_scores: pd.DataFrame
    summary: pd.DataFrame


@dataclass(frozen=True)
class InformationMultiplierDecision:
    passed: bool
    selected_multiplier: float | None
    eligible_multipliers: tuple[float, ...]
    candidate_summary: pd.DataFrame


def _sem(values) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) >= 2:
        return float(np.std(x, ddof=1) / np.sqrt(len(x)))
    if len(x) == 1:
        return 0.0
    return float("nan")


def summarize_information_folds(
    fold_scores: pd.DataFrame,
    *,
    adequacy_floor: float = -0.75,
) -> pd.DataFrame:
    """Summarize complete-system held-out scores against the equal-prior null."""

    if not isinstance(fold_scores, pd.DataFrame) or fold_scores.empty:
        raise ValueError("fold_scores must be a non-empty DataFrame")
    required = {"fold", "full_log_score"}
    missing = sorted(required - set(fold_scores.columns))
    if missing:
        raise KeyError(f"fold_scores missing columns: {missing}")
    if fold_scores["fold"].duplicated().any():
        raise ValueError("fold_scores must contain one row per fold")

    scores = pd.to_numeric(
        fold_scores["full_log_score"], errors="coerce"
    ).to_numpy(float)
    if not np.isfinite(scores).all():
        raise ValueError("full_log_score values must be finite")
    adequacy_floor = float(adequacy_floor)
    if not math.isfinite(adequacy_floor):
        raise ValueError("adequacy_floor must be finite")

    gains = scores - NULL_BALANCED_LOG_SCORE
    mean_full = float(np.mean(scores))
    mean_gain = float(np.mean(gains))
    gain_sem = _sem(gains)

    return pd.DataFrame(
        [
            {
                "n_folds": int(len(scores)),
                "mean_full_score": mean_full,
                "mean_gain_over_null": mean_gain,
                "gain_sem": gain_sem,
                "absolute_adequate": bool(mean_full >= adequacy_floor),
                "adequacy_floor": adequacy_floor,
                "null_balanced_log_score": NULL_BALANCED_LOG_SCORE,
            }
        ]
    )


def _sample_and_groups(
    world: KnownTruthWorld,
) -> tuple[pd.DataFrame, np.ndarray]:
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
        raise ValueError(
            "sample cell ids are not aligned with world spatial groups"
        )
    return sample, groups.to_numpy()


def evaluate_full_system_information(
    world: KnownTruthWorld,
    *,
    n_splits: int = 3,
    split_mode: str = "random_cell",
    learner: str = "hgb",
    hgb_profile: str = "shallow3",
    C: float = 1.0,
    adequacy_floor: float = -0.75,
) -> FullSystemInformationEvaluation:
    """Evaluate held-out information in the complete declared predictor system."""

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
    rows: list[dict[str, object]] = []

    for fold, (train_idx, test_idx) in enumerate(splits):
        train = sample.iloc[train_idx].reset_index(drop=True)
        test = sample.iloc[test_idx].reset_index(drop=True)
        score = _fit_score(
            train,
            test,
            predictors,
            C=float(C),
            learner=str(learner),
            hgb_profile=str(hgb_profile),
        )
        if not np.isfinite(score):
            raise ValueError(
                f"full-system score is non-finite in fold {fold}"
            )
        rows.append(
            {
                "fold": int(fold),
                "full_log_score": float(score),
                "gain_over_null": float(
                    score - NULL_BALANCED_LOG_SCORE
                ),
                "split_mode": split_mode,
                "learner": str(learner),
                "hgb_profile": (
                    str(hgb_profile) if str(learner) == "hgb" else ""
                ),
            }
        )

    fold_scores = pd.DataFrame(rows)
    summary = summarize_information_folds(
        fold_scores,
        adequacy_floor=float(adequacy_floor),
    )
    summary["split_mode"] = split_mode
    summary["learner"] = str(learner)
    summary["hgb_profile"] = (
        str(hgb_profile) if str(learner) == "hgb" else ""
    )
    return FullSystemInformationEvaluation(
        fold_scores=fold_scores,
        summary=summary,
    )


def evaluate_information_candidates(
    summary: pd.DataFrame,
    *,
    multipliers: Sequence[float],
) -> pd.DataFrame:
    """Expand full-system summaries over a frozen uncertainty-multiplier grid."""

    required = {
        "mean_full_score",
        "mean_gain_over_null",
        "gain_sem",
        "absolute_adequate",
    }
    missing = sorted(required - set(summary.columns))
    if missing:
        raise KeyError(f"summary missing columns: {missing}")
    if summary.empty:
        raise ValueError("summary must be non-empty")

    multiplier_tuple = tuple(float(x) for x in multipliers)
    if not multiplier_tuple:
        raise ValueError("multipliers must be non-empty")
    if len(set(multiplier_tuple)) != len(multiplier_tuple):
        raise ValueError("multipliers must be unique")
    if any((not math.isfinite(x)) or x < 0 for x in multiplier_tuple):
        raise ValueError("multipliers must be finite and non-negative")

    rows: list[dict[str, object]] = []
    for _, source in summary.iterrows():
        mean_gain = float(source["mean_gain_over_null"])
        gain_sem = float(source["gain_sem"])
        absolute_adequate = bool(source["absolute_adequate"])
        if not math.isfinite(mean_gain) or not math.isfinite(gain_sem):
            raise ValueError(
                "mean_gain_over_null and gain_sem must be finite"
            )
        base = source.to_dict()
        for multiplier in multiplier_tuple:
            lower_gain = mean_gain - multiplier * gain_sem
            row = dict(base)
            row.update(
                {
                    "multiplier": float(multiplier),
                    "lower_gain": float(lower_gain),
                    "authorized": bool(
                        absolute_adequate and lower_gain > 0.0
                    ),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def _validate_rate(value, *, name: str) -> float:
    x = float(value)
    if not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return x


def select_information_multiplier(
    world_rates: pd.DataFrame,
    *,
    candidate_order: Sequence[float],
    max_w7_false_authorization: float,
    min_informative_world_authorization: float,
) -> InformationMultiplierDecision:
    """Select the smallest predeclared multiplier satisfying null/power controls."""

    required = {"multiplier", "world", "authorization_rate"}
    missing = sorted(required - set(world_rates.columns))
    if missing:
        raise KeyError(f"world_rates missing columns: {missing}")
    if world_rates.empty:
        raise ValueError("world_rates must be non-empty")
    if world_rates.duplicated(["multiplier", "world"]).any():
        raise ValueError(
            "world_rates must contain one row per multiplier/world"
        )

    candidate_tuple = tuple(float(x) for x in candidate_order)
    if not candidate_tuple or len(set(candidate_tuple)) != len(candidate_tuple):
        raise ValueError(
            "candidate_order must be non-empty and unique"
        )
    max_null = _validate_rate(
        max_w7_false_authorization,
        name="max_w7_false_authorization",
    )
    min_info = _validate_rate(
        min_informative_world_authorization,
        name="min_informative_world_authorization",
    )

    observed_worlds = set(world_rates["world"].astype(str))
    missing_worlds = sorted(
        set(REQUIRED_CALIBRATION_WORLDS) - observed_worlds
    )
    if missing_worlds:
        raise ValueError(
            "required calibration worlds missing: "
            f"{missing_worlds}"
        )

    observed_candidates = set(
        pd.to_numeric(
            world_rates["multiplier"], errors="raise"
        ).astype(float)
    )
    if not set(candidate_tuple).issubset(observed_candidates):
        raise ValueError(
            "world_rates missing one or more candidate multipliers"
        )

    result_rows = []
    eligible: list[float] = []
    for candidate in candidate_tuple:
        subset = world_rates.loc[
            pd.to_numeric(
                world_rates["multiplier"], errors="raise"
            ).astype(float).eq(candidate)
        ].copy()
        rates = {
            str(row["world"]): _validate_rate(
                row["authorization_rate"],
                name=f"authorization_rate[{row['world']}]",
            )
            for _, row in subset.iterrows()
        }
        null_rate = rates[NULL_WORLD]
        informative_rates = [
            rates[world] for world in INFORMATIVE_CONTROL_WORLDS
        ]
        min_control_rate = float(min(informative_rates))
        qualifies = bool(
            null_rate <= max_null
            and min_control_rate >= min_info
        )
        if qualifies:
            eligible.append(float(candidate))
        result_rows.append(
            {
                "multiplier": float(candidate),
                "w7_false_authorization_rate": null_rate,
                "minimum_informative_control_rate": min_control_rate,
                "w6_report_only_authorization_rate": rates[
                    REPORT_ONLY_WORLD
                ],
                "eligible": qualifies,
            }
        )

    selected = eligible[0] if eligible else None
    return InformationMultiplierDecision(
        passed=selected is not None,
        selected_multiplier=selected,
        eligible_multipliers=tuple(eligible),
        candidate_summary=pd.DataFrame(result_rows),
    )
