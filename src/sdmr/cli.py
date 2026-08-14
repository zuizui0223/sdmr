"""Command-line entry point for SDMR method and driver benchmarks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .synthesis import benchmark_driver_corpus_from_strategy
from .tuning import benchmark_method_taxon_split
from .universality import benchmark_repeated_process_core_splits


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


def _resolve_frozen_strategy(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    choice_strategy = _read_method_choice(args.method_choice) if args.method_choice else None
    if args.strategy and choice_strategy and args.strategy != choice_strategy:
        parser.error("--strategy conflicts with winning_strategy in --method-choice")
    strategy = choice_strategy or args.strategy
    if strategy is None:
        parser.error("Product B requires --method-choice from Product A or an explicit frozen --strategy")
    return strategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Tune plant SDMs with sealed occurrences (Product A), apply the frozen "
            "Product-A strategy to driver synthesis, or validate a universal process core on unseen taxa."
        )
    )
    parser.add_argument("--occurrences", required=True)
    parser.add_argument("--background", required=True)
    parser.add_argument("--predictors", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--mode",
        choices=("method", "drivers", "universality"),
        default="method",
        help=(
            "method = Product A; drivers = Product B corpus synthesis; "
            "universality = repeated discovery/validation taxon tests of a reduced process core"
        ),
    )
    parser.add_argument(
        "--spatial-test-fraction",
        type=float,
        default=0.20,
        help="Fraction of spatial blocks reserved as sealed within-species answer checks.",
    )
    parser.add_argument(
        "--taxon-validation-fraction",
        type=float,
        default=0.20,
        help="Fraction of species reserved for unseen-taxon validation.",
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
    parser.add_argument(
        "--min-process-selection-fraction",
        type=float,
        default=0.25,
        help="Universality mode: discovery-taxon selection fraction required for a core process.",
    )
    parser.add_argument(
        "--process-top-k",
        type=int,
        default=6,
        help="Universality mode: maximum number of discovery-defined core processes.",
    )
    parser.add_argument(
        "--universality-repeats",
        type=int,
        default=5,
        help="Universality mode: number of repeated discovery/validation taxon splits.",
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
    if not 0 < args.equivalence_threshold <= 1:
        parser.error("--equivalence-threshold must be in (0, 1]")
    if not 0 <= args.min_process_selection_fraction <= 1:
        parser.error("--min-process-selection-fraction must be in [0, 1]")
    if args.process_top_k < 1:
        parser.error("--process-top-k must be >= 1")
    if args.universality_repeats < 1:
        parser.error("--universality-repeats must be >= 1")
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
        return 0

    strategy = _resolve_frozen_strategy(args, parser)
    manifest = _read_manifest(args.predictors)

    if args.mode == "drivers":
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

    seeds = tuple(args.seed + i * 1009 for i in range(args.universality_repeats))
    result = benchmark_repeated_process_core_splits(
        occurrences,
        background,
        predictors,
        manifest,
        strategy=strategy,
        seeds=seeds,
        taxon_validation_fraction=args.taxon_validation_fraction,
        min_process_selection_fraction=args.min_process_selection_fraction,
        process_top_k=args.process_top_k,
        sealed_fraction=args.spatial_test_fraction,
        vif_threshold=args.vif_threshold,
        max_predictors=args.max_predictors,
        equivalence_threshold=args.equivalence_threshold,
    )
    result.splits.to_csv(out / "universality_process_splits.csv", index=False)
    result.process_stability.to_csv(out / "universality_process_stability.csv", index=False)
    result.validation_comparison.to_csv(out / "universality_validation.csv", index=False)
    (out / "universality_strategy.txt").write_text(
        "strategy=" + strategy + "\n"
        + "seeds=" + ",".join(str(seed) for seed in seeds) + "\n"
        + f"spatial_test_fraction={args.spatial_test_fraction}\n"
        + f"taxon_validation_fraction={args.taxon_validation_fraction}\n"
        + f"min_process_selection_fraction={args.min_process_selection_fraction}\n"
        + f"process_top_k={args.process_top_k}\n"
        + f"equivalence_threshold={args.equivalence_threshold}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
