"""Explicit, predeclared promotion gate for freezing Product A before Product B."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd


@dataclass(frozen=True)
class ProductAPromotionCriteria:
    """All scientific thresholds are caller-declared; SDMR hides no cutoff."""

    min_protocol_selection_fraction: float
    min_runs_selected: int
    min_mean_delta_presence_rank: float
    min_positive_pair_fraction: float
    min_pairs_per_comparator: int
    required_comparators: tuple[str, ...]
    # Backward-compatible default only.  The citable Product-A program supplies
    # this explicitly from its versioned criteria file before results exist.
    min_m_spec_win_fraction: float = 0.0

    def __post_init__(self):
        if not 0 <= self.min_protocol_selection_fraction <= 1:
            raise ValueError("min_protocol_selection_fraction must be in [0, 1]")
        if self.min_runs_selected < 1:
            raise ValueError("min_runs_selected must be >= 1")
        if not 0 <= self.min_positive_pair_fraction <= 1:
            raise ValueError("min_positive_pair_fraction must be in [0, 1]")
        if self.min_pairs_per_comparator < 1:
            raise ValueError("min_pairs_per_comparator must be >= 1")
        if not self.required_comparators:
            raise ValueError("required_comparators must not be empty")
        if not 0 <= self.min_m_spec_win_fraction <= 1:
            raise ValueError("min_m_spec_win_fraction must be in [0, 1]")


@dataclass
class ProductAPromotionAssessment:
    promoted: bool
    top_protocol: pd.DataFrame
    comparator_evidence: pd.DataFrame
    failures: list[str]
    promoted_choice: dict[str, str]


def _required_columns(frame: pd.DataFrame, columns: Sequence[str], name: str) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise KeyError(f"{name} missing columns: {sorted(missing)}")


def assess_product_a_promotion(
    runs: pd.DataFrame,
    choice_stability: pd.DataFrame,
    paired_validation_deltas: pd.DataFrame,
    criteria: ProductAPromotionCriteria,
) -> ProductAPromotionAssessment:
    """Assess a discovery-selected method under predeclared stability rules.

    In the citable program ``winning_data_specification`` is a constant label
    representing the whole predeclared M sensitivity set; M itself is never
    optimized.  ``m_spec_win_fraction`` records whether the chosen method also
    wins inside the individual M specifications.
    """
    _required_columns(
        choice_stability,
        [
            "winning_data_specification",
            "winning_universe",
            "winning_strategy",
            "runs_selected",
            "n_runs",
            "selection_fraction",
        ],
        "choice_stability",
    )
    required_run_columns = [
        "run_id",
        "winning_data_specification",
        "winning_universe",
        "winning_strategy",
        "winning_universe_sha256",
        "winning_predictors",
        "occurrence_sha256",
        "occurrence_feature_sha256",
    ]
    if criteria.min_m_spec_win_fraction > 0:
        required_run_columns.append("m_spec_win_fraction")
    _required_columns(runs, required_run_columns, "runs")
    if not len(choice_stability):
        raise ValueError("choice_stability is empty")

    ranked = choice_stability.sort_values(
        ["selection_fraction", "runs_selected", "winning_data_specification", "winning_universe", "winning_strategy"],
        ascending=[False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    top = ranked.iloc[[0]].copy()
    top_row = top.iloc[0]
    spec = str(top_row["winning_data_specification"])
    universe = str(top_row["winning_universe"])
    strategy = str(top_row["winning_strategy"])

    failures: list[str] = []
    if float(top_row["selection_fraction"]) < criteria.min_protocol_selection_fraction:
        failures.append(
            f"protocol selection_fraction={float(top_row['selection_fraction']):.6g} "
            f"< {criteria.min_protocol_selection_fraction:.6g}"
        )
    if int(top_row["runs_selected"]) < criteria.min_runs_selected:
        failures.append(
            f"protocol runs_selected={int(top_row['runs_selected'])} < {criteria.min_runs_selected}"
        )

    matching_runs = runs.loc[
        (runs["winning_data_specification"].astype(str) == spec)
        & (runs["winning_universe"].astype(str) == universe)
        & (runs["winning_strategy"].astype(str) == strategy)
    ].sort_values("run_id", kind="mergesort")
    if not len(matching_runs):
        raise RuntimeError("Top stability method has no matching run rows")

    if criteria.min_m_spec_win_fraction > 0:
        observed_min = float(pd.to_numeric(matching_runs["m_spec_win_fraction"], errors="coerce").min())
        observed_mean = float(pd.to_numeric(matching_runs["m_spec_win_fraction"], errors="coerce").mean())
        top["min_m_spec_win_fraction_observed"] = observed_min
        top["mean_m_spec_win_fraction_observed"] = observed_mean
        if observed_min < criteria.min_m_spec_win_fraction:
            failures.append(
                f"M-sensitivity min_spec_win_fraction={observed_min:.6g} "
                f"< {criteria.min_m_spec_win_fraction:.6g}"
            )

    if len(paired_validation_deltas):
        _required_columns(
            paired_validation_deltas,
            [
                "run_id",
                "winning_data_specification",
                "winning_universe",
                "winning_strategy",
                "comparator",
                "delta_presence_rank",
            ],
            "paired_validation_deltas",
        )
        matched = paired_validation_deltas.loc[
            (paired_validation_deltas["winning_data_specification"].astype(str) == spec)
            & (paired_validation_deltas["winning_universe"].astype(str) == universe)
            & (paired_validation_deltas["winning_strategy"].astype(str) == strategy)
        ].copy()
    else:
        matched = pd.DataFrame()

    evidence_rows: list[dict[str, object]] = []
    for comparator in criteria.required_comparators:
        comparator = str(comparator)
        if comparator == strategy:
            evidence_rows.append(
                {
                    "comparator": comparator,
                    "status": "self_not_applicable",
                    "n_pairs": 0,
                    "n_runs": 0,
                    "mean_delta_presence_rank": 0.0,
                    "median_delta_presence_rank": 0.0,
                    "positive_pair_fraction": 0.0,
                    "passes": True,
                }
            )
            continue
        subset = matched.loc[matched["comparator"].astype(str) == comparator].copy() if len(matched) else pd.DataFrame()
        if not len(subset):
            evidence_rows.append(
                {
                    "comparator": comparator,
                    "status": "missing",
                    "n_pairs": 0,
                    "n_runs": 0,
                    "mean_delta_presence_rank": float("nan"),
                    "median_delta_presence_rank": float("nan"),
                    "positive_pair_fraction": float("nan"),
                    "passes": False,
                }
            )
            failures.append(f"no unseen-taxon paired validation evidence against comparator={comparator}")
            continue
        mean_delta = float(subset["delta_presence_rank"].mean())
        median_delta = float(subset["delta_presence_rank"].median())
        positive = float((subset["delta_presence_rank"] > 0).mean())
        n_pairs = int(len(subset))
        n_runs = int(subset["run_id"].nunique())
        passes = (
            n_pairs >= criteria.min_pairs_per_comparator
            and mean_delta >= criteria.min_mean_delta_presence_rank
            and positive >= criteria.min_positive_pair_fraction
        )
        evidence_rows.append(
            {
                "comparator": comparator,
                "status": "evaluated",
                "n_pairs": n_pairs,
                "n_runs": n_runs,
                "mean_delta_presence_rank": mean_delta,
                "median_delta_presence_rank": median_delta,
                "positive_pair_fraction": positive,
                "passes": passes,
            }
        )
        if n_pairs < criteria.min_pairs_per_comparator:
            failures.append(f"comparator={comparator} n_pairs={n_pairs} < {criteria.min_pairs_per_comparator}")
        if mean_delta < criteria.min_mean_delta_presence_rank:
            failures.append(
                f"comparator={comparator} mean_delta={mean_delta:.6g} "
                f"< {criteria.min_mean_delta_presence_rank:.6g}"
            )
        if positive < criteria.min_positive_pair_fraction:
            failures.append(
                f"comparator={comparator} positive_pair_fraction={positive:.6g} "
                f"< {criteria.min_positive_pair_fraction:.6g}"
            )

    reference = matching_runs.iloc[0]
    promoted_choice = {
        "winning_data_specification": spec,
        "winning_universe": universe,
        "winning_strategy": strategy,
        "winning_universe_sha256": str(reference["winning_universe_sha256"]),
        "winning_predictors": str(reference["winning_predictors"]),
        "occurrence_sha256": str(reference["occurrence_sha256"]),
        "occurrence_feature_sha256": str(reference["occurrence_feature_sha256"]),
    }
    if criteria.min_m_spec_win_fraction > 0:
        promoted_choice["min_m_spec_win_fraction_observed"] = str(
            float(pd.to_numeric(matching_runs["m_spec_win_fraction"], errors="coerce").min())
        )
    return ProductAPromotionAssessment(
        promoted=not failures,
        top_protocol=top,
        comparator_evidence=pd.DataFrame(evidence_rows),
        failures=failures,
        promoted_choice=promoted_choice,
    )
