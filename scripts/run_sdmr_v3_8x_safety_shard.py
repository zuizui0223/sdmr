#!/usr/bin/env python3
"""Run one frozen SDMR v3 8x safety-audit shard."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.safety_audit import run_8x_safety_audit


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
        raise ValueError("8x safety audit requires development_only")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("8x safety audit cannot reopen Product A")
    if payload.get("multiplier") != 8:
        raise ValueError("8x safety audit multiplier drift")
    if payload.get("hgb_profile") != "shallow3":
        raise ValueError("8x safety audit requires shallow3")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    odo = payload.get("odo_target", {})
    if odo.get("workflow_run") != 35495871747 or odo.get("artifact_id") != 10601311224:
        raise ValueError("ODO v2 target drift")
    if odo.get("state_key_sha256") != "966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d":
        raise ValueError("ODO full state hash drift")
    hashes = odo.get("world_state_sha256", {})
    if set(hashes) != set(payload.get("worlds", [])):
        raise ValueError("world-level ODO hash registry incomplete")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--split-mode", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = _load(config_path)

    world = str(args.world)
    split_mode = str(args.split_mode)
    if world not in config["worlds"]:
        raise ValueError("world outside frozen safety contract")
    if split_mode not in config["split_modes"]:
        raise ValueError("split mode outside frozen safety contract")

    odo = config["odo_target"]
    result = run_8x_safety_audit(
        seeds=tuple(config["seeds"]),
        worlds=(world,),
        split_modes=(split_mode,),
        sampling_replicates=tuple(config["sampling_replicates"]),
        multiplier=int(config["multiplier"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        hgb_profile=str(config["hgb_profile"]),
        odo_margin=float(config["margin"]),
        odo_sem_multiplier=float(config["sem_multiplier"]),
        odo_adequacy_floor=float(config["adequacy_floor"]),
        odo_approximation_tolerance=float(odo["approximation_tolerance"]),
        finite_margin=float(config["margin"]),
        finite_sem_multiplier=float(config["sem_multiplier"]),
        finite_adequacy_floor=float(config["adequacy_floor"]),
        logistic_C=float(config["logistic_C"]),
        expected_odo_state_hash=str(odo["world_state_sha256"][world]),
        sampling_world_indices={world: int(config["worlds"].index(world))},
    )

    states_path = outdir / "states.csv"
    metrics_path = outdir / "metrics.csv"
    result.states.to_csv(states_path, index=False)
    result.metrics.to_csv(metrics_path, index=False)

    confusion = (
        result.states.groupby(["odo_state", "finite_state"], sort=True)
        .size()
        .rename("count")
        .reset_index()
    )
    confusion_path = outdir / "confusion.csv"
    confusion.to_csv(confusion_path, index=False)

    summary = {
        "world": world,
        "split_mode": split_mode,
        "multiplier": int(config["multiplier"]),
        "hgb_profile": config["hgb_profile"],
        "odo_world_state_hash": result.odo_state_hash,
        "n_state_rows": int(len(result.states)),
        "metrics": result.metrics.to_dict(orient="records"),
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(
        json.dumps(_clean(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    outputs = ["states.csv", "metrics.csv", "confusion.csv", "summary.json"]
    manifest = {
        "program": config["program"],
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "world": world,
        "split_mode": split_mode,
        "odo_world_state_hash": result.odo_state_hash,
        "outputs": {name: _sha256(outdir / name) for name in outputs},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
