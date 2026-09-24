#!/usr/bin/env python3
"""Run one frozen shallow3 positive-recovery power-curve shard."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.selected_power import run_selected_power_curve


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean(value):
    if isinstance(value, dict):
        return {str(k):_clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [_clean(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):
        return None
    return value


def _load(path: Path) -> dict:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status")!="development_only":
        raise ValueError("power curve requires development_only")
    if payload.get("product_a_boundary")!="closed_not_reopened":
        raise ValueError("power curve cannot reopen Product A")
    if payload.get("hgb_profile")!="shallow3":
        raise ValueError("power curve requires frozen shallow3 profile")
    if payload.get("prospective_status")!="not_frozen":
        raise ValueError("prospective status must remain not_frozen")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    odo=payload.get("odo_target",{})
    if odo.get("workflow_run")!=35495871747 or odo.get("artifact_id")!=10601311224:
        raise ValueError("ODO v2 target drift")
    if odo.get("state_key_sha256")!="966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d":
        raise ValueError("ODO state hash drift")
    screen=payload.get("screen_target",{})
    if screen.get("workflow_run")!=35608090218 or screen.get("artifact_id")!=10644928842:
        raise ValueError("HGB screen target drift")
    if screen.get("selected_profile")!="shallow3":
        raise ValueError("HGB selected profile drift")
    if screen.get("selection_used_process_recovery") is not False:
        raise ValueError("HGB selection must remain process-outcome blind")
    return payload


def _group(states: pd.DataFrame, column: str) -> pd.DataFrame:
    positive={"contributory","required"}
    rows=[]
    for value, group in states.groupby(column,sort=True):
        rows.append({
            column:value,
            "n_rows":int(len(group)),
            "positive_recovery":float(group["finite_state"].isin(positive).mean()),
            "unresolved_rate":float(group["finite_state"].eq("unresolved").mean()),
            "replaceable_rate":float(group["finite_state"].eq("replaceable").mean()),
            "unavailable_rate":float(group["finite_state"].eq("unavailable").mean()),
            "mean_delta":float(pd.to_numeric(group["delta_mean"],errors="coerce").mean()),
            "mean_delta_sem":float(pd.to_numeric(group["delta_sem"],errors="coerce").mean()),
            "mean_full_log_score":float(pd.to_numeric(group["full_log_score"],errors="coerce").mean()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--outdir",required=True)
    parser.add_argument("--split-mode",required=True)
    parser.add_argument("--multiplier",required=True,type=int)
    args=parser.parse_args()

    config_path=Path(args.config)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    config=_load(config_path)
    split_mode=str(args.split_mode)
    multiplier=int(args.multiplier)
    if split_mode not in config["split_modes"]:
        raise ValueError("split mode outside frozen contract")
    if multiplier not in config["sample_multipliers"]:
        raise ValueError("multiplier outside frozen contract")
    odo=config["odo_target"]

    result=run_selected_power_curve(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        split_modes=(split_mode,),
        sample_multipliers=(multiplier,),
        sampling_replicates=tuple(config["sampling_replicates"]),
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

    states=result.states
    metrics=result.metrics
    by_world=_group(states,"world")
    by_process=_group(states,"process")
    frames={
        "states.csv":states,
        "metrics.csv":metrics,
        "by_world.csv":by_world,
        "by_process.csv":by_process,
    }
    for name,frame in frames.items():
        frame.to_csv(outdir/name,index=False)

    summary={
        "split_mode":split_mode,
        "multiplier":multiplier,
        "hgb_profile":config["hgb_profile"],
        "odo_state_hash":result.odo_state_hash,
        "n_state_rows":int(len(states)),
        "metrics":metrics.to_dict(orient="records"),
    }
    (outdir/"summary.json").write_text(
        json.dumps(_clean(summary),indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    outputs=list(frames)+["summary.json"]
    manifest={
        "program":config["program"],
        "status":"development_only",
        "product_a_boundary":"closed_not_reopened",
        "config_path":str(config_path),
        "config_sha256":_sha256(config_path),
        "split_mode":split_mode,
        "multiplier":multiplier,
        "hgb_profile":config["hgb_profile"],
        "odo_state_hash":result.odo_state_hash,
        "outputs":{name:_sha256(outdir/name) for name in outputs},
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
