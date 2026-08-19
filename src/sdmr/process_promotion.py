"""Explicit promotion gate for universal plant niche-process claims.

Discovery stability nominates process hypotheses. Unseen-taxon validation then
confirms or rejects those predeclared hypotheses. Validation failures are never
used to prune and re-promote a new core on the same data.
"""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class UniversalProcessPromotionCriteria:
    min_core_stability: float
    min_splits_selected: int
    min_mean_validation_process_drop: float
    min_positive_validation_drop_fraction: float
    min_validation_drop_pairs: int
    min_validation_drop_splits: int
    min_mean_core_minus_full: float
    min_core_validation_pairs: int
    min_core_validation_splits: int
    min_mean_core_minus_random: float
    min_positive_core_vs_random_fraction: float
    min_core_vs_random_pairs: int
    min_core_vs_random_splits: int

    def __post_init__(self):
        for name in ("min_core_stability", "min_positive_validation_drop_fraction", "min_positive_core_vs_random_fraction"):
            value = float(getattr(self, name))
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        for name in (
            "min_splits_selected",
            "min_validation_drop_pairs",
            "min_validation_drop_splits",
            "min_core_validation_pairs",
            "min_core_validation_splits",
            "min_core_vs_random_pairs",
            "min_core_vs_random_splits",
        ):
            if int(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be >= 1")


@dataclass
class UniversalProcessPromotionAssessment:
    promoted_core: bool
    process_evidence: pd.DataFrame
    core_transfer_evidence: pd.DataFrame
    core_random_evidence: pd.DataFrame
    validated_process_candidates: pd.DataFrame
    failures: list[str]


def _require(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise KeyError(f"{name} missing columns: {sorted(missing)}")


def assess_universal_process_promotion(
    process_stability: pd.DataFrame,
    validation_comparison: pd.DataFrame,
    core_vs_random: pd.DataFrame,
    criteria: UniversalProcessPromotionCriteria,
) -> UniversalProcessPromotionAssessment:
    """Assess predeclared universal-process and core-level promotion criteria."""
    _require(
        process_stability,
        {
            "process",
            "splits_selected",
            "n_splits",
            "core_stability",
            "validation_drop_pairs",
            "validation_drop_splits",
            "mean_validation_process_drop",
            "positive_validation_drop_fraction",
        },
        "process_stability",
    )
    _require(
        validation_comparison,
        {"species", "split_id", "core_minus_full_presence_rank"},
        "validation_comparison",
    )
    _require(
        core_vs_random,
        {"species", "split_id", "repeat", "core_minus_random_presence_rank"},
        "core_vs_random",
    )

    evidence = process_stability.copy()
    evidence["candidate_by_discovery"] = (
        (evidence["core_stability"] >= criteria.min_core_stability)
        & (evidence["splits_selected"] >= criteria.min_splits_selected)
    )
    evidence["necessity_pass"] = (
        (evidence["validation_drop_pairs"] >= criteria.min_validation_drop_pairs)
        & (evidence["validation_drop_splits"] >= criteria.min_validation_drop_splits)
        & (evidence["mean_validation_process_drop"] >= criteria.min_mean_validation_process_drop)
        & (evidence["positive_validation_drop_fraction"] >= criteria.min_positive_validation_drop_fraction)
    )
    evidence["independently_validated_process"] = evidence["candidate_by_discovery"] & evidence["necessity_pass"]

    failures: list[str] = []
    candidates = evidence.loc[evidence["candidate_by_discovery"]].copy()
    if not len(candidates):
        failures.append("no process met the predeclared discovery-stability nomination rule")
    else:
        for row in candidates.itertuples(index=False):
            process = str(row.process)
            if int(row.validation_drop_pairs) < criteria.min_validation_drop_pairs:
                failures.append(f"process={process} validation_drop_pairs below threshold")
            if int(row.validation_drop_splits) < criteria.min_validation_drop_splits:
                failures.append(f"process={process} validation_drop_splits below threshold")
            if float(row.mean_validation_process_drop) < criteria.min_mean_validation_process_drop:
                failures.append(f"process={process} mean unseen-taxon process-drop below threshold")
            if float(row.positive_validation_drop_fraction) < criteria.min_positive_validation_drop_fraction:
                failures.append(f"process={process} positive unseen-taxon process-drop fraction below threshold")

    core_pairs = int(len(validation_comparison))
    core_splits = int(validation_comparison["split_id"].nunique())
    mean_core_minus_full = float(validation_comparison["core_minus_full_presence_rank"].mean()) if core_pairs else float("nan")
    median_core_minus_full = float(validation_comparison["core_minus_full_presence_rank"].median()) if core_pairs else float("nan")
    core_transfer_pass = (
        core_pairs >= criteria.min_core_validation_pairs
        and core_splits >= criteria.min_core_validation_splits
        and mean_core_minus_full >= criteria.min_mean_core_minus_full
    )
    core_transfer = pd.DataFrame([
        {
            "n_pairs": core_pairs,
            "n_splits": core_splits,
            "mean_core_minus_full_presence_rank": mean_core_minus_full,
            "median_core_minus_full_presence_rank": median_core_minus_full,
            "passes": core_transfer_pass,
        }
    ])
    if core_pairs < criteria.min_core_validation_pairs:
        failures.append("core-vs-full validation pairs below threshold")
    if core_splits < criteria.min_core_validation_splits:
        failures.append("core-vs-full validation splits below threshold")
    if not pd.isna(mean_core_minus_full) and mean_core_minus_full < criteria.min_mean_core_minus_full:
        failures.append("mean core-minus-full unseen-taxon performance below threshold")
    elif pd.isna(mean_core_minus_full):
        failures.append("core-vs-full unseen-taxon performance unavailable")

    random_pairs = int(len(core_vs_random))
    random_splits = int(core_vs_random["split_id"].nunique())
    mean_core_minus_random = float(core_vs_random["core_minus_random_presence_rank"].mean()) if random_pairs else float("nan")
    median_core_minus_random = float(core_vs_random["core_minus_random_presence_rank"].median()) if random_pairs else float("nan")
    positive_random = float((core_vs_random["core_minus_random_presence_rank"] > 0).mean()) if random_pairs else float("nan")
    core_random_pass = (
        random_pairs >= criteria.min_core_vs_random_pairs
        and random_splits >= criteria.min_core_vs_random_splits
        and mean_core_minus_random >= criteria.min_mean_core_minus_random
        and positive_random >= criteria.min_positive_core_vs_random_fraction
    )
    core_random = pd.DataFrame([
        {
            "n_pairs": random_pairs,
            "n_splits": random_splits,
            "mean_core_minus_random_presence_rank": mean_core_minus_random,
            "median_core_minus_random_presence_rank": median_core_minus_random,
            "positive_core_vs_random_fraction": positive_random,
            "passes": core_random_pass,
        }
    ])
    if random_pairs < criteria.min_core_vs_random_pairs:
        failures.append("core-vs-random pairs below threshold")
    if random_splits < criteria.min_core_vs_random_splits:
        failures.append("core-vs-random splits below threshold")
    if pd.isna(mean_core_minus_random) or mean_core_minus_random < criteria.min_mean_core_minus_random:
        failures.append("mean core-minus-random performance below threshold")
    if pd.isna(positive_random) or positive_random < criteria.min_positive_core_vs_random_fraction:
        failures.append("positive core-vs-random fraction below threshold")

    all_candidates_validated = bool(len(candidates)) and bool(candidates["necessity_pass"].all())
    promoted_core = all_candidates_validated and core_transfer_pass and core_random_pass
    validated = evidence.loc[evidence["independently_validated_process"]].copy().reset_index(drop=True)
    return UniversalProcessPromotionAssessment(
        promoted_core=promoted_core,
        process_evidence=evidence.reset_index(drop=True),
        core_transfer_evidence=core_transfer,
        core_random_evidence=core_random,
        validated_process_candidates=validated,
        failures=failures,
    )
