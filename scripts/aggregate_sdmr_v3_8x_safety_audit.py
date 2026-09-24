#!/usr/bin/env python3
"""Aggregate sharded SDMR v3 8x safety evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.safety_audit import summarize_safety


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _group_metrics(states: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    positive = {"contributory", "required"}
    sharp = {"replaceable", "contributory", "required"}
    rows = []
    for keys, group in states.groupby(group_cols, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys, strict=True))
        odo_positive = group["odo_state"].isin(positive)
        odo_replaceable = group["odo_state"].eq("replaceable")
        odo_unresolved = group["odo_state"].eq("unresolved")
        odo_unavailable = group["odo_state"].eq("unavailable")
        finite_positive = group["finite_state"].isin(positive)
        finite_sharp = group["finite_state"].isin(sharp)
        refusal = group["structural_refusal_expected"].astype(bool)
        record.update(
            {
                "n_rows": int(len(group)),
                "positive_recovery": (
                    float((odo_positive & finite_positive).sum() / odo_positive.sum())
                    if int(odo_positive.sum()) else float("nan")
                ),
                "false_positive_rate": (
                    float((odo_replaceable & finite_positive).sum() / odo_replaceable.sum())
                    if int(odo_replaceable.sum()) else float("nan")
                ),
                "overresolution_rate": (
                    float((odo_unresolved & finite_sharp).sum() / odo_unresolved.sum())
                    if int(odo_unresolved.sum()) else float("nan")
                ),
                "unavailable_favorable_rate": (
                    float((odo_unavailable & finite_positive).sum() / odo_unavailable.sum())
                    if int(odo_unavailable.sum()) else float("nan")
                ),
                "structural_refusal_violation_rate": (
                    float((refusal & finite_sharp).sum() / refusal.sum())
                    if int(refusal.sum()) else float("nan")
                ),
            }
        )
        rows.append(record)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--expected-shards", type=int, default=16)
    args = parser.parse_args()

    input_root = Path(args.input_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    state_files = sorted(input_root.glob("**/states.csv"))
    if len(state_files) != int(args.expected_shards):
        raise ValueError(
            f"expected {args.expected_shards} safety shards, found {len(state_files)}"
        )

    frames = []
    for path in state_files:
        frame = pd.read_csv(path)
        required = {
            "world", "seed", "process", "multiplier", "replicate",
            "hgb_profile", "structural_refusal_expected",
            "odo_state", "finite_state", "split_mode",
        }
        missing = sorted(required - set(frame.columns))
        if missing:
            raise KeyError(f"{path} missing columns: {missing}")
        frames.append(frame)

    states = pd.concat(frames, ignore_index=True)
    key = ["world", "seed", "process", "replicate", "split_mode"]
    if states.duplicated(key).any():
        raise ValueError("aggregated safety evidence contains duplicate cells")

    expected_rows = 8 * 8 * 6 * 3 * 2
    if len(states) != expected_rows:
        raise ValueError(
            f"expected {expected_rows} safety state rows, observed {len(states)}"
        )
    if set(states["multiplier"].astype(int)) != {8}:
        raise ValueError("aggregated safety multiplier drift")
    if set(states["hgb_profile"].astype(str)) != {"shallow3"}:
        raise ValueError("aggregated HGB profile drift")

    metrics = summarize_safety(states)
    by_world = _group_metrics(states, ["split_mode", "world"])
    by_process = _group_metrics(states, ["split_mode", "process"])
    confusion = (
        states.groupby(["split_mode", "odo_state", "finite_state"], sort=True)
        .size()
        .rename("count")
        .reset_index()
    )

    refusal = states.loc[states["structural_refusal_expected"].astype(bool)].copy()
    refusal_summary = (
        refusal.groupby(["split_mode", "world", "process", "finite_state"], sort=True)
        .size()
        .rename("count")
        .reset_index()
    )

    outputs = {
        "states.csv": states,
        "metrics.csv": metrics,
        "by_world.csv": by_world,
        "by_process.csv": by_process,
        "confusion.csv": confusion,
        "structural_refusal.csv": refusal_summary,
    }
    for name, frame in outputs.items():
        frame.to_csv(outdir / name, index=False)

    summary = {
        "program": "sdmr-v3-8x-safety-audit-v1",
        "status": "development_only",
        "n_state_rows": int(len(states)),
        "n_shards": int(len(state_files)),
        "metrics": metrics.to_dict(orient="records"),
    }
    (outdir / "summary.json").write_text(
        json.dumps(_clean(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    output_names = list(outputs) + ["summary.json"]
    manifest = {
        "program": "sdmr-v3-8x-safety-audit-v1",
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "outputs": {name: _sha256(outdir / name) for name in output_names},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
