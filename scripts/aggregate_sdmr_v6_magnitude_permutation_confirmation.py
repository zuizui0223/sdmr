#!/usr/bin/env python3
"""Aggregate SDMR v6 magnitude-permutation confirmation evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def _sha256(path: Path) -> str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for b in iter(lambda:h.read(1024*1024),b""):
            d.update(b)
    return d.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--input-root",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--activation",required=True)
    p.add_argument("--outdir",required=True)
    p.add_argument("--expected-shards",type=int,default=40)
    args=p.parse_args()

    root=Path(args.input_root)
    config_path=Path(args.config)
    activation_path=Path(args.activation)
    config=_load(config_path)
    activation=_load(activation_path)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    manifests=sorted(root.glob("**/manifest.json"))
    if len(manifests)!=int(args.expected_shards):
        raise ValueError("unexpected v6 confirmation shard count")
    for path in manifests:
        item=_load(path)
        if item.get("status")!="development_confirmation_evidence":
            raise ValueError("unexpected v6 confirmation shard status")
        if item.get("config_sha256")!=_sha256(config_path):
            raise ValueError("v6 confirmation config drift")
        if item.get("activation_sha256")!=_sha256(activation_path):
            raise ValueError("v6 confirmation activation drift")
        if item.get("validation_artifact_digest")!=activation["validation_artifact_digest"]:
            raise ValueError("v6 validation provenance drift")

    summary_files=sorted(root.glob("**/summary.csv"))
    fold_files=sorted(root.glob("**/fold_scores.csv"))
    expected=int(args.expected_shards)
    if len(summary_files)!=expected or len(fold_files)!=expected:
        raise ValueError("incomplete v6 confirmation outputs")

    summary=pd.concat([pd.read_csv(x) for x in summary_files],ignore_index=True)
    folds=pd.concat([pd.read_csv(x) for x in fold_files],ignore_index=True)

    expected_worlds=set(config["worlds"])
    expected_seeds=set(int(x) for x in config["seeds"])
    if set(summary["world"].astype(str))!=expected_worlds:
        raise ValueError("v6 confirmation world denominator drift")
    if set(summary["seed"].astype(int))!=expected_seeds:
        raise ValueError("v6 confirmation seed denominator drift")
    if summary.duplicated(["world","seed"]).any():
        raise ValueError("duplicate v6 confirmation cells")

    world_counts=(
        summary.groupby("world",sort=True)
        .agg(
            authorized_count=("authorized","sum"),
            denominator=("seed","size"),
            minimum_p_value=("p_value","min"),
            minimum_gain=("mean_gain_over_null","min"),
            median_gain=("mean_gain_over_null","median"),
        )
        .reset_index()
    )

    gate=config["confirmation_gate"]
    w7=world_counts.loc[world_counts["world"].eq(config["null_world"])].iloc[0]
    informative=world_counts.loc[
        world_counts["world"].isin(config["informative_controls"])
    ]
    failed=informative.loc[
        informative["authorized_count"].astype(int)
        < int(gate["informative_control_min_authorized_count_each"]),
        "world",
    ].astype(str).tolist()
    passed=bool(int(w7["authorized_count"])<=0 and not failed)

    summary.to_csv(outdir/"summary.csv",index=False)
    folds.to_csv(outdir/"fold_scores.csv",index=False)
    world_counts.to_csv(outdir/"world_counts.csv",index=False)

    decision={
        "program":config["program"],
        "status":"development_confirmation_terminal",
        "passed":passed,
        "w7_authorized_count":int(w7["authorized_count"]),
        "failed_controls":failed,
        "minimum_control_authorized_count":int(informative["authorized_count"].min()),
        "w6_report_only_authorized_count":int(
            world_counts.loc[
                world_counts["world"].eq(config["report_only_world"]),
                "authorized_count",
            ].iloc[0]
        ),
        "integration_open":False,
        "reserved_future_prospective_open":False,
    }
    (outdir/"decision.json").write_text(
        json.dumps(decision,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    outputs=["summary.csv","fold_scores.csv","world_counts.csv","decision.json"]
    manifest={
        "program":config["program"],
        "status":"development_confirmation_terminal",
        "passed":passed,
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
