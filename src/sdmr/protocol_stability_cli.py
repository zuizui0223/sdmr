"""CLI for repeated full Product-A protocol promotion-gate validation."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .protocol_stability import benchmark_repeated_product_a_protocols
from .spec_cli import _read_specifications
from .universe import candidate_universes_from_manifest


def _parse_ints(value: str) -> tuple[int, ...]:
    parsed = tuple(int(x.strip()) for x in value.split(",") if x.strip())
    if not parsed:
        raise ValueError("At least one seed is required")
    return parsed


def _parse_floats(value: str) -> tuple[float, ...]:
    parsed = tuple(float(x.strip()) for x in value.split(",") if x.strip())
    if not parsed or any(not 0 < x < 1 for x in parsed):
        raise ValueError("sealed fractions must be comma-separated values between 0 and 1")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Repeat full Product-A protocol selection over multiple seeds and sealed fractions and report "
            "protocol stability plus paired unseen-taxon deltas against predeclared strategy baselines."
        )
    )
    parser.add_argument("--specifications", required=True, help="CSV: name,occurrences,background")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seeds", default="11,22,33,44,55")
    parser.add_argument("--sealed-fractions", default="0.15,0.20,0.30")
    parser.add_argument("--taxon-validation-fraction", type=float, default=0.20)
    parser.add_argument("--vif-threshold", type=float, default=5.0)
    parser.add_argument("--max-predictors", type=int, default=8)
    parser.add_argument("--random-baseline-repeats", type=int, default=20)
    args = parser.parse_args(argv)

    try:
        seeds = _parse_ints(args.seeds)
        fractions = _parse_floats(args.sealed_fractions)
    except ValueError as exc:
        parser.error(str(exc))
    if not 0 < args.taxon_validation_fraction < 1:
        parser.error("--taxon-validation-fraction must be between 0 and 1")
    if args.vif_threshold <= 1:
        parser.error("--vif-threshold must be > 1")
    if args.max_predictors < 1:
        parser.error("--max-predictors must be >= 1")
    if args.random_baseline_repeats < 0:
        parser.error("--random-baseline-repeats must be >= 0")

    specifications = _read_specifications(args.specifications)
    manifest = pd.read_csv(args.manifest)
    universes = candidate_universes_from_manifest(manifest)
    result = benchmark_repeated_product_a_protocols(
        specifications,
        universes,
        seeds=seeds,
        sealed_fractions=fractions,
        taxon_validation_fraction=args.taxon_validation_fraction,
        vif_threshold=args.vif_threshold,
        max_predictors=args.max_predictors,
        random_repeats=args.random_baseline_repeats,
        compute_drop_one=False,
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.runs.to_csv(out / "protocol_stability_runs.csv", index=False)
    result.choice_stability.to_csv(out / "protocol_choice_stability.csv", index=False)
    result.component_stability.to_csv(out / "protocol_component_stability.csv", index=False)
    result.selected_validation_metrics.to_csv(out / "protocol_selected_validation_metrics.csv", index=False)
    result.paired_validation_deltas.to_csv(out / "protocol_validation_paired_deltas.csv", index=False)
    result.validation_delta_summary.to_csv(out / "protocol_validation_delta_summary.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
