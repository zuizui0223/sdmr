#!/usr/bin/env python3
"""Run the frozen SDMR v3 selected nonlinear recovery retest."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.selected_recovery import (
    run_selected_recovery_retest,
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
        raise ValueError("selected recovery requires development_only status")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("selected recovery cannot reopen Product A")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    if payload.get("hgb_profile") != "shallow3":
        raise ValueError("selected recovery requires frozen shallow3 profile")
    screen = payload.get("screen_target", {})
    if screen.get("workflow_run") != 35608090218:
        raise ValueError("screen workflow target drift")
    if screen.get("artifact_id") != 10644928842:
        raise ValueError("screen artifact target drift")
    if screen.get("selected_profile") != "shallow3":
        raise ValueError("screen selection drift")
    if screen.get("selection_used_process_recovery") is not False:
        raise ValueError("screen selection must remain process-outcome blind")
    odo = payload.get("odo_target", {})
    if odo.get("workflow_run") != 35495871747:
        raise ValueError("ODO workflow target drift")
    if odo.get("artifact_id") != 10601311224:
        raise ValueError("ODO artifact target drift")
    if odo.get("split_mode") != "random":
        raise ValueError("ODO v2 target requires random crossfit")
    if not str(odo.get("state_key_sha256", "")).strip():
        raise ValueError("ODO state hash must be frozen")
    return payload


def _by_world(states: pd.DataFrame) -> pd.DataFrame:
    positive = {"contributory", "required"}
    sharp = {"replaceable", "contributory", "required"}
    rows = []
    for keys, group in states.groupby(
        ["learner", "split_mode", "world"], sort=True
    ):
        learner, split_mode, world = keys
        odo_positive = group["odo_state"].isin(positive)
        odo_replaceable = group["odo_state"].eq("replaceable")
        odo_unresolved = group["odo_state"].eq("unresolved")
        finite_positive = group["finite_state"].isin(positive)
        finite_sharp = group["finite_state"].isin(sharp)
        rows.append(
            {
                "learner": learner,
                "split_mode": split_mode,
                "world": world,
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
                "mean_positive_delta": float(
                    pd.to_numeric(
                        group.loc[odo_positive, "delta_mean"], errors="coerce"
                    ).mean()
                ),
                "mean_positive_full_log_score": float(
                    pd.to_numeric(
                        group.loc[odo_positive, "full_log_score"], errors="coerce"
                    ).mean()
                ),
            }
        )
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

    result = run_selected_recovery_retest(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        learners=tuple(config["learners"]),
        split_modes=tuple(config["split_modes"]),
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
        expected_odo_state_hash=str(odo["state_key_sha256"]),
    )

    states_path = outdir / "states.csv"
    metrics_path = outdir / "metrics.csv"
    by_world_path = outdir / "by_world.csv"
    result.states.to_csv(states_path, index=False)
    result.metrics.to_csv(metrics_path, index=False)
    by_world = _by_world(result.states)
    by_world.to_csv(by_world_path, index=False)

    summary = {
        "odo_state_hash": result.odo_state_hash,
        "hgb_profile": config["hgb_profile"],
        "screen_target": config["screen_target"],
        "odo_target": config["odo_target"],
        "metrics": result.metrics.to_dict(orient="records"),
        "n_state_rows": int(len(result.states)),
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(
        json.dumps(_clean(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    outputs = ["states.csv", "metrics.csv", "by_world.csv", "summary.json"]
    manifest = {
        "program": config["program"],
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "odo_state_hash": result.odo_state_hash,
        "hgb_profile": config["hgb_profile"],
        "outputs": {name: _sha256(outdir / name) for name in outputs},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
