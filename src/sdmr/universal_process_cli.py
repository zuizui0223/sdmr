"""Formal universality runner using only a promoted full Product-A protocol."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .cli import _candidate_fingerprint
from .product_b_cli import _validate_protocol_choice
from .universality import benchmark_repeated_process_core_splits


def _read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    return pd.read_csv(p)


def _resolve_promoted_predictors(
    protocol_choice: str,
    data_specification_name: str,
    manifest: pd.DataFrame,
) -> tuple[dict[str, str], list[str]]:
    values = _validate_protocol_choice(protocol_choice, data_specification_name)
    predictors = [x for x in values["winning_predictors"].split(",") if x]
    available = set(manifest["predictor"].astype(str))
    missing = [p for p in predictors if p not in available]
    if missing:
        raise ValueError(f"promoted predictors missing from manifest: {missing}")
    observed = _candidate_fingerprint(predictors)
    if observed != values["winning_universe_sha256"]:
        raise ValueError("promoted predictor fingerprint does not match winning_universe_sha256")
    return values, predictors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run repeated universal-process discovery/validation only under a promoted full Product-A protocol. "
            "Outputs include unseen-taxon process-drop necessity and matched random-core nulls."
        )
    )
    parser.add_argument("--protocol-choice", required=True, help="promoted_product_a_protocol.txt")
    parser.add_argument("--data-specification-name", required=True)
    parser.add_argument("--occurrences", required=True)
    parser.add_argument("--background", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--spatial-test-fraction", type=float, default=0.20)
    parser.add_argument("--taxon-validation-fraction", type=float, default=0.20)
    parser.add_argument("--min-process-selection-fraction", type=float, default=0.25)
    parser.add_argument("--process-top-k", type=int, default=6)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--random-process-repeats", type=int, default=20)
    parser.add_argument("--vif-threshold", type=float, default=5.0)
    parser.add_argument("--max-predictors", type=int, default=8)
    parser.add_argument("--equivalence-threshold", type=float, default=0.90)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if not 0 < args.spatial_test_fraction < 1:
        parser.error("--spatial-test-fraction must be between 0 and 1")
    if not 0 < args.taxon_validation_fraction < 1:
        parser.error("--taxon-validation-fraction must be between 0 and 1")
    if not 0 <= args.min_process_selection_fraction <= 1:
        parser.error("--min-process-selection-fraction must be in [0, 1]")
    if args.process_top_k < 1 or args.repeats < 1 or args.random_process_repeats < 0:
        parser.error("process-top-k/repeats must be positive and random-process-repeats non-negative")
    if args.vif_threshold <= 1 or args.max_predictors < 1:
        parser.error("vif-threshold must be > 1 and max-predictors >= 1")
    if not 0 < args.equivalence_threshold <= 1:
        parser.error("--equivalence-threshold must be in (0, 1]")

    manifest = pd.read_csv(args.manifest)
    try:
        choice, predictors = _resolve_promoted_predictors(
            args.protocol_choice,
            args.data_specification_name,
            manifest,
        )
    except ValueError as exc:
        parser.error(str(exc))

    occurrences = _read_table(args.occurrences)
    background = _read_table(args.background)
    seeds = tuple(args.seed + i * 1009 for i in range(args.repeats))
    result = benchmark_repeated_process_core_splits(
        occurrences,
        background,
        predictors,
        manifest,
        strategy=choice["winning_strategy"],
        seeds=seeds,
        taxon_validation_fraction=args.taxon_validation_fraction,
        min_process_selection_fraction=args.min_process_selection_fraction,
        process_top_k=args.process_top_k,
        random_process_repeats=args.random_process_repeats,
        sealed_fraction=args.spatial_test_fraction,
        vif_threshold=args.vif_threshold,
        max_predictors=args.max_predictors,
        equivalence_threshold=args.equivalence_threshold,
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.splits.to_csv(out / "universal_process_splits.csv", index=False)
    result.process_stability.to_csv(out / "universal_process_stability.csv", index=False)
    result.validation_comparison.to_csv(out / "universal_core_vs_full.csv", index=False)
    result.validation_process_drop.to_csv(out / "universal_process_drop_unseen_taxa.csv", index=False)
    result.random_core_metrics.to_csv(out / "universal_random_core_metrics.csv", index=False)
    result.core_vs_random.to_csv(out / "universal_core_vs_random.csv", index=False)
    (out / "universal_process_protocol.txt").write_text(
        "data_specification=" + choice["winning_data_specification"] + "\n"
        + "universe=" + choice["winning_universe"] + "\n"
        + "strategy=" + choice["winning_strategy"] + "\n"
        + "universe_sha256=" + choice["winning_universe_sha256"] + "\n"
        + "predictors=" + ",".join(predictors) + "\n"
        + "seeds=" + ",".join(str(x) for x in seeds) + "\n"
        + f"spatial_test_fraction={args.spatial_test_fraction}\n"
        + f"taxon_validation_fraction={args.taxon_validation_fraction}\n"
        + f"min_process_selection_fraction={args.min_process_selection_fraction}\n"
        + f"process_top_k={args.process_top_k}\n"
        + f"random_process_repeats={args.random_process_repeats}\n"
        + f"equivalence_threshold={args.equivalence_threshold}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
