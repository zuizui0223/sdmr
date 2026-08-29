"""Truth-blind receipt gate for the Product-A v2.8.4 sealed boundary.

This module validates only provenance metadata.  It never imports model-scoring,
raster-extraction, or sealed-audit code and never reads sealed ecological values.
The output of :func:`build_truth_blind_input_gate` is therefore not an execution
authorization; it is only a reviewed input manifest for a later, separately
authorized one-shot sealed workflow.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping


BOUNDARY_PURPOSE = "product_a_v2_8_4_one_shot_sealed_boundary_design"
PRESEALED_RECEIPT_PURPOSE = "product_a_v2_8_4_presealed_part_receipt"
EXPECTED_SEEDS = (2026082201, 2026082202, 2026082203)
EXPECTED_EXECUTION_ID = "product-a-v2-8-4-fresh-confirmation-v1"
EXPECTED_PREDECESSOR_BLOB = "1928de6d8f1289117415047c7a8d1ee894ca6bbe"


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_sealed_boundary_contract(path: str | Path) -> dict:
    payload = _load(path)
    if payload.get("purpose") != BOUNDARY_PURPOSE:
        raise ValueError("wrong Product-A v2.8.4 sealed boundary purpose")
    if payload.get("scientific_execution_id") != EXPECTED_EXECUTION_ID:
        raise ValueError("v2.8.4 sealed scientific execution identity changed")
    predecessor = payload.get("predecessor_scientific_contract", {})
    if predecessor.get("blob_sha") != EXPECTED_PREDECESSOR_BLOB:
        raise ValueError("v2.8.4 sealed boundary changed predecessor science contract")
    if predecessor.get("scientific_semantics_inherited_without_change") is not True:
        raise ValueError("v2.8.4 sealed boundary does not inherit science exactly")

    receipts = payload.get("presealed_receipts", [])
    if len(receipts) != 3 or {int(row["part_seed"]) for row in receipts} != set(EXPECTED_SEEDS):
        raise ValueError("v2.8.4 sealed boundary requires exactly three frozen receipts")
    if len({int(row["artifact_id"]) for row in receipts}) != 3:
        raise ValueError("v2.8.4 sealed boundary receipt artifact IDs are not unique")
    if len({str(row["receipt_digest"]) for row in receipts}) != 3:
        raise ValueError("v2.8.4 sealed boundary receipt digests are not unique")
    for row in receipts:
        if not str(row.get("artifact_digest", "")).startswith("sha256:"):
            raise ValueError("v2.8.4 sealed receipt lacks outer SHA-256 digest")
        if len(str(row.get("receipt_digest", ""))) != 64:
            raise ValueError("v2.8.4 sealed receipt lacks inner receipt digest")

    invariants = payload.get("scientific_invariants", {})
    expected = {
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
    for key, value in expected.items():
        if invariants.get(key) != value:
            raise ValueError(f"v2.8.4 sealed scientific invariant changed: {key}")
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
            raise ValueError(f"v2.8.4 sealed boundary crossed scientific barrier: {key}")

    execution = payload.get("execution_boundary", {})
    if execution.get("design_only") is not True:
        raise ValueError("v2.8.4 sealed boundary is not design-only")
    for key in (
        "sealed_workflow_implemented_and_reviewed",
        "sealed_execution_authorization_exists",
        "sealed_execution_allowed",
        "workflow_dispatch_allowed",
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if execution.get(key) is not False:
            raise ValueError(f"v2.8.4 sealed design unexpectedly authorizes execution: {key}")
    return payload


def _expected_receipt(boundary: Mapping[str, object], seed: int) -> dict:
    rows = [
        row for row in boundary["presealed_receipts"]
        if int(row["part_seed"]) == int(seed)
    ]
    if len(rows) != 1:
        raise ValueError(f"no unique sealed receipt pin for seed {seed}")
    return dict(rows[0])


def verify_outer_receipt_artifact(row: Mapping[str, object], *, expected: Mapping[str, object]) -> None:
    checks = {
        "id": int(expected["artifact_id"]),
        "name": str(expected["artifact_name"]),
        "digest": str(expected["artifact_digest"]),
        "size_in_bytes": int(expected["artifact_size_bytes"]),
    }
    for key, value in checks.items():
        observed = row.get(key)
        if key in {"id", "size_in_bytes"} and observed is not None:
            observed = int(observed)
        if observed != value:
            raise ValueError(f"presealed receipt outer artifact mismatch: {key}")
    if row.get("expired") is True:
        raise ValueError("presealed receipt artifact expired before sealed boundary")
    workflow_run = row.get("workflow_run") or {}
    if workflow_run and int(workflow_run.get("id", -1)) != int(expected["workflow_run_id"]):
        raise ValueError("presealed receipt outer workflow run mismatch")


def verify_presealed_receipt_payload(
    payload: Mapping[str, object], *, boundary: Mapping[str, object]
) -> dict:
    receipt = dict(payload)
    if receipt.get("purpose") != PRESEALED_RECEIPT_PURPOSE:
        raise ValueError("sealed boundary received wrong presealed receipt purpose")
    seed = int(receipt.get("part_seed", -1))
    expected = _expected_receipt(boundary, seed)
    embedded = str(receipt.get("receipt_digest", ""))
    canonical_payload = dict(receipt)
    canonical_payload.pop("receipt_digest", None)
    observed_digest = hashlib.sha256(_canonical(canonical_payload)).hexdigest()
    if embedded != observed_digest or embedded != expected["receipt_digest"]:
        raise ValueError("presealed receipt inner digest mismatch")

    implementation = boundary["presealed_implementation_identity"]
    exact = {
        "scientific_execution_id": boundary["scientific_execution_id"],
        "workflow_run_id": int(expected["workflow_run_id"]),
        "workflow_run_attempt": int(expected["workflow_run_attempt"]),
        "runtime_commit_sha": implementation["runtime_ref"],
        "reusable_workflow_sha256": implementation[
            "reusable_workflow_newline_canonical_sha256"
        ],
        "authorization_receipt_digest": implementation[
            "presealed_authorization_receipt_digest"
        ],
        "environment_digest": implementation["environment_digest"],
        "dependency_lock_sha256": implementation["dependency_lock_sha256"],
    }
    for key, value in exact.items():
        observed = receipt.get(key)
        if key in {"workflow_run_id", "workflow_run_attempt"} and observed is not None:
            observed = int(observed)
        if observed != value:
            raise ValueError(f"presealed receipt identity mismatch: {key}")

    denominator = receipt.get("full_denominator", {})
    if denominator != {
        "taxa": 12,
        "M": 3,
        "evaluation_groups_per_M": 7,
        "logical_group_shards": 252,
        "M_shards": 36,
        "final_models": 12,
        "complete": True,
    }:
        raise ValueError("presealed receipt full denominator changed")
    if receipt.get("checkpoint_retry_identity_preserved") is not True:
        raise ValueError("presealed receipt did not preserve retry identity")
    for key in (
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if receipt.get(key) is not False:
            raise ValueError(f"presealed receipt crossed sealed/promotion boundary: {key}")

    source = list(receipt.get("source_artifacts", []))
    if len(source) != 2 or {str(row.get("role")) for row in source} != {
        "model_pool", "structural_receipt"
    }:
        raise ValueError("presealed receipt source-artifact denominator changed")
    outputs = list(receipt.get("output_artifacts", []))
    if len(outputs) != 325:
        raise ValueError("presealed receipt output-artifact denominator changed")
    names = [str(row.get("artifact_name", "")) for row in outputs]
    if len(set(names)) != 325:
        raise ValueError("presealed receipt output artifact names are not unique")
    for row in outputs:
        if not str(row.get("artifact_digest", "")).startswith("sha256:"):
            raise ValueError("presealed output artifact lacks immutable SHA-256 digest")
    if sum(name.startswith(f"v284-pretruth-{seed}") for name in names) != 1:
        raise ValueError("presealed receipt does not pin exactly one pretruth artifact")
    if sum(name.startswith(f"v284-final-{seed}-taxon") for name in names) != 12:
        raise ValueError("presealed receipt does not pin exactly 12 final model artifacts")
    return receipt


def build_truth_blind_input_gate(
    *, boundary_path: str | Path,
    receipt_paths: Iterable[str | Path],
    outer_artifacts: Iterable[Mapping[str, object]],
    output_path: str | Path,
) -> dict:
    boundary = load_sealed_boundary_contract(boundary_path)
    payloads = [_load(path) for path in receipt_paths]
    if len(payloads) != 3:
        raise ValueError("sealed input gate requires exactly three receipt files")
    artifacts_by_name = {str(row.get("name", "")): row for row in outer_artifacts}
    if len(artifacts_by_name) != 3:
        raise ValueError("sealed input gate requires exactly three outer receipt artifacts")

    validated = []
    for payload in payloads:
        seed = int(payload.get("part_seed", -1))
        expected = _expected_receipt(boundary, seed)
        outer = artifacts_by_name.get(str(expected["artifact_name"]))
        if outer is None:
            raise ValueError(f"missing outer receipt artifact for seed {seed}")
        verify_outer_receipt_artifact(outer, expected=expected)
        validated.append(verify_presealed_receipt_payload(payload, boundary=boundary))
    if {int(row["part_seed"]) for row in validated} != set(EXPECTED_SEEDS):
        raise ValueError("sealed input gate receipt seed denominator changed")

    result = {
        "purpose": "product_a_v2_8_4_truth_blind_sealed_input_gate",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "receipt_artifacts": [
            {
                "part_seed": int(row["part_seed"]),
                "artifact_id": int(_expected_receipt(boundary, int(row["part_seed"]))["artifact_id"]),
                "artifact_digest": _expected_receipt(boundary, int(row["part_seed"]))["artifact_digest"],
                "receipt_digest": str(row["receipt_digest"]),
            }
            for row in sorted(validated, key=lambda item: int(item["part_seed"]))
        ],
        "full_primary_denominator_presealed": True,
        "sealed_workflow_implementation_review_ready": True,
        "sealed_execution_authorized": False,
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    result["gate_digest"] = hashlib.sha256(_canonical(result)).hexdigest()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
