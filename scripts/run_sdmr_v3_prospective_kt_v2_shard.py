#!/usr/bin/env python3
"""Run one frozen SDMR v3 prospective known-truth v2 shard.

This script requires an explicit activation receipt created only after the
frozen development prerequisite is terminally reviewed. Merely importing or
testing this script never opens prospective seeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.evidence import evaluate_occurrence_processes
from sdmr.process_id.known_truth.occurrence_oracle import (
    evaluate_occurrence_oracle_states,
)
from sdmr.process_id.known_truth.resampling import resample_world_observations
from sdmr.process_id.known_truth.safety_audit import structural_refusal_expected
from sdmr.process_id.known_truth.selected_power import _sampling_seed
from sdmr.process_id.known_truth.worlds import simulate_process_world


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_activation(
    contract_path: Path,
    execution_path: Path,
    activation_path: Path,
) -> tuple[dict, dict, dict]:
    contract = _load_json(contract_path)
    execution = _load_json(execution_path)
    activation = _load_json(activation_path)

    if contract.get("program") != "sdmr-v3-prospective-known-truth-v2":
        raise ValueError("wrong prospective KT scientific contract")
    if contract.get("activation_status") != "blocked":
        raise ValueError("scientific contract must remain immutable/blocked")
    if contract.get("prospective_outcomes_opened") is not False:
        raise ValueError("prospective outcomes were already marked opened")

    if (
        execution.get("program")
        != "sdmr-v3-prospective-known-truth-v2-execution-profile"
    ):
        raise ValueError("wrong prospective KT execution profile")
    if execution.get("activation_status") != "blocked":
        raise ValueError("execution profile must remain immutable/blocked")

    expected_contract_blob = str(execution["scientific_contract_blob_sha"])
    if activation.get("scientific_contract_blob_sha") != expected_contract_blob:
        raise ValueError("activation scientific contract blob SHA mismatch")

    if activation.get("scientific_contract_sha256") != _sha256(contract_path):
        raise ValueError("activation scientific contract content SHA mismatch")
    if activation.get("execution_profile_sha256") != _sha256(execution_path):
        raise ValueError("activation execution profile content SHA mismatch")

    prerequisite = contract["development_prerequisite"]
    if activation.get("development_prerequisite_run") != prerequisite["workflow_run"]:
        raise ValueError("activation prerequisite workflow drift")
    if activation.get("development_prerequisite_conclusion") != "success":
        raise ValueError("development prerequisite did not pass")
    if not str(activation.get("development_prerequisite_artifact_digest", "")).startswith(
        "sha256:"
    ):
        raise ValueError("development prerequisite artifact digest missing")
    if activation.get("approved_for_single_prospective_execution") is not True:
        raise ValueError("prospective execution is not explicitly approved")
    if activation.get("prospective_outcomes_opened_before_activation") is not False:
        raise ValueError("prospective outcomes were opened before activation")

    return contract, execution, activation


def _seed_block(execution: dict, block_index: int) -> tuple[int, ...]:
    blocks = execution["sharding"]["seed_blocks"]
    block_index = int(block_index)
    if block_index < 0 or block_index >= len(blocks):
        raise ValueError("seed block index outside frozen execution profile")
    return tuple(int(x) for x in blocks[block_index])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--execution-profile", required=True)
    parser.add_argument("--activation", required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--seed-block", required=True, type=int)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    contract_path = Path(args.contract)
    execution_path = Path(args.execution_profile)
    activation_path = Path(args.activation)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    contract, execution, activation = _validate_activation(
        contract_path, execution_path, activation_path
    )

    world_name = str(args.world)
    world_order = tuple(execution["sampling"]["world_index_order"])
    if world_name not in world_order:
        raise ValueError("world outside frozen prospective execution profile")
    if world_name not in contract["worlds"]:
        raise ValueError("world outside frozen scientific contract")
    world_index = world_order.index(world_name)

    seeds = _seed_block(execution, int(args.seed_block))
    declared_seed_set = set(int(x) for x in contract["seeds"]["values"])
    if not set(seeds).issubset(declared_seed_set):
        raise ValueError("seed block contains undeclared prospective seed")

    stage_p_cfg = contract["stage_p"]
    multiplier = int(execution["sampling"]["multiplier"])
    replicate = int(execution["sampling"]["sampling_replicate"])
    if multiplier != int(stage_p_cfg["multiplier"]):
        raise ValueError("execution multiplier differs from scientific contract")

    placeholder = execution["base_world_sample_placeholders"]
    odo_source = contract["source_freezes"]["odo_v2"]

    stage_p_frames = []
    stage_t_frames = []
    odo_frames = []

    for ecological_seed in seeds:
        world = simulate_process_world(
            world_name,
            seed=int(ecological_seed),
            n_cells=int(stage_p_cfg["n_cells"]),
            n_occurrences=int(placeholder["n_occurrences"]),
            n_background=int(placeholder["n_background"]),
        )

        odo = evaluate_occurrence_oracle_states(
            world,
            n_splits=int(stage_p_cfg["n_splits"]),
            margin=float(stage_p_cfg["margin"]),
            sem_multiplier=float(stage_p_cfg["sem_multiplier"]),
            baseline_r2_floor=0.80,
            required_r2_ceiling=0.0,
        ).copy()
        odo.insert(0, "seed", int(ecological_seed))
        odo.insert(0, "world", world_name)
        odo_frames.append(odo)

        sampling_seed = _sampling_seed(
            int(ecological_seed),
            int(world_index),
            multiplier,
            replicate,
        )
        sampled = resample_world_observations(
            world,
            n_occurrences=int(stage_p_cfg["n_occurrences"]),
            n_background=int(stage_p_cfg["n_background"]),
            sampling_seed=sampling_seed,
        )

        stage_p = evaluate_occurrence_processes(
            sampled,
            n_splits=int(stage_p_cfg["n_splits"]),
            margin=float(stage_p_cfg["margin"]),
            adequacy_floor=float(stage_p_cfg["adequacy_floor"]),
            sem_multiplier=float(stage_p_cfg["sem_multiplier"]),
            C=float(stage_p_cfg["logistic_C"]),
            learner=str(stage_p_cfg["learner"]),
            split_mode=str(stage_p_cfg["split_mode"]),
            hgb_profile=str(stage_p_cfg["hgb_profile"]),
            require_full_system_information=True,
        ).states.copy()

        stage_t = evaluate_occurrence_processes(
            sampled,
            n_splits=int(stage_p_cfg["n_splits"]),
            margin=float(stage_p_cfg["margin"]),
            adequacy_floor=float(stage_p_cfg["adequacy_floor"]),
            sem_multiplier=float(stage_p_cfg["sem_multiplier"]),
            C=float(stage_p_cfg["logistic_C"]),
            learner=str(stage_p_cfg["learner"]),
            split_mode=str(contract["stage_t"]["split_mode"]),
            hgb_profile=str(stage_p_cfg["hgb_profile"]),
            require_full_system_information=False,
        ).states.copy()

        odo_target = odo.loc[:, ["process", "state"]].rename(
            columns={"state": "odo_state"}
        )

        for frame, stage_name in ((stage_p, "P"), (stage_t, "T")):
            merged = odo_target.merge(
                frame,
                on="process",
                how="left",
                validate="one_to_one",
            ).rename(columns={"state": "finite_state"})
            merged.insert(
                0,
                "structural_refusal_expected",
                [
                    structural_refusal_expected(world_name, p)
                    for p in merged["process"].astype(str)
                ],
            )
            merged.insert(0, "sampling_seed", int(sampling_seed))
            merged.insert(0, "stage", stage_name)
            merged.insert(0, "seed", int(ecological_seed))
            merged.insert(0, "world", world_name)
            if stage_name == "P":
                stage_p_frames.append(merged)
            else:
                stage_t_frames.append(merged)

    stage_p_out = pd.concat(stage_p_frames, ignore_index=True)
    stage_t_out = pd.concat(stage_t_frames, ignore_index=True)
    odo_out = pd.concat(odo_frames, ignore_index=True)

    stage_p_out.to_csv(outdir / "stage_p_states.csv", index=False)
    stage_t_out.to_csv(outdir / "stage_t_states.csv", index=False)
    odo_out.to_csv(outdir / "odo_states.csv", index=False)

    manifest = {
        "program": contract["program"],
        "status": "prospective_evidence",
        "scientific_contract_sha256": _sha256(contract_path),
        "execution_profile_sha256": _sha256(execution_path),
        "activation_sha256": _sha256(activation_path),
        "development_prerequisite_artifact_digest": activation[
            "development_prerequisite_artifact_digest"
        ],
        "world": world_name,
        "seed_block": int(args.seed_block),
        "seeds": list(seeds),
        "n_stage_p_rows": int(len(stage_p_out)),
        "n_stage_t_rows": int(len(stage_t_out)),
        "n_odo_rows": int(len(odo_out)),
        "outputs": {
            name: _sha256(outdir / name)
            for name in (
                "stage_p_states.csv",
                "stage_t_states.csv",
                "odo_states.csv",
            )
        },
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
