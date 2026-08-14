"""CLI gate that emits a promoted Product-A protocol only when declared criteria pass."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .promotion import ProductAPromotionCriteria, assess_product_a_promotion


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate predeclared Product-A promotion criteria from repeated protocol runs. "
            "No threshold has a hidden default: all scientific cutoffs must be supplied explicitly."
        )
    )
    parser.add_argument("--runs", required=True)
    parser.add_argument("--choice-stability", required=True)
    parser.add_argument("--paired-validation-deltas", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--min-protocol-selection-fraction", type=float, required=True)
    parser.add_argument("--min-runs-selected", type=int, required=True)
    parser.add_argument("--min-mean-delta-presence-rank", type=float, required=True)
    parser.add_argument("--min-positive-pair-fraction", type=float, required=True)
    parser.add_argument("--min-pairs-per-comparator", type=int, required=True)
    parser.add_argument("--required-comparators", required=True, help="Comma-separated, e.g. all,vif")
    args = parser.parse_args(argv)

    comparators = tuple(x.strip() for x in args.required_comparators.split(",") if x.strip())
    try:
        criteria = ProductAPromotionCriteria(
            min_protocol_selection_fraction=args.min_protocol_selection_fraction,
            min_runs_selected=args.min_runs_selected,
            min_mean_delta_presence_rank=args.min_mean_delta_presence_rank,
            min_positive_pair_fraction=args.min_positive_pair_fraction,
            min_pairs_per_comparator=args.min_pairs_per_comparator,
            required_comparators=comparators,
        )
        assessment = assess_product_a_promotion(
            pd.read_csv(args.runs),
            pd.read_csv(args.choice_stability),
            pd.read_csv(args.paired_validation_deltas),
            criteria,
        )
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    assessment.top_protocol.to_csv(out / "promotion_top_protocol.csv", index=False)
    assessment.comparator_evidence.to_csv(out / "promotion_comparator_evidence.csv", index=False)
    pd.DataFrame(
        [
            {
                "promoted": assessment.promoted,
                "n_failures": len(assessment.failures),
                "failures": " | ".join(assessment.failures),
                "min_protocol_selection_fraction": criteria.min_protocol_selection_fraction,
                "min_runs_selected": criteria.min_runs_selected,
                "min_mean_delta_presence_rank": criteria.min_mean_delta_presence_rank,
                "min_positive_pair_fraction": criteria.min_positive_pair_fraction,
                "min_pairs_per_comparator": criteria.min_pairs_per_comparator,
                "required_comparators": ",".join(criteria.required_comparators),
            }
        ]
    ).to_csv(out / "promotion_assessment.csv", index=False)

    if assessment.promoted:
        choice = assessment.promoted_choice
        (out / "promoted_product_a_protocol.txt").write_text(
            "winning_data_specification=" + choice["winning_data_specification"] + "\n"
            + "winning_universe=" + choice["winning_universe"] + "\n"
            + "winning_strategy=" + choice["winning_strategy"] + "\n"
            + "winning_universe_sha256=" + choice["winning_universe_sha256"] + "\n"
            + "winning_predictors=" + choice["winning_predictors"] + "\n"
            + "occurrence_sha256=" + choice["occurrence_sha256"] + "\n"
            + "occurrence_feature_sha256=" + choice["occurrence_feature_sha256"] + "\n"
            + "promotion_min_protocol_selection_fraction=" + str(criteria.min_protocol_selection_fraction) + "\n"
            + "promotion_min_runs_selected=" + str(criteria.min_runs_selected) + "\n"
            + "promotion_min_mean_delta_presence_rank=" + str(criteria.min_mean_delta_presence_rank) + "\n"
            + "promotion_min_positive_pair_fraction=" + str(criteria.min_positive_pair_fraction) + "\n"
            + "promotion_min_pairs_per_comparator=" + str(criteria.min_pairs_per_comparator) + "\n"
            + "promotion_required_comparators=" + ",".join(criteria.required_comparators) + "\n",
            encoding="utf-8",
        )
        return 0

    (out / "promotion_not_met.txt").write_text(
        "Product A was not promoted under the predeclared criteria.\n"
        + "\n".join("- " + failure for failure in assessment.failures)
        + "\n",
        encoding="utf-8",
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
