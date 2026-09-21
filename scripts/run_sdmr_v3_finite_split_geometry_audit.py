#!/usr/bin/env python3
"""Run the frozen SDMR v3 finite split-geometry diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.finite_split_audit import (
    run_finite_split_geometry_audit,
)


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def _clean(value):
    if isinstance(value,dict):
        return {str(k):_clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [_clean(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):
        return None
    return value


def _load(path: Path) -> dict:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "development_only":
        raise ValueError("split audit requires development_only status")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("split audit cannot reopen Product A")
    if payload.get("learner") != "hgb":
        raise ValueError("split audit is frozen to hgb")
    if payload.get("split_modes") != ["spatial","random_cell"]:
        raise ValueError("split audit requires spatial and random_cell")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    odo=payload.get("odo_target",{})
    if odo.get("workflow_run") != 35495871747 or odo.get("artifact_id") != 10601311224:
        raise ValueError("split audit ODO target does not match frozen v2 target")
    if odo.get("split_mode") != "random":
        raise ValueError("split audit requires ODO v2 random crossfit target")
    return payload


def _by_world(states: pd.DataFrame) -> pd.DataFrame:
    positive={"contributory","required"}
    rows=[]
    for (split_mode,world),group in states.groupby(["split_mode","world"],sort=True):
        rows.append({
            "split_mode":str(split_mode),
            "world":str(world),
            "n_rows":int(len(group)),
            "positive_recovery":float(group["finite_state"].isin(positive).mean()),
            "unavailable_rate":float(group["finite_state"].eq("unavailable").mean()),
            "unresolved_rate":float(group["finite_state"].eq("unresolved").mean()),
            "replaceable_rate":float(group["finite_state"].eq("replaceable").mean()),
            "mean_full_log_score":float(pd.to_numeric(group["full_log_score"]).mean()),
            "mean_delta":float(pd.to_numeric(group["delta_mean"]).mean()),
            "mean_delta_sem":float(pd.to_numeric(group["delta_sem"]).mean()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--outdir",required=True)
    args=parser.parse_args()

    config_path=Path(args.config)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    config=_load(config_path)

    result=run_finite_split_geometry_audit(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        split_modes=tuple(config["split_modes"]),
        margin=float(config["margin"]),
        sem_multiplier=float(config["sem_multiplier"]),
        adequacy_floor=float(config["adequacy_floor"]),
        odo_approximation_tolerance=float(config["odo_target"]["approximation_tolerance"]),
        logistic_C=float(config["logistic_C"]),
    )
    by_world=_by_world(result.states)
    frames={
        "states.csv":result.states,
        "metrics.csv":result.metrics,
        "by_world.csv":by_world,
    }
    for name,frame in frames.items():
        frame.to_csv(outdir/name,index=False)

    payload={
        "overall":result.metrics.to_dict(orient="records"),
        "by_world":by_world.to_dict(orient="records"),
        "n_rows":int(len(result.states)),
    }
    (outdir/"metrics.json").write_text(
        json.dumps(_clean(payload),indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    outputs=list(frames)+["metrics.json"]
    manifest={
        "program":config["program"],
        "status":"development_only",
        "product_a_boundary":"closed_not_reopened",
        "config_path":str(config_path),
        "config_sha256":_sha256(config_path),
        "odo_target":config["odo_target"],
        "outputs":{name:_sha256(outdir/name) for name in outputs},
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
