#!/usr/bin/env python3
"""Aggregate SDMR v5 permutation-gate validation evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


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

    manifests=sorted(root.glob("**/manifest.json"))
    if len(manifests)!=int(args.expected_shards):
        raise ValueError(f"expected {args.expected_shards} validation shards, found {len(manifests)}")
    for path in manifests:
        item=_load(path)
        if item.get("status")!="development_validation_evidence":
            raise ValueError("unexpected v5 validation shard status")
        if item.get("config_sha256")!=_sha256(config_path):
            raise ValueError("v5 validation config hash drift")
        if item.get("activation_sha256")!=_sha256(activation_path):
            raise ValueError("v5 validation activation hash drift")

    summary_files=sorted(root.glob("**/summary.csv"))
    fold_files=sorted(root.glob("**/fold_scores.csv"))
    expected=int(args.expected_shards)
    if len(summary_files)!=expected or len(fold_files)!=expected:
        raise ValueError("incomplete v5 validation outputs")

    summary=pd.concat([pd.read_csv(p) for p in summary_files],ignore_index=True)
    folds=pd.concat([pd.read_csv(p) for p in fold_files],ignore_index=True)

    expected_worlds=set(config["worlds"])
    expected_seeds=set(int(x) for x in config["seeds"]["validation"])
    if set(summary["world"].astype(str))!=expected_worlds:
        raise ValueError("v5 validation world denominator drift")
    if set(summary["seed"].astype(int))!=expected_seeds:
        raise ValueError("v5 validation seed denominator drift")
    if summary.duplicated(["world","seed"]).any():
        raise ValueError("duplicate v5 validation cells")
    if len(summary)!=len(expected_worlds)*len(expected_seeds):
        raise ValueError("unexpected v5 validation row count")

    world_counts=(
        summary.groupby("world",sort=True)
        .agg(
            authorized_count=("authorized","sum"),
            denominator=("seed","size"),
            minimum_p_value=("p_value","min"),
            median_p_value=("p_value","median"),
            mean_gain=("mean_gain_over_null","mean"),
        )
        .reset_index()
    )

    validation=config["validation_gate"]
    w7=world_counts.loc[world_counts["world"].eq(config["null_world"])].iloc[0]
    informative=world_counts.loc[
        world_counts["world"].isin(config["informative_controls"])
    ].copy()
    failed_controls=informative.loc[
        informative["authorized_count"].astype(int)
        < int(validation["informative_control_min_authorized_count_each"]),
        "world",
    ].astype(str).tolist()

    passed=bool(
        int(w7["authorized_count"])<=int(validation["w7_max_authorized_count"])
        and not failed_controls
    )

    summary.to_csv(outdir/"summary.csv",index=False)
    folds.to_csv(outdir/"fold_scores.csv",index=False)
    world_counts.to_csv(outdir/"world_counts.csv",index=False)

    decision={
        "program":config["program"],
        "status":"development_validation_terminal",
        "passed":passed,
        "w7_authorized_count":int(w7["authorized_count"]),
        "failed_controls":failed_controls,
        "minimum_control_authorized_count":int(informative["authorized_count"].min()),
        "w6_report_only_authorized_count":int(
            world_counts.loc[
                world_counts["world"].eq(config["report_only_world"]),
                "authorized_count",
            ].iloc[0]
        ),
        "confirmation_open":False,
        "reserved_future_prospective_open":False,
    }
    (outdir/"decision.json").write_text(
        json.dumps(decision,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    outputs=["summary.csv","fold_scores.csv","world_counts.csv","decision.json"]
    manifest={
        "program":config["program"],
        "status":"development_validation_terminal",
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
