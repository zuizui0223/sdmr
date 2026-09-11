"""Type-stable aggregate wrapper for the v15 consumed-development audit.

Family artifacts are authoritative. Header-only CSVs from zero-focus families can
promote numeric columns to object dtype during concat; normalize manifest key
columns before equality checking so denominator validation tests values, not a
pandas concat dtype artifact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .alignment_transport_v15_development import _manifest
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES


def _read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["family"] = out["family"].astype(str)
    out["seed"] = pd.to_numeric(out["seed"], errors="raise").astype(int)
    out["target_process"] = out["target_process"].astype(str)
    out["v14_classification"] = out["v14_classification"].astype(str)
    return out


def aggregate(input_dir: str | Path, output_dir: str | Path):
    root = Path(input_dir)
    expected = len(KNOWN_TRUTH_FAMILIES)
    names = ["pair_summary.csv", "route_summary.csv", "cell_summary.csv"]
    files = {name: list(root.rglob(name)) for name in names}
    if any(len(paths) != expected for paths in files.values()):
        raise ValueError("v15 aggregate requires one artifact per family")

    merged = {
        name: pd.concat([_read(path) for path in paths], ignore_index=True)
        for name, paths in files.items()
    }
    cells = merged["cell_summary.csv"]
    manifest = _manifest()
    observed = _normalize_keys(
        cells[["family", "seed", "target_process", "v14_classification"]]
    ).sort_values(["family", "seed", "target_process"]).reset_index(drop=True)
    expected_manifest = _normalize_keys(manifest).sort_values(
        ["family", "seed", "target_process"]
    ).reset_index(drop=True)
    if not observed.equals(expected_manifest):
        raise ValueError("v15 aggregate denominator does not equal frozen focus manifest")

    counts = cells["classification"].astype(str).value_counts()
    result = {
        "purpose": "alignment_transport_v15_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_focus_cells": 9,
        "n_transported": int(counts.get("transported", 0)),
        "n_local_alignment_only": int(counts.get("local_alignment_only", 0)),
        "n_heterogeneous": int(counts.get("heterogeneous", 0)),
        "n_insufficient": int(counts.get("insufficient", 0)),
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in merged.items():
        frame.to_csv(out / name, index=False)
    (out / "development_decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(aggregate(args.input_dir, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
