"""Verify a separate one-shot Product-A v2.8.4 sealed execution authorization.

This module is intentionally truth-blind. It validates only repository identities,
presealed receipt pins, and execution-boundary flags. It never imports the sealed
audit, raster extraction, model scoring, or ecological decision code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping

from .v2_8_4_sealed_boundary import EXPECTED_EXECUTION_ID, EXPECTED_SEEDS, load_sealed_boundary_contract

AUTH_PURPOSE = "product_a_v2_8_4_one_shot_sealed_execution_authorization"
AUTH_GATE_PURPOSE = "product_a_v2_8_4_sealed_execution_authorization_gate"
REQUIRED_IMPLEMENTATION_PATHS = (
    ".github/workflows/product-a-v2-8-4-sealed-reusable.yml",
    "src/sdmr/v2_8_4_sealed_authorization.py",
    "src/sdmr/v2_8_4_sealed_runtime.py",
    "src/sdmr/v2_8_4_sealed_boundary.py",
    "configs/product_a_v2_8_4_sealed_boundary_contract.json",
    "configs/product_a_v2_8_4_environment_timeout_freeze.json",
    "configs/product_a_v2_8_4_scientific_requirements.lock",
    "configs/product_a_v2_8_3_fresh_confirmation_contract.json",
    "src/sdmr/v2_8_3_fresh_runtime.py",
    "src/sdmr/v2_8_3_fresh_aggregate.py",
    "src/sdmr/v2_7_2_fresh_sealed_audit.py",
)


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _canonical_file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _write(path: str | Path, payload: Mapping[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_sealed_authorization(
    *, authorization_path: str | Path,
    boundary_path: str | Path,
    implementation_root: str | Path,
    authorization_root: str | Path,
    implementation_ref: str,
    reusable_workflow_sha256: str,
    caller_workflow_sha256: str,
    authorization_commit_sha: str,
    current_sha: str,
    current_ref: str,
    current_event: str,
    output_path: str | Path,
) -> dict:
    boundary = load_sealed_boundary_contract(boundary_path)
    auth = _load(authorization_path)
    if auth.get("purpose") != AUTH_PURPOSE:
        raise ValueError("wrong Product-A v2.8.4 sealed authorization purpose")
    if auth.get("scientific_execution_id") != EXPECTED_EXECUTION_ID:
        raise ValueError("sealed authorization scientific execution identity changed")
    if auth.get("one_shot") is not True:
        raise ValueError("sealed authorization is not one-shot")
    if current_ref != "refs/heads/main" or current_event != "workflow_dispatch":
        raise ValueError("sealed execution must originate from a manual main dispatch")
    if authorization_commit_sha != current_sha:
        raise ValueError("sealed authorization must execute from its exact merge commit")

    embedded = str(auth.get("authorization_receipt_digest", ""))
    body = dict(auth)
    body.pop("authorization_receipt_digest", None)
    observed = hashlib.sha256(_canonical(body)).hexdigest()
    if embedded != observed:
        raise ValueError("sealed authorization receipt digest changed")

    implementation = auth.get("implementation_identity", {})
    if implementation.get("runtime_ref") != implementation_ref:
        raise ValueError("sealed authorization implementation ref changed")
    if implementation.get("sealed_reusable_workflow_sha256") != reusable_workflow_sha256:
        raise ValueError("sealed authorization reusable workflow hash changed")
    hashes = implementation.get("newline_canonical_sha256", {})
    if set(REQUIRED_IMPLEMENTATION_PATHS) - set(hashes):
        raise ValueError("sealed authorization does not pin the complete required implementation surface")
    root = Path(implementation_root)
    for relative in REQUIRED_IMPLEMENTATION_PATHS:
        path = root / relative
        if not path.is_file() or _canonical_file_sha256(path) != hashes[relative]:
            raise ValueError(f"sealed implementation identity changed: {relative}")
    if _canonical_file_sha256(root / ".github/workflows/product-a-v2-8-4-sealed-reusable.yml") != reusable_workflow_sha256:
        raise ValueError("sealed reusable workflow self-hash changed")

    caller = auth.get("authorized_caller", {})
    caller_path = str(caller.get("path", ""))
    if caller_path != ".github/workflows/product-a-v2-8-4-sealed-authorized.yml":
        raise ValueError("sealed authorization caller path changed")
    if caller.get("newline_canonical_sha256") != caller_workflow_sha256:
        raise ValueError("sealed authorization caller hash changed")
    auth_root = Path(authorization_root)
    if _canonical_file_sha256(auth_root / caller_path) != caller_workflow_sha256:
        raise ValueError("sealed authorization caller file does not match frozen hash")

    expected_receipts = {
        int(row["part_seed"]): {
            "workflow_run_id": int(row["workflow_run_id"]),
            "workflow_run_attempt": int(row["workflow_run_attempt"]),
            "artifact_id": int(row["artifact_id"]),
            "artifact_name": str(row["artifact_name"]),
            "artifact_digest": str(row["artifact_digest"]),
            "artifact_size_bytes": int(row["artifact_size_bytes"]),
            "receipt_digest": str(row["receipt_digest"]),
        }
        for row in boundary["presealed_receipts"]
    }
    observed_receipts = {
        int(row["part_seed"]): {
            "workflow_run_id": int(row["workflow_run_id"]),
            "workflow_run_attempt": int(row["workflow_run_attempt"]),
            "artifact_id": int(row["artifact_id"]),
            "artifact_name": str(row["artifact_name"]),
            "artifact_digest": str(row["artifact_digest"]),
            "artifact_size_bytes": int(row["artifact_size_bytes"]),
            "receipt_digest": str(row["receipt_digest"]),
        }
        for row in auth.get("presealed_receipts", [])
    }
    if set(observed_receipts) != set(EXPECTED_SEEDS) or observed_receipts != expected_receipts:
        raise ValueError("sealed authorization presealed receipt pins changed")

    invariants = auth.get("scientific_invariants", {})
    expected_invariants = {
        "sealed_fraction": 0.25,
        "split_seeds": list(EXPECTED_SEEDS),
        "M_km": [150, 300, 500],
        "model_random_state": 0,
        "selection_process_numpy_seed": 0,
        "primary_denominator": 3,
        "prediction_guardrail_mean_presence_rank_delta_vs_auc_min": -0.01,
        "ecological_nondomination_minimum_parts": 2,
        "strict_ecological_improvement_minimum_parts": 2,
        "process_modal_status_fraction_min": 2.0 / 3.0,
    }
    for key, value in expected_invariants.items():
        if invariants.get(key) != value:
            raise ValueError(f"sealed authorization scientific invariant changed: {key}")
    for key in (
        "candidate_predictor_universe_changed",
        "candidate_library_changed",
        "thresholds_changed",
        "taxa_changed",
        "M_changed",
        "seeds_changed",
        "fraction_changed",
        "denominator_changed",
        "decision_rule_changed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if invariants.get(key) is not False:
            raise ValueError(f"sealed authorization crossed scientific boundary: {key}")

    execution = auth.get("execution_boundary", {})
    for key in (
        "sealed_workflow_implemented_and_reviewed",
        "sealed_execution_authorization_exists",
        "sealed_execution_allowed",
        "workflow_dispatch_allowed",
    ):
        if execution.get(key) is not True:
            raise ValueError(f"sealed authorization is closed: {key}")
    for key in (
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if execution.get(key) is not False:
            raise ValueError(f"sealed authorization crossed outcome/promotion boundary: {key}")

    retry = auth.get("retry_policy", {})
    if retry.get("pre_read_exact_retry_allowed_only_if_sealed_read_entered_false") is not True:
        raise ValueError("sealed authorization retry rule changed")
    if int(retry.get("maximum_pre_read_attempts_per_part", -1)) != 2:
        raise ValueError("sealed authorization pre-read retry count changed")
    for key in (
        "retry_after_sealed_read_entered_allowed",
        "broad_rerun_of_successful_sealed_part_allowed",
        "scientific_null_negative_or_unavailable_outcome_retry_allowed",
    ):
        if retry.get(key) is not False:
            raise ValueError(f"sealed authorization retry boundary changed: {key}")

    result = {
        "purpose": AUTH_GATE_PURPOSE,
        "scientific_execution_id": EXPECTED_EXECUTION_ID,
        "authorization_commit_sha": authorization_commit_sha,
        "authorization_receipt_digest": embedded,
        "implementation_ref": implementation_ref,
        "sealed_reusable_workflow_sha256": reusable_workflow_sha256,
        "authorized_caller_workflow_sha256": caller_workflow_sha256,
        "one_shot_sealed_execution_authorized": True,
        "pre_read_exact_retry_maximum_attempts_per_part": 2,
        "retry_after_sealed_read_entered_allowed": False,
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    result["gate_digest"] = hashlib.sha256(_canonical(result)).hexdigest()
    _write(output_path, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--implementation-root", required=True)
    parser.add_argument("--authorization-root", required=True)
    parser.add_argument("--implementation-ref", required=True)
    parser.add_argument("--reusable-workflow-sha256", required=True)
    parser.add_argument("--caller-workflow-sha256", required=True)
    parser.add_argument("--authorization-commit-sha", required=True)
    parser.add_argument("--current-sha", required=True)
    parser.add_argument("--current-ref", required=True)
    parser.add_argument("--current-event", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    verify_sealed_authorization(
        authorization_path=args.authorization,
        boundary_path=args.boundary,
        implementation_root=args.implementation_root,
        authorization_root=args.authorization_root,
        implementation_ref=args.implementation_ref,
        reusable_workflow_sha256=args.reusable_workflow_sha256,
        caller_workflow_sha256=args.caller_workflow_sha256,
        authorization_commit_sha=args.authorization_commit_sha,
        current_sha=args.current_sha,
        current_ref=args.current_ref,
        current_event=args.current_event,
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
