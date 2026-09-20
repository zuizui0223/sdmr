#!/usr/bin/env python3
"""Run the frozen SDMR v3 positive-evidence development audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.positive_audit import run_positive_evidence_audit


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "diagnostic_only":
        raise ValueError("positive audit requires status=diagnostic_only")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("positive audit cannot reopen Product A")
    if payload.get("seeds_reused_only_as_burned_development_evidence") is not True:
        raise ValueError("positive audit must use already-burned development evidence")
    if payload.get("worlds") != ["unique_process", "interaction", "geographic_shift"]:
        raise ValueError("positive audit requires exact positive-world set")
    if payload.get("learners") != ["linear", "quadratic"]:
        raise ValueError("positive audit requires exact learner pair")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("positive audit cannot consume prospective evidence")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    return payload


def _summary_json(summary: pd.DataFrame) -> dict:
    by_boundary = (
        summary.groupby(["learner", "diagnostic_boundary"], dropna=False)
        .size().rename("count").reset_index()
    )
    by_world = (
        summary.groupby(["learner", "world", "diagnostic_boundary"], dropna=False)
        .size().rename("count").reset_index()
    )
    by_process = (
        summary.groupby(["learner", "process", "diagnostic_boundary"], dropna=False)
        .size().rename("count").reset_index()
    )
    deltas = (
        summary.groupby(["learner", "world"], dropna=False)
        .agg(
            n_cells=("process", "size"),
            mean_delta=("delta_mean", "mean"),
            median_delta=("delta_mean", "median"),
            mean_sem=("delta_sem", "mean"),
        )
        .reset_index()
    )
    return {
        "n_summary_rows": int(len(summary)),
        "by_boundary": by_boundary.to_dict(orient="records"),
        "by_world_boundary": by_world.to_dict(orient="records"),
        "by_process_boundary": by_process.to_dict(orient="records"),
        "delta_summary": deltas.to_dict(orient="records"),
    }


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
    result = run_positive_evidence_audit(
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

    result.summary.to_csv(outdir / "positive_summary.csv", index=False)
    result.folds.to_csv(outdir / "positive_folds.csv", index=False)
    result.boundary_counts.to_csv(outdir / "boundary_counts.csv", index=False)
    metrics_path = outdir / "audit_metrics.json"
    metrics_path.write_text(
        json.dumps(_summary_json(result.summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    output_names = [
        "positive_summary.csv",
        "positive_folds.csv",
        "boundary_counts.csv",
        "audit_metrics.json",
    ]
    manifest = {
        "program": config["program"],
        "status": "diagnostic_only",
        "product_a_boundary": "closed_not_reopened",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "seeds": config["seeds"],
        "worlds": config["worlds"],
        "learners": config["learners"],
        "outputs": {name: _sha256(outdir / name) for name in output_names},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
