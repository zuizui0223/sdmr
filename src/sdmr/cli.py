"""Command-line entry point for table-based benchmarks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .benchmark import benchmark_taxon_split


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
    parser = argparse.ArgumentParser(description="Discover transferable SDM predictors with nested spatial holdout.")
    parser.add_argument("--occurrences", required=True, help="CSV/Parquet of GBIF-like occurrence rows plus raster values")
    parser.add_argument("--background", required=True, help="CSV/Parquet of target-group/background rows plus raster values")
    parser.add_argument("--predictors", required=True, help="Text file or CSV manifest of predictor column names")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    occurrences = _read_table(args.occurrences)
    background = _read_table(args.background)
    predictors = _read_predictors(args.predictors)
    result = benchmark_taxon_split(occurrences, background, predictors, random_state=args.seed)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.predictor_aggregate.to_csv(out / "predictor_aggregate.csv", index=False)
    result.discovery_selection.to_csv(out / "discovery_selection.csv", index=False)
    result.discovery_outer.to_csv(out / "discovery_outer.csv", index=False)
    result.validation_outer.to_csv(out / "validation_outer.csv", index=False)
    (out / "common_predictors.txt").write_text("\n".join(result.common_predictors) + "\n", encoding="utf-8")
    (out / "taxon_split.txt").write_text(
        "discovery=" + ",".join(result.discovery_species) + "\n" +
        "validation=" + ",".join(result.validation_species) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
