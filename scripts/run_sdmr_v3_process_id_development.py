#!/usr/bin/env python3
"""Run the frozen burned-seed SDMR v3 development panel."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.development import run_development_panel
from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_json(value):
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "development_only":
        raise ValueError("development runner requires status=development_only")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("development runner cannot reopen Product A")
    if tuple(payload.get("worlds", ())) != KNOWN_TRUTH_WORLDS:
        raise ValueError("development runner requires exact W1-W8 world order")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("development runner cannot consume a prospective contract")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = _load_contract(config_path)

    oracle = config["oracle"]
    occurrence = config["occurrence"]
    result = run_development_panel(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        oracle_margin=float(oracle["margin"]),
        oracle_sem_multiplier=float(oracle["sem_multiplier"]),
        oracle_baseline_r2_floor=float(oracle["baseline_r2_floor"]),
        oracle_required_r2_ceiling=float(oracle["required_r2_ceiling"]),
        occurrence_margin=float(occurrence["margin"]),
        occurrence_sem_multiplier=float(occurrence["sem_multiplier"]),
        occurrence_adequacy_floor=float(occurrence["adequacy_floor"]),
        logistic_C=float(occurrence["logistic_C"]),
    )

    outputs = {
        "comparison.csv": result.comparison,
        "world_summary.csv": result.world_summary,
        "state_confusion.csv": result.state_confusion,
    }
    for filename, frame in outputs.items():
        frame.to_csv(outdir / filename, index=False)

    metrics_payload = {
        "overall": result.metrics,
        "by_process": result.process_summary.to_dict(orient="records"),
        "by_world": result.world_metrics.to_dict(orient="records"),
    }
    metrics_path = outdir / "metrics.json"
    metrics_path.write_text(
        json.dumps(_clean_json(metrics_payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    files = ["comparison.csv", "world_summary.csv", "state_confusion.csv", "metrics.json"]
    manifest = {
        "program": config["program"],
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "seeds": config["seeds"],
        "worlds": config["worlds"],
        "outputs": {name: _sha256(outdir / name) for name in files},
    }
    manifest_path = outdir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
