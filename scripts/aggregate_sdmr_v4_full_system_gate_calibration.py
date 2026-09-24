#!/usr/bin/env python3
"""Aggregate SDMR v4 full-system gate calibration evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.full_system_calibration import (
    select_information_multiplier,
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
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    config=_load(config_path)
    activation=_load(activation_path)
    if activation.get("config_sha256")!=_sha256(config_path):
        raise ValueError("aggregate config hash mismatch")

    manifests=sorted(root.glob("**/manifest.json"))
    if len(manifests)!=int(args.expected_shards):
        raise ValueError(
            f"expected {args.expected_shards} calibration shards, found {len(manifests)}"
        )
    manifest_rows=[_load(p) for p in manifests]
    for item in manifest_rows:
        if item.get("status")!="development_calibration_evidence":
            raise ValueError("unexpected shard status")
        if item.get("config_sha256")!=_sha256(config_path):
            raise ValueError("shard config hash drift")
        if item.get("activation_sha256")!=_sha256(activation_path):
            raise ValueError("shard activation hash drift")

    summary_files=sorted(root.glob("**/summary.csv"))
    candidate_files=sorted(root.glob("**/candidates.csv"))
    fold_files=sorted(root.glob("**/fold_scores.csv"))
    expected=int(args.expected_shards)
    if not (len(summary_files)==len(candidate_files)==len(fold_files)==expected):
        raise ValueError("incomplete calibration shard outputs")

    summaries=pd.concat([pd.read_csv(p) for p in summary_files],ignore_index=True)
    candidates=pd.concat([pd.read_csv(p) for p in candidate_files],ignore_index=True)
    folds=pd.concat([pd.read_csv(p) for p in fold_files],ignore_index=True)

    expected_worlds=set(config["worlds"])
    expected_seeds=set(int(x) for x in config["seeds"]["calibration"])
    if set(summaries["world"].astype(str))!=expected_worlds:
        raise ValueError("calibration world denominator drift")
    if set(summaries["seed"].astype(int))!=expected_seeds:
        raise ValueError("calibration seed denominator drift")
    if summaries.duplicated(["world","seed"]).any():
        raise ValueError("duplicate calibration world/seed summaries")
    if len(summaries)!=len(expected_worlds)*len(expected_seeds):
        raise ValueError("unexpected calibration summary row count")

    expected_candidates=tuple(float(x) for x in config["candidate_multipliers"])
    if set(pd.to_numeric(candidates["multiplier"]).astype(float))!=set(expected_candidates):
        raise ValueError("candidate multiplier drift")
    if candidates.duplicated(["world","seed","multiplier"]).any():
        raise ValueError("duplicate calibration candidate cells")

    world_rates=(
        candidates.groupby(["multiplier","world"],sort=True)["authorized"]
        .mean()
        .rename("authorization_rate")
        .reset_index()
    )
    selection=config["calibration_selection"]
    decision=select_information_multiplier(
        world_rates,
        candidate_order=expected_candidates,
        max_w7_false_authorization=float(
            selection["max_w7_false_authorization_rate"]
        ),
        min_informative_world_authorization=float(
            selection["min_each_informative_control_authorization_rate"]
        ),
    )

    summaries.to_csv(outdir/"summary.csv",index=False)
    candidates.to_csv(outdir/"candidates.csv",index=False)
    folds.to_csv(outdir/"fold_scores.csv",index=False)
    world_rates.to_csv(outdir/"world_rates.csv",index=False)
    decision.candidate_summary.to_csv(
        outdir/"candidate_selection.csv",index=False
    )

    result={
        "program":config["program"],
        "status":"development_calibration_terminal",
        "passed":bool(decision.passed),
        "selected_multiplier":decision.selected_multiplier,
        "eligible_multipliers":list(decision.eligible_multipliers),
        "calibration_seed_min":min(expected_seeds),
        "calibration_seed_max":max(expected_seeds),
        "n_calibration_seeds":len(expected_seeds),
        "candidate_order":list(expected_candidates),
        "confirmation_open":False,
        "reserved_future_prospective_open":False,
    }
    (outdir/"decision.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    outputs=[
        "summary.csv","candidates.csv","fold_scores.csv",
        "world_rates.csv","candidate_selection.csv","decision.json",
    ]
    manifest={
        "program":config["program"],
        "status":"development_calibration_terminal",
        "passed":bool(decision.passed),
        "selected_multiplier":decision.selected_multiplier,
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
