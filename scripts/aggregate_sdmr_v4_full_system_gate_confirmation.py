#!/usr/bin/env python3
"""Aggregate the independent SDMR v4 gate confirmation panel."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.full_system_calibration import (
    evaluate_confirmation_panel,
)


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-root",required=True)
    parser.add_argument("--config",required=True)
    parser.add_argument("--activation",required=True)
    parser.add_argument("--outdir",required=True)
    parser.add_argument("--expected-shards",type=int,default=40)
    args=parser.parse_args()

    root=Path(args.input_root)
    config_path=Path(args.config)
    activation_path=Path(args.activation)
    config=_load(config_path)
    activation=_load(activation_path)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    if activation.get("config_sha256")!=_sha256(config_path):
        raise ValueError("confirmation aggregate config hash mismatch")

    manifests=sorted(root.glob("**/manifest.json"))
    if len(manifests)!=int(args.expected_shards):
        raise ValueError("unexpected confirmation shard count")
    for path in manifests:
        item=_load(path)
        if item.get("status")!="development_confirmation_evidence":
            raise ValueError("unexpected confirmation shard status")
        if item.get("config_sha256")!=_sha256(config_path):
            raise ValueError("confirmation shard config drift")
        if item.get("activation_sha256")!=_sha256(activation_path):
            raise ValueError("confirmation shard activation drift")
        if float(item.get("selected_multiplier"))!=float(config["selected_multiplier"]):
            raise ValueError("confirmation selected multiplier drift")

    result_files=sorted(root.glob("**/results.csv"))
    fold_files=sorted(root.glob("**/fold_scores.csv"))
    expected=int(args.expected_shards)
    if len(result_files)!=expected or len(fold_files)!=expected:
        raise ValueError("incomplete confirmation outputs")

    results=pd.concat([pd.read_csv(p) for p in result_files],ignore_index=True)
    folds=pd.concat([pd.read_csv(p) for p in fold_files],ignore_index=True)

    expected_worlds=set(config["worlds"])
    expected_seeds=set(int(x) for x in config["seeds"])
    if set(results["world"].astype(str))!=expected_worlds:
        raise ValueError("confirmation world denominator drift")
    if set(results["seed"].astype(int))!=expected_seeds:
        raise ValueError("confirmation seed denominator drift")
    if results.duplicated(["world","seed"]).any():
        raise ValueError("duplicate confirmation cells")
    if set(pd.to_numeric(results["multiplier"]).astype(float))!={float(config["selected_multiplier"])}:
        raise ValueError("confirmation multiplier drift")

    world_counts=(
        results.groupby("world",sort=True)
        .agg(
            authorized_count=("authorized","sum"),
            denominator=("seed","size"),
        )
        .reset_index()
    )
    gate=config["confirmation_gate"]
    decision=evaluate_confirmation_panel(
        world_counts,
        w7_max_authorized_count=int(gate["w7_max_authorized_count"]),
        informative_control_min_authorized_count=int(
            gate["informative_control_min_authorized_count_each"]
        ),
        expected_denominator=int(gate["informative_control_denominator_each"]),
    )

    results.to_csv(outdir/"results.csv",index=False)
    folds.to_csv(outdir/"fold_scores.csv",index=False)
    world_counts.to_csv(outdir/"world_counts.csv",index=False)

    payload={
        "program":config["program"],
        "status":"development_confirmation_terminal",
        "passed":bool(decision.passed),
        "selected_multiplier":float(config["selected_multiplier"]),
        "w7_authorized_count":decision.w7_authorized_count,
        "minimum_control_authorized_count":decision.minimum_control_authorized_count,
        "failed_controls":list(decision.failed_controls),
        "w6_report_only_authorized_count":decision.w6_report_only_authorized_count,
        "reserved_future_prospective_open":False,
    }
    (outdir/"decision.json").write_text(
        json.dumps(payload,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    outputs=["results.csv","fold_scores.csv","world_counts.csv","decision.json"]
    manifest={
        "program":config["program"],
        "status":"development_confirmation_terminal",
        "passed":bool(decision.passed),
        "selected_multiplier":float(config["selected_multiplier"]),
        "config_sha256":_sha256(config_path),
        "activation_sha256":_sha256(activation_path),
        "outputs":{name:_sha256(outdir/name) for name in outputs},
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
