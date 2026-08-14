"""CLI promotion gate for universal plant niche-process claims."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .cli import _read_method_choice_values
from .process_promotion import UniversalProcessPromotionCriteria, assess_universal_process_promotion

_REQUIRED_PROTOCOL_FIELDS = (
    "universality_run_sha256",
    "data_specification",
    "universe",
    "strategy",
    "universe_sha256",
    "predictors",
    "product_a_promotion_min_protocol_selection_fraction",
    "product_a_promotion_min_runs_selected",
    "product_a_promotion_min_mean_delta_presence_rank",
    "product_a_promotion_min_positive_pair_fraction",
    "product_a_promotion_min_pairs_per_comparator",
    "product_a_promotion_required_comparators",
)


def _validate_universality_binding(
    protocol_path: str,
    frames: dict[str, pd.DataFrame],
) -> dict[str, str]:
    values = _read_method_choice_values(protocol_path)
    missing = [field for field in _REQUIRED_PROTOCOL_FIELDS if not values.get(field, "").strip()]
    if missing:
        raise ValueError(f"universality protocol missing fields: {missing}")
    run_sha = values["universality_run_sha256"]
    expected_columns = {
        "universality_run_sha256": run_sha,
        "product_a_data_specification": values["data_specification"],
        "product_a_universe": values["universe"],
        "product_a_strategy": values["strategy"],
        "product_a_universe_sha256": values["universe_sha256"],
    }
    for name, frame in frames.items():
        for column, expected in expected_columns.items():
            if column not in frame.columns:
                raise ValueError(f"{name} missing provenance column {column}")
            observed = set(frame[column].dropna().astype(str))
            if observed != {str(expected)}:
                raise ValueError(
                    f"{name} provenance mismatch for {column}: expected {expected!r}, observed {sorted(observed)!r}"
                )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Promote a universal process core only if predeclared discovery stability, unseen-taxon necessity, "
            "core-vs-full transfer, and core-vs-random criteria all pass. All thresholds are required."
        )
    )
    parser.add_argument("--universality-protocol", required=True, help="universal_process_protocol.txt")
    parser.add_argument("--process-stability", required=True)
    parser.add_argument("--validation-comparison", required=True)
    parser.add_argument("--core-vs-random", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--min-core-stability", type=float, required=True)
    parser.add_argument("--min-splits-selected", type=int, required=True)
    parser.add_argument("--min-mean-validation-process-drop", type=float, required=True)
    parser.add_argument("--min-positive-validation-drop-fraction", type=float, required=True)
    parser.add_argument("--min-validation-drop-pairs", type=int, required=True)
    parser.add_argument("--min-validation-drop-splits", type=int, required=True)
    parser.add_argument("--min-mean-core-minus-full", type=float, required=True)
    parser.add_argument("--min-core-validation-pairs", type=int, required=True)
    parser.add_argument("--min-core-validation-splits", type=int, required=True)
    parser.add_argument("--min-mean-core-minus-random", type=float, required=True)
    parser.add_argument("--min-positive-core-vs-random-fraction", type=float, required=True)
    parser.add_argument("--min-core-vs-random-pairs", type=int, required=True)
    parser.add_argument("--min-core-vs-random-splits", type=int, required=True)
    args = parser.parse_args(argv)

    process_stability = pd.read_csv(args.process_stability)
    validation_comparison = pd.read_csv(args.validation_comparison)
    core_vs_random = pd.read_csv(args.core_vs_random)
    try:
        protocol = _validate_universality_binding(
            args.universality_protocol,
            {
                "process_stability": process_stability,
                "validation_comparison": validation_comparison,
                "core_vs_random": core_vs_random,
            },
        )
        criteria = UniversalProcessPromotionCriteria(
            min_core_stability=args.min_core_stability,
            min_splits_selected=args.min_splits_selected,
            min_mean_validation_process_drop=args.min_mean_validation_process_drop,
            min_positive_validation_drop_fraction=args.min_positive_validation_drop_fraction,
            min_validation_drop_pairs=args.min_validation_drop_pairs,
            min_validation_drop_splits=args.min_validation_drop_splits,
            min_mean_core_minus_full=args.min_mean_core_minus_full,
            min_core_validation_pairs=args.min_core_validation_pairs,
            min_core_validation_splits=args.min_core_validation_splits,
            min_mean_core_minus_random=args.min_mean_core_minus_random,
            min_positive_core_vs_random_fraction=args.min_positive_core_vs_random_fraction,
            min_core_vs_random_pairs=args.min_core_vs_random_pairs,
            min_core_vs_random_splits=args.min_core_vs_random_splits,
        )
        assessment = assess_universal_process_promotion(
            process_stability,
            validation_comparison,
            core_vs_random,
            criteria,
        )
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    assessment.process_evidence.to_csv(out / "universal_process_promotion_evidence.csv", index=False)
    assessment.validated_process_candidates.to_csv(out / "validated_universal_process_candidates.csv", index=False)
    assessment.core_transfer_evidence.to_csv(out / "universal_core_transfer_gate.csv", index=False)
    assessment.core_random_evidence.to_csv(out / "universal_core_random_gate.csv", index=False)
    pd.DataFrame([
        {
            "promoted_core": assessment.promoted_core,
            "universality_run_sha256": protocol["universality_run_sha256"],
            "n_validated_process_candidates": len(assessment.validated_process_candidates),
            "n_failures": len(assessment.failures),
            "failures": " | ".join(assessment.failures),
        }
    ]).to_csv(out / "universal_process_promotion_assessment.csv", index=False)

    criteria_lines = [
        f"min_core_stability={criteria.min_core_stability}",
        f"min_splits_selected={criteria.min_splits_selected}",
        f"min_mean_validation_process_drop={criteria.min_mean_validation_process_drop}",
        f"min_positive_validation_drop_fraction={criteria.min_positive_validation_drop_fraction}",
        f"min_validation_drop_pairs={criteria.min_validation_drop_pairs}",
        f"min_validation_drop_splits={criteria.min_validation_drop_splits}",
        f"min_mean_core_minus_full={criteria.min_mean_core_minus_full}",
        f"min_core_validation_pairs={criteria.min_core_validation_pairs}",
        f"min_core_validation_splits={criteria.min_core_validation_splits}",
        f"min_mean_core_minus_random={criteria.min_mean_core_minus_random}",
        f"min_positive_core_vs_random_fraction={criteria.min_positive_core_vs_random_fraction}",
        f"min_core_vs_random_pairs={criteria.min_core_vs_random_pairs}",
        f"min_core_vs_random_splits={criteria.min_core_vs_random_splits}",
    ]
    upstream_lines = [
        "universality_run_sha256=" + protocol["universality_run_sha256"],
        "product_a_data_specification=" + protocol["data_specification"],
        "product_a_universe=" + protocol["universe"],
        "product_a_strategy=" + protocol["strategy"],
        "product_a_universe_sha256=" + protocol["universe_sha256"],
        "product_a_predictors=" + protocol["predictors"],
    ]
    for field in _REQUIRED_PROTOCOL_FIELDS:
        if field.startswith("product_a_promotion_"):
            upstream_lines.append(field + "=" + protocol[field])

    if len(assessment.validated_process_candidates):
        (out / "independently_validated_process_candidates.txt").write_text(
            "processes=" + ",".join(assessment.validated_process_candidates["process"].astype(str)) + "\n"
            + "note=These are independently validated process hypotheses; they are not a re-optimized core.\n"
            + "\n".join(upstream_lines + criteria_lines) + "\n",
            encoding="utf-8",
        )

    if assessment.promoted_core:
        candidates = assessment.process_evidence.loc[assessment.process_evidence["candidate_by_discovery"], "process"].astype(str)
        (out / "promoted_universal_process_core.txt").write_text(
            "processes=" + ",".join(candidates) + "\n"
            + "promotion_rule=all discovery-nominated processes passed unseen-taxon necessity; core passed transfer and random-null gates\n"
            + "\n".join(upstream_lines + criteria_lines) + "\n",
            encoding="utf-8",
        )
        return 0

    (out / "universal_core_not_promoted.txt").write_text(
        "The frozen discovery-defined universal process core did not satisfy all predeclared promotion gates.\n"
        + "No validation-driven pruning/redefinition of the core was performed.\n"
        + "universality_run_sha256=" + protocol["universality_run_sha256"] + "\n"
        + "\n".join("- " + failure for failure in assessment.failures) + "\n",
        encoding="utf-8",
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
