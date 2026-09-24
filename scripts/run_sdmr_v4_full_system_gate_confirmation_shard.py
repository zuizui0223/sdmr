#!/usr/bin/env python3
"""Run one SDMR v4 full-system gate confirmation shard.

This runner is inert until a confirmation contract and activation receipt are
created after calibration has terminally selected exactly one multiplier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.full_system_calibration import (
    evaluate_full_system_information,
    evaluate_information_candidates,
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
    header=f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header+data).hexdigest()


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

    if config.get("program")!="sdmr-v4-full-system-gate-confirmation-v1":
        raise ValueError("wrong v4 confirmation contract")
    if config.get("status")!="frozen_pending_confirmation":
        raise ValueError("confirmation contract not frozen")
    if activation.get("purpose")!="execute_sdmr_v4_full_system_gate_confirmation_v1":
        raise ValueError("wrong confirmation activation")
    if activation.get("single_activation") is not True:
        raise ValueError("confirmation activation must be single-use")
    if activation.get("config_blob_sha")!=_git_blob_sha(config_path):
        raise ValueError("confirmation config blob SHA mismatch")
    if activation.get("calibration_terminal_passed") is not True:
        raise ValueError("calibration did not terminally pass")
    if activation.get("reserved_prospective_opened") is not False:
        raise ValueError("reserved prospective panel opened before confirmation")

    world=str(args.world)
    worlds=tuple(config["worlds"])
    if world not in worlds:
        raise ValueError("world outside confirmation contract")
    world_index=worlds.index(world)

    blocks=activation["seed_blocks"]
    block_index=int(args.seed_block)
    if block_index<0 or block_index>=len(blocks):
        raise ValueError("seed block outside confirmation activation")
    seeds=tuple(int(x) for x in blocks[block_index])
    declared=set(int(x) for x in config["seeds"])
    if not set(seeds).issubset(declared):
        raise ValueError("confirmation seed block drift")

    finite=config["finite_architecture"]
    selected=float(config["selected_multiplier"])
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    rows=[]
    folds=[]
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
        evaluation=evaluate_full_system_information(
            sampled,
            n_splits=int(finite["n_splits"]),
            split_mode=str(finite["split_mode"]),
            learner=str(finite["learner"]),
            hgb_profile=str(finite["hgb_profile"]),
            adequacy_floor=float(finite["adequacy_floor"]),
        )
        summary=evaluation.summary.copy()
        summary.insert(0,"sampling_seed",int(sampling_seed))
        summary.insert(0,"seed",ecological_seed)
        summary.insert(0,"world",world)
        candidate=evaluate_information_candidates(
            summary,
            multipliers=(selected,),
        )
        rows.append(candidate)

        fs=evaluation.fold_scores.copy()
        fs.insert(0,"sampling_seed",int(sampling_seed))
        fs.insert(0,"seed",ecological_seed)
        fs.insert(0,"world",world)
        folds.append(fs)

    results=pd.concat(rows,ignore_index=True)
    fold_scores=pd.concat(folds,ignore_index=True)
    results.to_csv(outdir/"results.csv",index=False)
    fold_scores.to_csv(outdir/"fold_scores.csv",index=False)

    manifest={
        "program":config["program"],
        "status":"development_confirmation_evidence",
        "config_sha256":_sha256(config_path),
        "activation_sha256":_sha256(activation_path),
        "selected_multiplier":selected,
        "world":world,
        "seed_block":block_index,
        "seeds":list(seeds),
        "outputs":{
            "results.csv":_sha256(outdir/"results.csv"),
            "fold_scores.csv":_sha256(outdir/"fold_scores.csv"),
        },
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
