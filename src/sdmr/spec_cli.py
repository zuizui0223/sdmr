"""CLI for leakage-safe Product-A M/background specification selection."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .specification import benchmark_matched_data_specifications


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
            raise ValueError("Predictor CSV must contain a 'predictor' column")
        return manifest["predictor"].dropna().astype(str).tolist()
    return [
        line.strip()
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _read_specifications(path: str) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    config = pd.read_csv(path)
    required = {"name", "occurrences", "background"}
    missing = required - set(config.columns)
    if missing:
        raise ValueError(f"specification CSV missing columns: {sorted(missing)}")
    if config["name"].astype(str).duplicated().any():
        raise ValueError("specification names must be unique")
    root = Path(path).resolve().parent
    out: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for row in config.itertuples(index=False):
        name = str(row.name).strip()
        if not name:
            raise ValueError("specification name must not be empty")
        occ_path = Path(str(row.occurrences))
        bg_path = Path(str(row.background))
        if not occ_path.is_absolute():
            occ_path = root / occ_path
        if not bg_path.is_absolute():
            bg_path = root / bg_path
        out[name] = (_read_table(str(occ_path)), _read_table(str(bg_path)))
    return out


def _predictor_fingerprint(predictors: list[str]) -> str:
    payload = json.dumps(list(predictors), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Select an M/background specification plus SDM strategy using discovery taxa only. "
            "All directly compared specifications must contain identical occurrence evidence."
        )
    )
    parser.add_argument("--specifications", required=True, help="CSV: name,occurrences,background")
    parser.add_argument("--predictors", required=True, help="Predictor manifest/list shared by all specifications")
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
    predictors = _read_predictors(args.predictors)
    result = benchmark_matched_data_specifications(
        specifications,
        predictors,
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
    result.discovery_metrics.to_csv(out / "spec_discovery_metrics.csv", index=False)
    result.discovery_summary.to_csv(out / "spec_discovery_summary.csv", index=False)
    result.validation_metrics.to_csv(out / "spec_validation_metrics.csv", index=False)
    result.validation_summary.to_csv(out / "spec_validation_summary.csv", index=False)
    result.paired_validation_deltas.to_csv(out / "spec_validation_paired_deltas.csv", index=False)
    (out / "method_spec_choice.txt").write_text(
        "winning_data_specification=" + result.winning_specification + "\n"
        + "winning_strategy=" + result.winning_strategy + "\n"
        + "occurrence_sha256=" + result.occurrence_sha256 + "\n"
        + "predictor_sha256=" + _predictor_fingerprint(predictors) + "\n"
        + "predictors=" + ",".join(predictors) + "\n"
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
