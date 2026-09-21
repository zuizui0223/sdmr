#!/usr/bin/env python3
"""Run the frozen SDMR v3 finite-recovery capacity and power audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.finite_recovery_audit import (
    run_finite_recovery_audit,
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
        raise ValueError("finite-recovery audit requires development_only status")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("finite-recovery audit cannot reopen Product A")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    odo = payload.get("odo_target", {})
    if odo.get("workflow_run") != 35495871747:
        raise ValueError("ODO target workflow run does not match frozen v2 target")
    if odo.get("artifact_id") != 10601311224:
        raise ValueError("ODO target artifact does not match frozen v2 target")
    if odo.get("split_mode") != "random":
        raise ValueError("ODO v2 target requires random crossfit")
    return payload


def _group_metrics(states: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    positive = {"contributory", "required"}
    rows = []
    for keys, group in states.groupby(group_cols, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys, strict=True))
        record.update(
            {
                "n_rows": int(len(group)),
                "positive_recovery": float(group["finite_state"].isin(positive).mean()),
                "unresolved_rate": float(group["finite_state"].eq("unresolved").mean()),
                "replaceable_rate": float(group["finite_state"].eq("replaceable").mean()),
                "unavailable_rate": float(group["finite_state"].eq("unavailable").mean()),
                "mean_delta": float(pd.to_numeric(group["delta_mean"]).mean()),
                "mean_delta_sem": float(pd.to_numeric(group["delta_sem"]).mean()),
            }
        )
        rows.append(record)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = _load(config_path)
    odo = config["odo_target"]

    result = run_finite_recovery_audit(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        baseline_learners=tuple(config["baseline_learners"]),
        sample_multipliers=tuple(config["sample_multipliers"]),
        sampling_replicates=tuple(config["sampling_replicates"]),
        odo_margin=float(config["margin"]),
        odo_sem_multiplier=float(config["sem_multiplier"]),
        odo_adequacy_floor=float(config["adequacy_floor"]),
        odo_approximation_tolerance=float(odo["approximation_tolerance"]),
        finite_margin=float(config["margin"]),
        finite_sem_multiplier=float(config["sem_multiplier"]),
        finite_adequacy_floor=float(config["adequacy_floor"]),
        logistic_C=float(config["logistic_C"]),
    )

    frames = {
        "baseline_states.csv": result.baseline_states,
        "power_states.csv": result.power_states,
        "baseline_metrics.csv": result.baseline_metrics,
        "power_metrics.csv": result.power_metrics,
        "power_by_world.csv": _group_metrics(
            result.power_states, ["multiplier", "world"]
        ),
        "power_by_process.csv": _group_metrics(
            result.power_states, ["multiplier", "process"]
        ),
    }
    for name, frame in frames.items():
        frame.to_csv(outdir / name, index=False)

    metrics_payload = {
        "baseline": result.baseline_metrics.to_dict(orient="records"),
        "power": result.power_metrics.to_dict(orient="records"),
        "n_baseline_rows": int(len(result.baseline_states)),
        "n_power_rows": int(len(result.power_states)),
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
        "odo_target": config["odo_target"],
        "outputs": {name: _sha256(outdir / name) for name in outputs},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
