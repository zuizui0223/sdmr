#!/usr/bin/env python3
"""Run one frozen SDMR v6 magnitude-permutation validation shard."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.permutation_gate import (
    evaluate_full_system_permutation_gate,
)
from sdmr.process_id.known_truth.resampling import resample_world_observations
from sdmr.process_id.known_truth.selected_power import _sampling_seed
from sdmr.process_id.known_truth.worlds import simulate_process_world


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def _git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("utf-8")+data
    ).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--activation",required=True)
    parser.add_argument("--world",required=True)
    parser.add_argument("--seed-block",required=True,type=int)
    parser.add_argument("--outdir",required=True)
    args=parser.parse_args()

    config_path=Path(args.config)
    activation_path=Path(args.activation)
    config=_load(config_path)
    activation=_load(activation_path)

    if config.get("program")!="sdmr-v6-magnitude-permutation-validation-v1":
        raise ValueError("wrong v6 validation contract")
    if config.get("status")!="development_only_frozen_before_outcomes":
        raise ValueError("v6 validation contract not frozen")
    if activation.get("purpose")!="execute_sdmr_v6_magnitude_permutation_validation_v1":
        raise ValueError("wrong v6 validation activation")
    if activation.get("single_activation") is not True:
        raise ValueError("v6 validation activation must be single-use")
    if activation.get("config_blob_sha")!=_git_blob_sha(config_path):
        raise ValueError("v6 validation config blob SHA mismatch")
    if activation.get("confirmation_opened_before_validation") is not False:
        raise ValueError("confirmation panel opened before validation")
    if activation.get("integration_opened_before_validation") is not False:
        raise ValueError("integration panel opened before validation")
    if activation.get("reserved_prospective_opened") is not False:
        raise ValueError("reserved prospective panel opened before validation")

    world=str(args.world)
    worlds=tuple(config["worlds"])
    if world not in worlds:
        raise ValueError("world outside frozen v6 validation contract")
    world_index=worlds.index(world)

    block_index=int(args.seed_block)
    blocks=activation["seed_blocks"]
    if block_index<0 or block_index>=len(blocks):
        raise ValueError("seed block outside activation")
    seeds=tuple(int(x) for x in blocks[block_index])
    declared=set(int(x) for x in config["seeds"]["validation"])
    if not set(seeds).issubset(declared):
        raise ValueError("validation seed block drift")

    finite=config["finite_architecture"]
    gate=config["authorization_gate"]
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    summary_rows=[]
    fold_frames=[]

    for ecological_seed in seeds:
        world_obj=simulate_process_world(
            world,
            seed=ecological_seed,
            n_cells=int(finite["n_cells"]),
            n_occurrences=int(finite["base_world_placeholder_occurrences"]),
            n_background=int(finite["base_world_placeholder_background"]),
        )
        sampling_seed=_sampling_seed(
            ecological_seed,
            world_index,
            int(finite["multiplier"]),
            int(finite["sampling_replicate"]),
        )
        sampled=resample_world_observations(
            world_obj,
            n_occurrences=int(finite["n_occurrences"]),
            n_background=int(finite["n_background"]),
            sampling_seed=sampling_seed,
        )
        result=evaluate_full_system_permutation_gate(
            sampled,
            n_splits=int(finite["n_splits"]),
            split_mode=str(finite["split_mode"]),
            learner=str(finite["learner"]),
            hgb_profile=str(finite["hgb_profile"]),
            adequacy_floor=float(finite["adequacy_floor"]),
            n_permutations=int(gate["n_permutations"]),
            alpha=float(gate["alpha"]),
            permutation_seed=int(gate["permutation_seed"]),
            minimum_gain_over_null=float(gate["minimum_gain_over_null"]),
        )

        row=dict(result.summary)
        row.update({
            "world":world,
            "seed":int(ecological_seed),
            "sampling_seed":int(sampling_seed),
        })
        summary_rows.append(row)

        folds=result.fold_scores.copy()
        folds.insert(0,"sampling_seed",int(sampling_seed))
        folds.insert(0,"seed",int(ecological_seed))
        folds.insert(0,"world",world)
        fold_frames.append(folds)

    summary=pd.DataFrame(summary_rows)
    folds=pd.concat(fold_frames,ignore_index=True)

    summary.to_csv(outdir/"summary.csv",index=False)
    folds.to_csv(outdir/"fold_scores.csv",index=False)

    manifest={
        "program":config["program"],
        "status":"development_validation_evidence",
        "config_sha256":_sha256(config_path),
        "activation_sha256":_sha256(activation_path),
        "world":world,
        "seed_block":block_index,
        "seeds":list(seeds),
        "outputs":{
            "summary.csv":_sha256(outdir/"summary.csv"),
            "fold_scores.csv":_sha256(outdir/"fold_scores.csv"),
        },
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
