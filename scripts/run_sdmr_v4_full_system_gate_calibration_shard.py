#!/usr/bin/env python3
"""Run one frozen SDMR v4 full-system gate calibration shard."""
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


def _load(path: Path) -> dict:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("program")!="sdmr-v4-full-system-gate-calibration-v1":
        raise ValueError("wrong v4 calibration contract")
    if payload.get("status")!="development_only_frozen_before_outcomes":
        raise ValueError("v4 calibration contract not frozen")
    if payload["seed_use"]["calibration_open"] is not False:
        raise ValueError("frozen contract seed-use marker drift")
    return payload


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
    activation=json.loads(activation_path.read_text(encoding="utf-8"))

    if activation.get("purpose")!="execute_sdmr_v4_full_system_gate_calibration_v1":
        raise ValueError("wrong v4 calibration activation")
    if activation.get("single_activation") is not True:
        raise ValueError("calibration activation must be single-use")
    if activation.get("config_sha256")!=_sha256(config_path):
        raise ValueError("calibration activation config hash mismatch")
    if activation.get("confirmation_opened_before_calibration") is not False:
        raise ValueError("confirmation panel opened before calibration")
    if activation.get("reserved_prospective_opened") is not False:
        raise ValueError("reserved prospective panel was opened")

    world=str(args.world)
    worlds=tuple(config["worlds"])
    if world not in worlds:
        raise ValueError("world outside frozen calibration contract")
    world_index=worlds.index(world)

    calibration_seeds=tuple(int(x) for x in config["seeds"]["calibration"])
    blocks=activation["seed_blocks"]
    block_index=int(args.seed_block)
    if block_index<0 or block_index>=len(blocks):
        raise ValueError("seed block outside calibration activation")
    seeds=tuple(int(x) for x in blocks[block_index])
    if not set(seeds).issubset(set(calibration_seeds)):
        raise ValueError("seed block contains non-calibration seed")

    finite=config["finite_architecture"]
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    candidate_frames=[]
    summary_frames=[]
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
        summary.insert(0,"seed",int(ecological_seed))
        summary.insert(0,"world",world)
        summary_frames.append(summary)

        folds=evaluation.fold_scores.copy()
        folds.insert(0,"sampling_seed",int(sampling_seed))
        folds.insert(0,"seed",int(ecological_seed))
        folds.insert(0,"world",world)
        fold_frames.append(folds)

        candidates=evaluate_information_candidates(
            summary,
            multipliers=tuple(config["candidate_multipliers"]),
        )
        candidate_frames.append(candidates)

    summary_all=pd.concat(summary_frames,ignore_index=True)
    folds_all=pd.concat(fold_frames,ignore_index=True)
    candidates_all=pd.concat(candidate_frames,ignore_index=True)

    summary_all.to_csv(outdir/"summary.csv",index=False)
    folds_all.to_csv(outdir/"fold_scores.csv",index=False)
    candidates_all.to_csv(outdir/"candidates.csv",index=False)

    manifest={
        "program":config["program"],
        "status":"development_calibration_evidence",
        "config_sha256":_sha256(config_path),
        "activation_sha256":_sha256(activation_path),
        "world":world,
        "seed_block":block_index,
        "seeds":list(seeds),
        "outputs":{
            name:_sha256(outdir/name)
            for name in ("summary.csv","fold_scores.csv","candidates.csv")
        },
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
