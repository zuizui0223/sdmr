"""CLI for freezing a complete Product-A protocol on discovery taxa."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .protocol import benchmark_product_a_protocol_grid
from .spec_cli import _read_specifications
from .universe import CandidateUniverse, candidate_universes_from_manifest


def _read_universes(path: str) -> dict[str, CandidateUniverse]:
    manifest = pd.read_csv(path)
    required = {"predictor", "source", "version", "candidate_class", "process", "mechanism"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Product-A protocol manifest missing columns: {sorted(missing)}")
    return candidate_universes_from_manifest(manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Choose data specification × environmental candidate universe × SDM strategy using discovery taxa only, "
            "then validate the frozen protocol on unseen taxa."
        )
    )
    parser.add_argument("--specifications", required=True, help="CSV: name,occurrences,background")
    parser.add_argument("--manifest", required=True, help="Active predictor manifest defining standard candidate universes")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--spatial-test-fraction", type=float, default=0.20)
    parser.add_argument("--taxon-validation-fraction", type=float, default=0.20)
    parser.add_argument("--vif-threshold", type=float, default=5.0)
    parser.add_argument("--max-predictors", type=int, default=8)
    parser.add_argument("--random-baseline-repeats", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if not 0 < args.spatial_test_fraction < 1:
        parser.error("--spatial-test-fraction must be between 0 and 1")
    if not 0 < args.taxon_validation_fraction < 1:
        parser.error("--taxon-validation-fraction must be between 0 and 1")
    if args.vif_threshold <= 1:
        parser.error("--vif-threshold must be > 1")
    if args.max_predictors < 1:
        parser.error("--max-predictors must be >= 1")
    if args.random_baseline_repeats < 0:
        parser.error("--random-baseline-repeats must be >= 0")

    specifications = _read_specifications(args.specifications)
    universes = _read_universes(args.manifest)
    result = benchmark_product_a_protocol_grid(
        specifications,
        universes,
        taxon_validation_fraction=args.taxon_validation_fraction,
        sealed_fraction=args.spatial_test_fraction,
        vif_threshold=args.vif_threshold,
        max_predictors=args.max_predictors,
        random_repeats=args.random_baseline_repeats,
        compute_drop_one=False,
        random_state=args.seed,
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.discovery_metrics.to_csv(out / "protocol_discovery_metrics.csv", index=False)
    result.discovery_summary.to_csv(out / "protocol_discovery_summary.csv", index=False)
    result.validation_metrics.to_csv(out / "protocol_validation_metrics.csv", index=False)
    result.validation_summary.to_csv(out / "protocol_validation_summary.csv", index=False)
    result.paired_validation_deltas.to_csv(out / "protocol_validation_paired_deltas.csv", index=False)
    (out / "product_a_protocol_choice.txt").write_text(
        "winning_data_specification=" + result.winning_data_specification + "\n"
        + "winning_universe=" + result.winning_universe + "\n"
        + "winning_strategy=" + result.winning_strategy + "\n"
        + "winning_universe_sha256=" + result.winning_universe_sha256 + "\n"
        + "winning_predictors=" + ",".join(result.winning_predictors) + "\n"
        + "occurrence_sha256=" + result.occurrence_sha256 + "\n"
        + "occurrence_feature_sha256=" + result.occurrence_feature_sha256 + "\n"
        + "discovery_species=" + ",".join(result.discovery_species) + "\n"
        + "validation_species=" + ",".join(result.validation_species) + "\n"
        + f"spatial_test_fraction={args.spatial_test_fraction}\n"
        + f"taxon_validation_fraction={args.taxon_validation_fraction}\n"
        + f"seed={args.seed}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
