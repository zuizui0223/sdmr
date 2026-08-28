"""Truth-blind runtime calibration receipts for Product-A v2.8.4.

This module intentionally never reads fold metrics, selection traces, or sealed
artifacts.  It converts execution status, runtime telemetry, and barrier-only
group contracts into technical calibration receipts, then aggregates the exact
predeclared 3-M by 7-group denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
from pathlib import Path


PURPOSE = "product_a_v2_8_4_runtime_calibration_v1"
RECEIPT_PURPOSE = "product_a_v2_8_4_runtime_calibration_group_receipt"
DECISION_PURPOSE = "product_a_v2_8_4_runtime_calibration_decision"
GROUPS = (
    "base",
    "thermal",
    "water",
    "seasonality_phenology",
    "energy_productivity",
    "snow",
    "wind",
)
M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")
BARRIER_KEYS = (
    "sealed_occurrence_environment_read",
    "sealed_occurrence_used_for_selection",
    "sealed_occurrence_used_for_process_status",
    "candidate_scores_used_for_partition_or_audit_selection",
    "scientific_promotion_allowed",
    "product_b_unblocked",
)


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("wrong v2.8.4 runtime calibration contract")
    workload = payload.get("workload", {})
    if tuple(workload.get("M", ())) != M_NAMES:
        raise ValueError("runtime calibration M denominator changed")
    if tuple(workload.get("evaluation_groups", ())) != GROUPS:
        raise ValueError("runtime calibration group denominator changed")
    if int(workload.get("cell_count", -1)) != len(M_NAMES) * len(GROUPS):
        raise ValueError("runtime calibration cell count changed")
    barrier = payload.get("information_barrier", {})
    for key in (
        "sealed_artifact_downloaded",
        "sealed_ecological_outcomes_read",
        "telemetry_used_for_scientific_selection",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"runtime calibration crossed information barrier: {key}")
    boundary = payload.get("execution_boundary", {})
    if boundary.get("runtime_calibration_allowed") is not True:
        raise ValueError("runtime calibration execution is not authorized by its contract")
    for key in (
        "scientific_presealed_execution_allowed",
        "sealed_execution_allowed",
        "workflow_dispatch_allowed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if boundary.get(key) is not False:
            raise ValueError(f"runtime calibration crossed execution boundary: {key}")
    return payload


def write_environment_receipt(contract_path: str | Path, output_path: str | Path) -> dict:
    contract = load_contract(contract_path)
    expected = contract["runtime_environment"]["direct_dependencies"]
    versions = {name: importlib.metadata.version(name) for name in expected}
    if versions != expected:
        raise ValueError(f"runtime calibration dependency identity changed: {versions}")
    payload = {
        "purpose": "product_a_v2_8_4_runtime_calibration_environment",
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "runner_image_os": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "dependencies": versions,
    }
    if payload["python_version"] != contract["runtime_environment"]["python_patch"]:
        raise ValueError("runtime calibration Python patch changed")
    payload["environment_digest"] = hashlib.sha256(_canonical(payload)).hexdigest()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def write_group_receipt(
    *, contract_path: str | Path, group_output_dir: str | Path,
    environment_receipt_path: str | Path, M_name: str, evaluation_group: str,
    return_code: int, wall_elapsed_seconds: float, output_path: str | Path,
) -> dict:
    contract = load_contract(contract_path)
    if M_name not in M_NAMES or evaluation_group not in GROUPS:
        raise ValueError("runtime calibration group identity is not frozen")
    environment = json.loads(Path(environment_receipt_path).read_text(encoding="utf-8"))
    root = Path(group_output_dir)
    status = "completed" if int(return_code) == 0 else (
        "calibration_ceiling_reached" if int(return_code) in {124, 137} else "engineering_failure"
    )
    receipt = {
        "purpose": RECEIPT_PURPOSE,
        "calibration_id": contract["calibration_id"],
        "M": M_name,
        "evaluation_group": evaluation_group,
        "status": status,
        "return_code": int(return_code),
        "wall_elapsed_seconds": float(wall_elapsed_seconds),
        "command_timeout_minutes": int(contract["workload"]["command_timeout_minutes"]),
        "environment_digest": environment["environment_digest"],
        "source_artifact_id": int(contract["source_materialization"]["artifact_id"]),
        "source_artifact_digest": contract["source_materialization"]["artifact_digest"],
        "sealed_artifact_downloaded": False,
        "sealed_ecological_outcomes_read": False,
        "telemetry_used_for_scientific_selection": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    group_contract_path = root / "contract.json"
    telemetry_path = root / "telemetry.json"
    if status == "completed":
        group_contract = json.loads(group_contract_path.read_text(encoding="utf-8"))
        telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
        expected_id = contract["workload"]["calibration_execution_id"]
        expected_identity = {
            "scientific_execution_id": expected_id,
            "part_seed": int(contract["workload"]["part_seed"]),
            "taxon_index": int(contract["workload"]["taxon_index"]),
            "taxon": contract["workload"]["taxon"],
            "M": M_name,
            "evaluation_group": evaluation_group,
        }
        for key, expected_value in expected_identity.items():
            if group_contract.get(key) != expected_value:
                raise ValueError(f"runtime calibration group identity changed: {key}")
        for key in BARRIER_KEYS:
            if group_contract.get(key) is not False:
                raise ValueError(f"runtime calibration group crossed barrier: {key}")
        required = set(contract["telemetry"]["required_fields"])
        if not required.issubset(telemetry):
            raise ValueError("runtime calibration telemetry is incomplete")
        if telemetry.get("scientific_selection_input") is not False:
            raise ValueError("runtime calibration telemetry entered scientific selection")
        receipt.update({
            "logical_shard_id": group_contract["logical_shard_id"],
            "runtime_elapsed_seconds": float(telemetry["elapsed_seconds"]),
            "candidate_count": int(telemetry["candidate_count"]),
            "fit_count": int(telemetry["fit_count"]),
            "checkpoint_digest": telemetry["checkpoint_digest"],
            "group_contract_sha256": _sha256(group_contract_path),
            "telemetry_sha256": _sha256(telemetry_path),
        })
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    receipt["receipt_digest"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def aggregate_receipts(
    *, contract_path: str | Path, receipts_root: str | Path, output_path: str | Path,
) -> dict:
    contract = load_contract(contract_path)
    found: dict[tuple[str, str], dict] = {}
    for path in sorted(Path(receipts_root).rglob("receipt.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != RECEIPT_PURPOSE:
            continue
        if payload.get("calibration_id") != contract["calibration_id"]:
            raise ValueError("runtime calibration receipt identity changed")
        if int(payload.get("source_artifact_id", -1)) != int(
            contract["source_materialization"]["artifact_id"]
        ):
            raise ValueError("runtime calibration receipt source artifact changed")
        if payload.get("source_artifact_digest") != contract["source_materialization"]["artifact_digest"]:
            raise ValueError("runtime calibration receipt source digest changed")
        for key in (
            "sealed_artifact_downloaded",
            "sealed_ecological_outcomes_read",
            "telemetry_used_for_scientific_selection",
            "scientific_promotion_allowed",
            "product_b_unblocked",
        ):
            if payload.get(key) is not False:
                raise ValueError(f"runtime calibration receipt crossed barrier: {key}")
        identity = (str(payload.get("M")), str(payload.get("evaluation_group")))
        if identity in found:
            raise ValueError(f"duplicate runtime calibration receipt: {identity}")
        found[identity] = payload
    expected = {(M, group) for M in M_NAMES for group in GROUPS}
    if set(found) != expected:
        raise ValueError("runtime calibration receipt denominator is incomplete")
    environment_digests = {x["environment_digest"] for x in found.values()}
    statuses = {identity: x["status"] for identity, x in found.items()}
    completed = [x for x in found.values() if x["status"] == "completed"]
    timeouts = [identity for identity, x in found.items() if x["status"] == "calibration_ceiling_reached"]
    failures = [identity for identity, x in found.items() if x["status"] == "engineering_failure"]
    observed_max = max((float(x["wall_elapsed_seconds"]) for x in completed), default=None)
    rule = contract["timeout_freeze_rule"]
    proposed_minutes = None
    if observed_max is not None and not timeouts and not failures:
        raw_minutes = (
            float(observed_max) / 60.0 * float(rule["elapsed_multiplier"])
            + float(rule["runner_overhead_minutes"])
        )
        quantum = int(rule["round_up_minutes"])
        proposed_minutes = max(
            int(rule["minimum_group_timeout_minutes"]),
            int(math.ceil(raw_minutes / quantum) * quantum),
        )
        if proposed_minutes > int(rule["maximum_group_timeout_minutes"]):
            proposed_minutes = None
    if len(environment_digests) != 1:
        status = "runtime_environment_inconsistent_not_ready_to_freeze"
        proposed_minutes = None
    elif failures:
        status = "engineering_failure"
    elif timeouts or proposed_minutes is None:
        status = "runtime_ceiling_observed_not_ready_to_freeze"
    else:
        status = "calibration_complete_timeout_proposal_ready_for_separate_freeze"
    result = {
        "purpose": DECISION_PURPOSE,
        "calibration_id": contract["calibration_id"],
        "status": status,
        "cell_count": len(found),
        "completed_cell_count": len(completed),
        "calibration_ceiling_cells": [list(x) for x in sorted(timeouts)],
        "engineering_failure_cells": [list(x) for x in sorted(failures)],
        "environment_digests": sorted(environment_digests),
        "environment_consistent_across_all_cells": len(environment_digests) == 1,
        "observed_max_wall_elapsed_seconds": observed_max,
        "proposed_scientific_group_timeout_minutes": proposed_minutes,
        "proposal_requires_separate_environment_and_timeout_freeze": True,
        "sealed_ecological_outcomes_read": False,
        "telemetry_used_for_scientific_selection": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    result["decision_digest"] = hashlib.sha256(_canonical(result)).hexdigest()
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("environment")
    q.add_argument("--contract", required=True)
    q.add_argument("--output", required=True)
    q.set_defaults(func=lambda a: write_environment_receipt(a.contract, a.output))
    q = sub.add_parser("group-receipt")
    q.add_argument("--contract", required=True)
    q.add_argument("--group-output-dir", required=True)
    q.add_argument("--environment-receipt", required=True)
    q.add_argument("--M", required=True)
    q.add_argument("--evaluation-group", required=True)
    q.add_argument("--return-code", type=int, required=True)
    q.add_argument("--wall-elapsed-seconds", type=float, required=True)
    q.add_argument("--output", required=True)
    q.set_defaults(func=lambda a: write_group_receipt(
        contract_path=a.contract,
        group_output_dir=a.group_output_dir,
        environment_receipt_path=a.environment_receipt,
        M_name=a.M,
        evaluation_group=a.evaluation_group,
        return_code=a.return_code,
        wall_elapsed_seconds=a.wall_elapsed_seconds,
        output_path=a.output,
    ))
    q = sub.add_parser("aggregate")
    q.add_argument("--contract", required=True)
    q.add_argument("--receipts-root", required=True)
    q.add_argument("--output", required=True)
    q.set_defaults(func=lambda a: aggregate_receipts(
        contract_path=a.contract,
        receipts_root=a.receipts_root,
        output_path=a.output,
    ))
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
