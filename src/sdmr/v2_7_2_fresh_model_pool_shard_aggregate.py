"""Aggregate three primary deterministic v2.7.2 M shards into one taxon×part worker."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from .v2_6_empirical_model_pool_worker import M_NAMES

SHARD_PURPOSE = "product_a_v2_7_2_fresh_model_pool_M_shard"
WORKER_PURPOSE = "product_a_v2_7_2_fresh_model_pool_worker"


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_unavailable(
    out: Path, *, taxon: str, taxon_index: int, part_seed: int,
    stage: str, error: str,
) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame().to_csv(out / "base_fold_metrics.csv", index=False)
    pd.DataFrame().to_csv(out / "knockout_fold_metrics.csv", index=False)
    pd.DataFrame().to_csv(out / "selection_trace.csv", index=False)
    pd.DataFrame([{
        "taxon": taxon, "group": "worker", "status": "unavailable", "error": error
    }]).to_csv(out / "worker_status.csv", index=False)
    pd.DataFrame().to_csv(out / "predictor_coverage.csv", index=False)
    result = {
        "purpose": WORKER_PURPOSE,
        "available": False,
        "unavailable_stage": str(stage),
        "unavailable_reason": str(error),
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": False,
        "assembled_from_three_primary_M_shards": True,
        "deterministic_successor": True,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def aggregate_fresh_model_pool_shards(
    *, shard_root: str | Path, taxon: str, taxon_index: int, part_seed: int,
    output_dir: str | Path,
) -> dict[str, object]:
    root = Path(shard_root)
    out = Path(output_dir)
    found: dict[str, tuple[dict, Path]] = {}
    for path in sorted(root.rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != SHARD_PURPOSE:
            continue
        if str(payload.get("taxon")) != str(taxon):
            continue
        if int(payload.get("taxon_index", -1)) != int(taxon_index):
            raise ValueError("v2.7.2 M-shard taxon index changed")
        if int(payload.get("part_seed", -1)) != int(part_seed):
            raise ValueError("v2.7.2 M-shard part seed changed")
        M_name = str(payload.get("M", ""))
        if M_name in found:
            raise ValueError(f"duplicate v2.7.2 M shard: {M_name}")
        found[M_name] = (payload, path.parent)

    if set(found) != set(M_NAMES):
        raise ValueError(
            f"expected exactly three frozen v2.7.2 M shards, found {sorted(found)}"
        )

    unavailable = [
        (name, c) for name, (c, _) in found.items() if c.get("available") is not True
    ]
    if unavailable:
        name, payload = sorted(unavailable)[0]
        return _write_unavailable(
            out,
            taxon=str(taxon),
            taxon_index=int(taxon_index),
            part_seed=int(part_seed),
            stage=str(payload.get("unavailable_stage", "M_shard_unavailable")),
            error=f"{name}:{payload.get('unavailable_reason', 'M_shard_unavailable')}",
        )

    reference = found[M_NAMES[0]][0]
    identity_keys = (
        "partition_seed", "selected_assignment_attempt", "n_admissible_predictors",
        "admissible_predictors", "audit_predictors", "audit_processes",
        "model_random_state", "selection_process_numpy_seed",
    )
    for name in M_NAMES[1:]:
        payload = found[name][0]
        for key in identity_keys:
            if payload.get(key) != reference.get(key):
                raise ValueError(f"v2.7.2 M shards disagree on shared identity: {key}")
        if payload.get("primary_M_shard") is not True or payload.get("deterministic_successor") is not True:
            raise ValueError("v2.7.2 aggregate received a non-primary/non-deterministic shard")
        for key in (
            "sealed_occurrence_environment_read", "sealed_occurrence_used_for_selection",
            "sealed_occurrence_used_for_process_status",
            "candidate_scores_used_for_partition_or_audit_selection",
        ):
            if payload.get(key) is not False:
                raise ValueError(f"v2.7.2 M shard crossed frozen barrier: {key}")

    shared_files = [
        "predictor_coverage.csv",
        "evidence_balanced_partition_support.csv",
        "evidence_balanced_partition_attempts.csv",
        "audit_support.csv",
        "audit_pruning.csv",
        "base_audit_space.csv",
        "partition_presence.csv",
        *[f"partition_background__{name}.csv" for name in M_NAMES],
    ]
    for filename in shared_files:
        hashes = {_sha(found[name][1] / filename) for name in M_NAMES}
        if len(hashes) != 1:
            raise ValueError(
                f"deterministic v2.7.2 M shards disagree byte-for-byte on shared file: {filename}"
            )

    out.mkdir(parents=True, exist_ok=True)
    for filename in shared_files:
        shutil.copy2(found[M_NAMES[0]][1] / filename, out / filename)

    for filename in (
        "base_fold_metrics.csv", "knockout_fold_metrics.csv",
        "selection_trace.csv", "worker_status.csv",
    ):
        frames = [_read_csv_or_empty(found[name][1] / filename) for name in M_NAMES]
        nonempty = [frame for frame in frames if not frame.empty]
        (pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()).to_csv(
            out / filename, index=False
        )

    result = {
        "purpose": WORKER_PURPOSE,
        "available": True,
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "M_specs": list(M_NAMES),
        "partition_seed": int(reference["partition_seed"]),
        "selected_assignment_attempt": int(reference["selected_assignment_attempt"]),
        "n_admissible_predictors": int(reference["n_admissible_predictors"]),
        "admissible_predictors": list(reference["admissible_predictors"]),
        "audit_predictors": list(reference["audit_predictors"]),
        "audit_processes": list(reference["audit_processes"]),
        "model_random_state": int(reference["model_random_state"]),
        "selection_process_numpy_seed": int(reference["selection_process_numpy_seed"]),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": True,
        "candidate_scores_used_for_partition_or_audit_selection": False,
        "assembled_from_three_primary_M_shards": True,
        "shared_partition_and_audit_ledgers_byte_identical": True,
        "deterministic_successor": True,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--shard-root", required=True)
    p.add_argument("--taxon", required=True)
    p.add_argument("--taxon-index", type=int, required=True)
    p.add_argument("--part-seed", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    aggregate_fresh_model_pool_shards(
        shard_root=a.shard_root,
        taxon=a.taxon,
        taxon_index=a.taxon_index,
        part_seed=a.part_seed,
        output_dir=a.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
