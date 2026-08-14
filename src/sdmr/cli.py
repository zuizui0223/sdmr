"""Command-line entry point for SDMR method and driver benchmarks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .synthesis import benchmark_driver_corpus_from_strategy
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


def _read_manifest(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() != ".csv":
        raise ValueError("Product B requires a CSV predictor manifest with process metadata.")
    return pd.read_csv(p)


def _read_method_choice(path: str) -> str:
    values: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    strategy = values.get("winning_strategy", "")
    if strategy not in {"all", "vif", "predictive"}:
        raise ValueError("method_choice must contain winning_strategy=all|vif|predictive")
    return strategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Tune plant SDMs with sealed occurrences (Product A) or apply the "
            "already-frozen Product-A strategy to environmental-driver synthesis (Product B)."
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
        help="method = Product A (default); drivers = Product B using a frozen Product-A strategy",
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
        help="Product A: fraction of species reserved for unseen-taxon method validation.",
    )
    parser.add_argument(
        "--strategy",
        choices=("all", "vif", "predictive"),
        help="Product B only: explicitly frozen strategy. Prefer --method-choice from Product A.",
    )
    parser.add_argument(
        "--method-choice",
        help="Product B only: Product-A method_choice.txt containing winning_strategy=...",
    )
    parser.add_argument("--equivalence-threshold", type=float, default=0.90)
    parser.add_argument("--vif-threshold", type=float, default=5.0)
    parser.add_argument("--max-predictors", type=int, default=8)
    parser.add_argument("--random-baseline-repeats", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if not 0 < args.spatial_test_fraction < 1:
        parser.error("--spatial-test-fraction must be between 0 and 1")
    if not 0 < args.taxon_validation_fraction < 1:
        parser.error("--taxon-validation-fraction must be between 0 and 1")
    if not 0 < args.equivalence_threshold <= 1:
        parser.error("--equivalence-threshold must be in (0, 1]")
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
        choice_strategy = _read_method_choice(args.method_choice) if args.method_choice else None
        if args.strategy and choice_strategy and args.strategy != choice_strategy:
            parser.error("--strategy conflicts with winning_strategy in --method-choice")
        strategy = choice_strategy or args.strategy
        if strategy is None:
            parser.error("Product B requires --method-choice from Product A or an explicit frozen --strategy")
        manifest = _read_manifest(args.predictors)
        result = benchmark_driver_corpus_from_strategy(
            occurrences,
            background,
            predictors,
            manifest,
            strategy=strategy,
            sealed_fraction=args.spatial_test_fraction,
            vif_threshold=args.vif_threshold,
            max_predictors=args.max_predictors,
            equivalence_threshold=args.equivalence_threshold,
            random_state=args.seed,
        )
        result.per_species_metrics.to_csv(out / "driver_species_metrics.csv", index=False)
        result.selection_rows.to_csv(out / "driver_selection_rows.csv", index=False)
        result.drop_one_rows.to_csv(out / "driver_drop_one.csv", index=False)
        result.equivalence_rows.to_csv(out / "driver_equivalence.csv", index=False)
        result.group_drop_rows.to_csv(out / "driver_group_drop.csv", index=False)
        result.predictor_summary.to_csv(out / "driver_predictor_summary.csv", index=False)
        result.process_summary.to_csv(out / "driver_process_summary.csv", index=False)
        (out / "driver_strategy.txt").write_text(
            "strategy=" + strategy + "\n"
            + f"spatial_test_fraction={args.spatial_test_fraction}\n"
            + f"equivalence_threshold={args.equivalence_threshold}\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
