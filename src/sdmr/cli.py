"""Command-line entry point for SDMR method and driver benchmarks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .benchmark import benchmark_taxon_split
from .tuning import benchmark_method_taxon_split


def _read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    return pd.read_csv(p)


def _read_predictors(path: str) -> list[str]:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        manifest = pd.read_csv(p)
        if "predictor" not in manifest.columns:
            raise ValueError("Predictor CSV must contain a 'predictor' column.")
        return manifest["predictor"].dropna().astype(str).tolist()
    lines = p.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Tune plant SDMs with sealed occurrences (Product A) or discover "
            "cross-taxon environmental drivers (Product B)."
        )
    )
    parser.add_argument("--occurrences", required=True)
    parser.add_argument("--background", required=True)
    parser.add_argument("--predictors", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--mode",
        choices=("method", "drivers"),
        default="method",
        help="method = Product A (default); drivers = Product B common-raster benchmark",
    )
    parser.add_argument(
        "--spatial-test-fraction",
        type=float,
        default=0.20,
        help="Configurable fraction of spatial blocks reserved as sealed within-species answer checks.",
    )
    parser.add_argument(
        "--taxon-validation-fraction",
        type=float,
        default=0.20,
        help="Configurable fraction of species reserved for unseen-taxon validation.",
    )
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

    occurrences = _read_table(args.occurrences)
    background = _read_table(args.background)
    predictors = _read_predictors(args.predictors)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.mode == "method":
        result = benchmark_method_taxon_split(
            occurrences,
            background,
            predictors,
            taxon_validation_fraction=args.taxon_validation_fraction,
            sealed_fraction=args.spatial_test_fraction,
            vif_threshold=args.vif_threshold,
            max_predictors=args.max_predictors,
            random_repeats=args.random_baseline_repeats,
            compute_drop_one=False,
            random_state=args.seed,
        )
        result.discovery_metrics.to_csv(out / "method_discovery_metrics.csv", index=False)
        result.discovery_summary.to_csv(out / "method_discovery_summary.csv", index=False)
        result.validation_metrics.to_csv(out / "method_validation_metrics.csv", index=False)
        result.validation_summary.to_csv(out / "method_validation_summary.csv", index=False)
        (out / "method_choice.txt").write_text(
            "winning_strategy=" + result.winning_strategy + "\n"
            + "discovery_species=" + ",".join(result.discovery_species) + "\n"
            + "validation_species=" + ",".join(result.validation_species) + "\n"
            + f"spatial_test_fraction={args.spatial_test_fraction}\n"
            + f"taxon_validation_fraction={args.taxon_validation_fraction}\n",
            encoding="utf-8",
        )
    else:
        result = benchmark_taxon_split(
            occurrences,
            background,
            predictors,
            spatial_holdout_fraction=args.spatial_test_fraction,
            taxon_holdout_fraction=args.taxon_validation_fraction,
            max_predictors=args.max_predictors,
            random_state=args.seed,
        )
        result.predictor_aggregate.to_csv(out / "predictor_aggregate.csv", index=False)
        result.discovery_selection.to_csv(out / "discovery_selection.csv", index=False)
        result.discovery_outer.to_csv(out / "discovery_outer.csv", index=False)
        result.validation_outer.to_csv(out / "validation_outer.csv", index=False)
        (out / "common_predictors.txt").write_text(
            "\n".join(result.common_predictors) + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
