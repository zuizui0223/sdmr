"""Aggregate wrapper for v17 with dtype/order-insensitive denominator validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .context_geometry_v17_development import _config, _evaluate, _target_manifest
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES

KEYS = ("family", "seed", "target_process", "target_block", "context_status")


def _normalized_keys(frame: pd.DataFrame) -> tuple[tuple[str, ...], ...]:
    rows = frame.loc[:, KEYS].copy()
    rows["seed"] = rows["seed"].astype(int).astype(str)
    rows["target_block"] = rows["target_block"].astype(int).astype(str)
    for col in ("family", "target_process", "context_status"):
        rows[col] = rows[col].astype(str)
    return tuple(sorted(tuple(row) for row in rows.itertuples(index=False, name=None)))


def aggregate(input_dir: str | Path, output_dir: str | Path):
    cfg = _config()
    root = Path(input_dir)
    files = list(root.rglob("context_geometry.csv"))
    if len(files) != len(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v17 aggregate requires one artifact per family")

    parts = []
    for path in files:
        try:
            parts.append(pd.read_csv(path))
        except pd.errors.EmptyDataError:
            pass
    frame = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(frame) != 72:
        raise ValueError(f"v17 must preserve the frozen 72-context denominator; got {len(frame)}")

    expected = _target_manifest()
    if _normalized_keys(frame) != _normalized_keys(expected):
        observed = set(_normalized_keys(frame))
        frozen = set(_normalized_keys(expected))
        missing = sorted(frozen - observed)[:10]
        extra = sorted(observed - frozen)[:10]
        raise ValueError(f"v17 denominator mismatch; missing={missing}, extra={extra}")

    pred, metrics = _evaluate(frame, cfg)
    result = {
        "purpose": "context_geometry_v17_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_contexts": 72,
        **metrics,
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / "context_geometry.csv", index=False)
    pred.to_csv(out / "cell_disjoint_predictions.csv", index=False)
    (out / "development_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(aggregate(args.input_dir, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
