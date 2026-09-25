#!/usr/bin/env python3
"""Run one blocked SDMR v5 full-pipeline integration shard."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.evidence import evaluate_occurrence_processes
from sdmr.process_id.known_truth.integration_v5 import (
    apply_permutation_authorization,
)
from sdmr.process_id.known_truth.occurrence_oracle import (
    evaluate_occurrence_oracle_states,
)
from sdmr.process_id.known_truth.permutation_gate import (
    evaluate_full_system_permutation_gate,
)
from sdmr.process_id.known_truth.resampling import resample_world_observations
from sdmr.process_id.known_truth.safety_audit import structural_refusal_expected
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


def _validate_activation(
    scientific_path: Path,
    execution_path: Path,
    activation_path: Path,
) -> tuple[dict,dict,dict]:
    scientific=_load(scientific_path)
    execution=_load(execution_path)
    activation=_load(activation_path)

    if scientific.get("program")!="sdmr-v6-full-pipeline-integration-v1":
        raise ValueError("wrong integration scientific contract")
    if execution.get("program")!="sdmr-v6-full-pipeline-integration-v1-execution":
        raise ValueError("wrong integration execution profile")
    if activation.get("purpose")!="execute_sdmr_v5_full_pipeline_integration_v1":
        raise ValueError("wrong integration activation")
    if activation.get("single_activation") is not True:
        raise ValueError("integration activation must be single-use")
    if activation.get("scientific_contract_blob_sha")!=_git_blob_sha(scientific_path):
        raise ValueError("integration scientific contract blob SHA mismatch")
    if activation.get("execution_profile_blob_sha")!=_git_blob_sha(execution_path):
        raise ValueError("integration execution profile blob SHA mismatch")

    validation=activation.get("validation_prerequisite",{})
    confirmation=activation.get("confirmation_prerequisite",{})
    if validation.get("terminal_passed") is not True:
        raise ValueError("v6 validation prerequisite did not pass")
    if confirmation.get("terminal_passed") is not True:
        raise ValueError("v6 confirmation prerequisite did not pass")
    if not str(validation.get("artifact_digest","")).startswith("sha256:"):
        raise ValueError("validation artifact digest missing")
    if not str(confirmation.get("artifact_digest","")).startswith("sha256:"):
        raise ValueError("confirmation artifact digest missing")
    if activation.get("prospective_opened_before_integration") is not False:
        raise ValueError("prospective panel opened before integration")
    if activation.get("fresh_empirical_opened") is not False:
        raise ValueError("fresh empirical data opened before integration")

    return scientific,execution,activation


def _unavailable_state_table(world, gate_summary: dict) -> pd.DataFrame:
    rows=[]
    for process in world.process_universe:
        rows.append({
            "process":str(process),
            "state":"unavailable",
            "reason":"full_system_not_informative",
            "full_log_score":float(gate_summary["observed_mean_score"]),
            "knockout_log_score":float("nan"),
            "delta_mean":float("nan"),
            "delta_sem":float("nan"),
            "closure_predictors":"",
        })
    frame=pd.DataFrame(rows)
    return apply_permutation_authorization(
        frame,
        authorized=False,
        observed_mean_score=float(gate_summary["observed_mean_score"]),
        mean_gain_over_null=float(gate_summary["mean_gain_over_null"]),
        p_value=float(gate_summary["p_value"]),
    )


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--scientific-contract",required=True)
    parser.add_argument("--execution-profile",required=True)
    parser.add_argument("--activation",required=True)
    parser.add_argument("--world",required=True)
    parser.add_argument("--seed-block",required=True,type=int)
    parser.add_argument("--outdir",required=True)
    args=parser.parse_args()

    scientific_path=Path(args.scientific_contract)
    execution_path=Path(args.execution_profile)
    activation_path=Path(args.activation)
    scientific,execution,activation=_validate_activation(
        scientific_path,execution_path,activation_path
    )

    world_name=str(args.world)
    worlds=tuple(scientific["worlds"])
    if world_name not in worlds:
        raise ValueError("world outside integration contract")
    world_index=worlds.index(world_name)

    block_index=int(args.seed_block)
    blocks=execution["sharding"]["seed_blocks"]
    if block_index<0 or block_index>=len(blocks):
        raise ValueError("seed block outside integration execution profile")
    seeds=tuple(int(x) for x in blocks[block_index])
    declared=set(int(x) for x in scientific["seeds"])
    if not set(seeds).issubset(declared):
        raise ValueError("integration seed block drift")

    stage_p_cfg=scientific["stage_p"]
    stage_t_cfg=scientific["stage_t"]
    odo_cfg=execution["odo_v2"]
    placeholder=execution["base_world_placeholders"]
    sampling_cfg=execution["sampling"]

    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    stage_p_frames=[]
    stage_t_frames=[]
    odo_frames=[]
    full_gate_rows=[]

    for ecological_seed in seeds:
        base_world=simulate_process_world(
            world_name,
            seed=ecological_seed,
            n_cells=int(stage_p_cfg["n_cells"]),
            n_occurrences=int(placeholder["n_occurrences"]),
            n_background=int(placeholder["n_background"]),
        )

        odo=evaluate_occurrence_oracle_states(
            base_world,
            n_splits=int(odo_cfg["n_splits"]),
            margin=float(odo_cfg["margin"]),
            sem_multiplier=float(odo_cfg["sem_multiplier"]),
            adequacy_floor=float(odo_cfg["adequacy_floor"]),
            approximation_tolerance=float(odo_cfg["approximation_tolerance"]),
            split_mode=str(odo_cfg["split_mode"]),
        ).states.copy()
        odo.insert(0,"seed",ecological_seed)
        odo.insert(0,"world",world_name)
        odo_frames.append(odo)

        sampling_seed=_sampling_seed(
            ecological_seed,
            world_index,
            int(sampling_cfg["multiplier"]),
            int(sampling_cfg["sampling_replicate"]),
        )
        sampled=resample_world_observations(
            base_world,
            n_occurrences=int(stage_p_cfg["n_occurrences"]),
            n_background=int(stage_p_cfg["n_background"]),
            sampling_seed=sampling_seed,
        )

        permutation=stage_p_cfg["permutation_gate"]
        gate_result=evaluate_full_system_permutation_gate(
            sampled,
            n_splits=int(stage_p_cfg["n_splits"]),
            split_mode=str(stage_p_cfg["split_mode"]),
            learner=str(stage_p_cfg["learner"]),
            hgb_profile=str(stage_p_cfg["hgb_profile"]),
            adequacy_floor=float(stage_p_cfg["adequacy_floor"]),
            n_permutations=int(permutation["n_permutations"]),
            alpha=float(permutation["alpha"]),
            permutation_seed=int(permutation["permutation_seed"]),
            minimum_gain_over_null=float(permutation["minimum_gain_over_null"]),
        )
        gate_summary=dict(gate_result.summary)
        gate_summary.update({
            "world":world_name,
            "seed":ecological_seed,
            "sampling_seed":sampling_seed,
        })
        full_gate_rows.append(gate_summary)

        if bool(gate_summary["authorized"]):
            p_states=evaluate_occurrence_processes(
                sampled,
                n_splits=int(stage_p_cfg["n_splits"]),
                margin=float(stage_p_cfg["margin"]),
                adequacy_floor=float(stage_p_cfg["adequacy_floor"]),
                sem_multiplier=1.0,
                C=1.0,
                learner=str(stage_p_cfg["learner"]),
                split_mode=str(stage_p_cfg["split_mode"]),
                hgb_profile=str(stage_p_cfg["hgb_profile"]),
                require_full_system_information=False,
            ).states
            p_states=apply_permutation_authorization(
                p_states,
                authorized=True,
                observed_mean_score=float(gate_summary["observed_mean_score"]),
                mean_gain_over_null=float(gate_summary["mean_gain_over_null"]),
                p_value=float(gate_summary["p_value"]),
            )
        else:
            p_states=_unavailable_state_table(sampled,gate_summary)

        t_states=evaluate_occurrence_processes(
            sampled,
            n_splits=int(stage_p_cfg["n_splits"]),
            margin=float(stage_p_cfg["margin"]),
            adequacy_floor=float(stage_p_cfg["adequacy_floor"]),
            sem_multiplier=1.0,
            C=1.0,
            learner=str(stage_p_cfg["learner"]),
            split_mode=str(stage_t_cfg["split_mode"]),
            hgb_profile=str(stage_p_cfg["hgb_profile"]),
            require_full_system_information=False,
        ).states

        odo_target=odo.loc[:,["process","state"]].rename(
            columns={"state":"odo_state"}
        )
        for states,stage_name,target in (
            (p_states,"P",stage_p_frames),
            (t_states,"T",stage_t_frames),
        ):
            merged=odo_target.merge(
                states,
                on="process",
                how="left",
                validate="one_to_one",
            ).rename(columns={"state":"finite_state"})
            merged.insert(
                0,
                "structural_refusal_expected",
                [
                    structural_refusal_expected(world_name,p)
                    for p in merged["process"].astype(str)
                ],
            )
            merged.insert(0,"sampling_seed",sampling_seed)
            merged.insert(0,"stage",stage_name)
            merged.insert(0,"seed",ecological_seed)
            merged.insert(0,"world",world_name)
            target.append(merged)

    stage_p=pd.concat(stage_p_frames,ignore_index=True)
    stage_t=pd.concat(stage_t_frames,ignore_index=True)
    odo=pd.concat(odo_frames,ignore_index=True)
    full_gate=pd.DataFrame(full_gate_rows)

    stage_p.to_csv(outdir/"stage_p_states.csv",index=False)
    stage_t.to_csv(outdir/"stage_t_states.csv",index=False)
    odo.to_csv(outdir/"odo_states.csv",index=False)
    full_gate.to_csv(outdir/"full_system_gate.csv",index=False)

    manifest={
        "program":scientific["program"],
        "status":"development_integration_evidence",
        "scientific_contract_sha256":_sha256(scientific_path),
        "execution_profile_sha256":_sha256(execution_path),
        "activation_sha256":_sha256(activation_path),
        "world":world_name,
        "seed_block":block_index,
        "seeds":list(seeds),
        "validation_artifact_digest":activation["validation_prerequisite"]["artifact_digest"],
        "confirmation_artifact_digest":activation["confirmation_prerequisite"]["artifact_digest"],
        "outputs":{
            name:_sha256(outdir/name)
            for name in (
                "stage_p_states.csv",
                "stage_t_states.csv",
                "odo_states.csv",
                "full_system_gate.csv",
            )
        },
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
