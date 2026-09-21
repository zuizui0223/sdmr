#!/usr/bin/env python3
"""Run the frozen SDMR v3 finite probability-quality audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.probability_audit import (
    run_probability_quality_audit,
)


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


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "development_only":
        raise ValueError("probability-quality audit requires development_only")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("probability-quality audit cannot reopen Product A")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    if payload.get("learners") != ["linear", "hgb"]:
        raise ValueError("probability-quality audit learner panel must remain frozen")
    if payload.get("split_modes") != ["spatial", "random_cell"]:
        raise ValueError("probability-quality audit split panel must remain frozen")
    return payload


def _summarize(rows: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metrics = [
        "balanced_log_score",
        "roc_auc",
        "balanced_brier",
        "mean_p_positive",
        "mean_p_negative",
        "q01",
        "q05",
        "q50",
        "q95",
        "q99",
        "extreme_fraction",
        "train_test_log_score_gap",
    ]
    return (
        rows.groupby(group_cols, sort=True)[metrics]
        .mean()
        .reset_index()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = _load(config_path)

    rows = run_probability_quality_audit(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        learners=tuple(config["learners"]),
        split_modes=tuple(config["split_modes"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        C=float(config["logistic_C"]),
    )
    overall = _summarize(
        rows,
        ["learner", "split_mode", "dataset"],
    )
    by_world = _summarize(
        rows,
        ["learner", "split_mode", "dataset", "world"],
    )

    frames = {
        "fold_metrics.csv": rows,
        "overall.csv": overall,
        "by_world.csv": by_world,
    }
    for name, frame in frames.items():
        frame.to_csv(outdir / name, index=False)

    metrics_payload = {
        "overall": overall.to_dict(orient="records"),
        "by_world": by_world.to_dict(orient="records"),
        "n_fold_rows": int(len(rows)),
    }
    (outdir / "metrics.json").write_text(
        json.dumps(_clean(metrics_payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    outputs = list(frames) + ["metrics.json"]
    manifest = {
        "program": config["program"],
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "outputs": {name: _sha256(outdir / name) for name in outputs},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
