#!/usr/bin/env python3
"""Run one frozen SDMR v6 magnitude-permutation confirmation shard."""
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
    d=hashlib.sha256()
    with path.open("rb") as h:
        for b in iter(lambda:h.read(1024*1024),b""):
            d.update(b)
    return d.hexdigest()


def _git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--activation",required=True)
    p.add_argument("--world",required=True)
    p.add_argument("--seed-block",required=True,type=int)
    p.add_argument("--outdir",required=True)
    args=p.parse_args()

    config_path=Path(args.config)
    activation_path=Path(args.activation)
    config=_load(config_path)
    activation=_load(activation_path)

    if config.get("program")!="sdmr-v6-magnitude-permutation-confirmation-v1":
        raise ValueError("wrong v6 confirmation contract")
    if config.get("status")!="frozen_pending_validation_prerequisite":
        raise ValueError("v6 confirmation contract not frozen")
    if activation.get("purpose")!="execute_sdmr_v6_magnitude_permutation_confirmation_v1":
        raise ValueError("wrong v6 confirmation activation")
    if activation.get("single_activation") is not True:
        raise ValueError("confirmation activation must be single-use")
    if activation.get("config_blob_sha")!=_git_blob_sha(config_path):
        raise ValueError("confirmation config blob SHA mismatch")
    if activation.get("validation_terminal_passed") is not True:
        raise ValueError("v6 validation prerequisite did not pass")
    if activation.get("integration_opened_before_confirmation") is not False:
        raise ValueError("integration panel opened before confirmation")
    if activation.get("reserved_prospective_opened") is not False:
        raise ValueError("prospective reserve opened before confirmation")

    world=str(args.world)
    worlds=tuple(config["worlds"])
    if world not in worlds:
        raise ValueError("world outside v6 confirmation contract")
    world_index=worlds.index(world)

    blocks=activation["seed_blocks"]
    bi=int(args.seed_block)
    if bi<0 or bi>=len(blocks):
        raise ValueError("seed block outside confirmation activation")
    seeds=tuple(int(x) for x in blocks[bi])
    if not set(seeds).issubset(set(int(x) for x in config["seeds"])):
        raise ValueError("confirmation seed block drift")

    finite=config["finite_architecture"]
    gate=config["authorization_gate"]
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
            ecological_seed,world_index,
            int(finite["multiplier"]),0,
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
        row.update({"world":world,"seed":ecological_seed,"sampling_seed":sampling_seed})
        rows.append(row)

        fs=result.fold_scores.copy()
        fs.insert(0,"sampling_seed",sampling_seed)
        fs.insert(0,"seed",ecological_seed)
        fs.insert(0,"world",world)
        folds.append(fs)

    summary=pd.DataFrame(rows)
    fold_scores=pd.concat(folds,ignore_index=True)
    summary.to_csv(outdir/"summary.csv",index=False)
    fold_scores.to_csv(outdir/"fold_scores.csv",index=False)

    manifest={
        "program":config["program"],
        "status":"development_confirmation_evidence",
        "config_sha256":_sha256(config_path),
        "activation_sha256":_sha256(activation_path),
        "validation_artifact_digest":activation["validation_artifact_digest"],
        "world":world,
        "seed_block":bi,
        "seeds":list(seeds),
        "outputs":{
            "summary.csv":_sha256(outdir/"summary.csv"),
            "fold_scores.csv":_sha256(outdir/"fold_scores.csv"),
        }
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
