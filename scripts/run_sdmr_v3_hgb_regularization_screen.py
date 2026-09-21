#!/usr/bin/env python3
"""Run the frozen SDMR v3 HGB regularization probability screen."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.hgb_regularization_screen import (
    HGB_PROFILES,
    run_hgb_regularization_screen,
    select_hgb_profile,
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
        raise ValueError("HGB screen requires development_only")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("HGB screen cannot reopen Product A")
    if payload.get("selection_uses_process_recovery") is not False:
        raise ValueError("HGB screen must forbid process-recovery selection")
    if tuple(payload.get("profiles", ())) != tuple(HGB_PROFILES):
        raise ValueError("HGB screen profile order differs from frozen code")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    return payload


def _summarize_test(rows: pd.DataFrame) -> pd.DataFrame:
    test = rows.loc[rows["dataset"].eq("test")].copy()
    metrics = [
        "balanced_log_score",
        "roc_auc",
        "balanced_brier",
        "extreme_fraction",
        "train_test_log_score_gap",
    ]
    return (
        test.groupby(["profile", "split_mode", "world"], sort=True)[metrics]
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

    rows = run_hgb_regularization_screen(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        split_modes=tuple(config["split_modes"]),
        profiles=tuple(config["profiles"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
    )
    summary = _summarize_test(rows)
    decision = select_hgb_profile(
        rows,
        adequacy_floor=float(config["adequacy_floor"]),
        tie_margin=float(config["tie_margin"]),
    )

    rows.to_csv(outdir / "fold_metrics.csv", index=False)
    summary.to_csv(outdir / "test_summary.csv", index=False)
    (outdir / "selection.json").write_text(
        json.dumps(_clean(decision), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics = {
        "selection": decision,
        "test_summary": summary.to_dict(orient="records"),
        "n_fold_rows": int(len(rows)),
    }
    (outdir / "metrics.json").write_text(
        json.dumps(_clean(metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    outputs = ["fold_metrics.csv", "test_summary.csv", "selection.json", "metrics.json"]
    manifest = {
        "program": config["program"],
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "selection_uses_process_recovery": False,
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
