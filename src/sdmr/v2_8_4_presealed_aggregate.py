"""Fail-closed v2.8.4 M-group aggregation wrapper.

The available path delegates to :mod:`sdmr.v2_8_4_presealed_runtime`.  If the
shared taxon-part precompute is scientifically unavailable, this wrapper emits a
legacy-compatible unavailable M shard directly, without requiring seven model
jobs and without treating the missing computation as technical evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v2_6_empirical_model_pool_worker import M_NAMES
from .v2_8_4_presealed_runtime import (
    COMPAT_M_SHARD_PURPOSE,
    PRECOMPUTE_PURPOSE,
    _load_runtime_design,
    aggregate_groups as _aggregate_available_groups,
)


def _copy_or_empty(source: Path, target: Path) -> None:
    if source.exists():
        target.write_bytes(source.read_bytes())
    else:
        pd.DataFrame().to_csv(target, index=False)


def aggregate_groups_resumable(
    *, runtime_design_path: str | Path, precompute_dir: str | Path,
    group_root: str | Path, scientific_execution_id: str, taxon: str,
    taxon_index: int, part_seed: int, M_name: str, output_dir: str | Path,
) -> dict[str, object]:
    _load_runtime_design(runtime_design_path)
    if str(M_name) not in M_NAMES:
        raise ValueError(f"v2.8.4 M must be one of {M_NAMES}")

    pre_root = Path(precompute_dir)
    pre = json.loads((pre_root / "contract.json").read_text(encoding="utf-8"))
    if pre.get("purpose") != PRECOMPUTE_PURPOSE:
        raise ValueError("v2.8.4 resumable aggregate received wrong precompute")
    for key, expected in (
        ("scientific_execution_id", str(scientific_execution_id)),
        ("taxon", str(taxon)),
        ("taxon_index", int(taxon_index)),
        ("part_seed", int(part_seed)),
    ):
        actual = pre.get(key)
        if isinstance(expected, int):
            actual = int(actual)
        if actual != expected:
            raise ValueError(f"v2.8.4 precompute identity mismatch: {key}")

    if pre.get("available") is True:
        return _aggregate_available_groups(
            runtime_design_path=runtime_design_path,
            precompute_dir=precompute_dir,
            group_root=group_root,
            scientific_execution_id=scientific_execution_id,
            taxon=taxon,
            taxon_index=taxon_index,
            part_seed=part_seed,
            M_name=M_name,
            output_dir=output_dir,
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for filename in (
        "predictor_coverage.csv",
        "evidence_balanced_partition_support.csv",
        "evidence_balanced_partition_attempts.csv",
        "audit_support.csv",
        "audit_pruning.csv",
        "base_audit_space.csv",
        "partition_presence.csv",
        *[f"partition_background__{name}.csv" for name in M_NAMES],
    ):
        _copy_or_empty(pre_root / filename, out / filename)

    for filename in (
        "base_fold_metrics.csv", "knockout_fold_metrics.csv", "selection_trace.csv"
    ):
        pd.DataFrame().to_csv(out / filename, index=False)
    pd.DataFrame([{
        "taxon": str(taxon),
        "M": str(M_name),
        "group": "shard",
        "status": "unavailable",
        "error": str(pre.get("unavailable_reason", "precompute_unavailable")),
    }]).to_csv(out / "worker_status.csv", index=False)

    result = {
        "purpose": COMPAT_M_SHARD_PURPOSE,
        "available": False,
        "unavailable_stage": str(pre.get("unavailable_stage", "precompute")),
        "unavailable_reason": str(
            pre.get("unavailable_reason", "precompute_unavailable")
        ),
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "M": str(M_name),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_used_for_partition_or_audit_selection": False,
        "primary_M_shard": True,
        "deterministic_successor": True,
        "v2_8_4_runtime_successor": True,
        "scientific_execution_id": str(scientific_execution_id),
        "M_shared_precompute_reused": True,
        "telemetry_used_for_scientific_selection": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runtime-design", required=True)
    p.add_argument("--precompute-dir", required=True)
    p.add_argument("--group-root", required=True)
    p.add_argument("--scientific-execution-id", required=True)
    p.add_argument("--taxon", required=True)
    p.add_argument("--taxon-index", type=int, required=True)
    p.add_argument("--part-seed", type=int, required=True)
    p.add_argument("--M", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    aggregate_groups_resumable(
        runtime_design_path=a.runtime_design,
        precompute_dir=a.precompute_dir,
        group_root=a.group_root,
        scientific_execution_id=a.scientific_execution_id,
        taxon=a.taxon,
        taxon_index=a.taxon_index,
        part_seed=a.part_seed,
        M_name=a.M,
        output_dir=a.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
