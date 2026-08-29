import copy
import hashlib
import json
from pathlib import Path

import pytest

from sdmr.v2_8_3_fresh_aggregate import (
    ECO_NONDOMINATED_MIN_PARTS,
    ECO_STRICT_IMPROVEMENT_MIN_PARTS,
    PREDICTION_DELTA_FLOOR,
    PROCESS_MODAL_FRACTION_MIN,
)
from sdmr.v2_8_4_sealed_boundary import (
    EXPECTED_SEEDS,
    build_truth_blind_input_gate,
    load_sealed_boundary_contract,
    verify_presealed_receipt_payload,
)


BOUNDARY = Path("configs/product_a_v2_8_4_sealed_boundary_contract.json")


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _synthetic_receipt(boundary, seed):
    expected = next(row for row in boundary["presealed_receipts"] if row["part_seed"] == seed)
    implementation = boundary["presealed_implementation_identity"]
    names = [f"v284-group-{seed}-logical-{i}" for i in range(252)]
    names += [f"v284-precompute-{seed}-taxon{i}" for i in range(12)]
    names += [f"v284-M-{seed}-taxon{i}-buffer_{M}km" for i in range(12) for M in (150, 300, 500)]
    names += [f"v284-worker-{seed}-taxon{i}" for i in range(12)]
    names += [f"v284-pretruth-{seed}"]
    names += [f"v284-final-{seed}-taxon{i}" for i in range(12)]
    assert len(names) == 325
    payload = {
        "purpose": "product_a_v2_8_4_presealed_part_receipt",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "part_seed": seed,
        "workflow_run_id": expected["workflow_run_id"],
        "workflow_run_attempt": expected["workflow_run_attempt"],
        "runtime_commit_sha": implementation["runtime_ref"],
        "runtime_ref": implementation["runtime_ref"],
        "reusable_workflow_sha256": implementation["reusable_workflow_newline_canonical_sha256"],
        "authorization_receipt_digest": implementation["presealed_authorization_receipt_digest"],
        "environment_digest": implementation["environment_digest"],
        "dependency_lock_sha256": implementation["dependency_lock_sha256"],
        "source_artifacts": [
            {"role": "model_pool", "artifact_id": 1, "artifact_name": f"source-{seed}", "artifact_digest": "sha256:" + "1" * 64},
            {"role": "structural_receipt", "artifact_id": 2, "artifact_name": f"structural-{seed}", "artifact_digest": "sha256:" + "2" * 64},
        ],
        "output_artifacts": [
            {
                "artifact_id": i + 10,
                "artifact_name": name,
                "artifact_digest": "sha256:" + hashlib.sha256(name.encode()).hexdigest(),
                "artifact_size_bytes": 1,
            }
            for i, name in enumerate(names)
        ],
        "full_denominator": {
            "taxa": 12,
            "M": 3,
            "evaluation_groups_per_M": 7,
            "logical_group_shards": 252,
            "M_shards": 36,
            "final_models": 12,
            "complete": True,
        },
        "checkpoint_retry_identity_preserved": True,
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    payload["receipt_digest"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload


def _synthetic_boundary(tmp_path):
    boundary = copy.deepcopy(load_sealed_boundary_contract(BOUNDARY))
    receipts = []
    outer = []
    for seed in EXPECTED_SEEDS:
        payload = _synthetic_receipt(boundary, seed)
        expected = next(row for row in boundary["presealed_receipts"] if row["part_seed"] == seed)
        expected["receipt_digest"] = payload["receipt_digest"]
        path = tmp_path / f"receipt-{seed}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        receipts.append(path)
        outer.append({
            "id": expected["artifact_id"],
            "name": expected["artifact_name"],
            "digest": expected["artifact_digest"],
            "size_in_bytes": expected["artifact_size_bytes"],
            "expired": False,
            "workflow_run": {"id": expected["workflow_run_id"]},
        })
    boundary_path = tmp_path / "boundary.json"
    boundary_path.write_text(json.dumps(boundary), encoding="utf-8")
    return boundary_path, receipts, outer


def test_v284_sealed_boundary_pins_three_real_presealed_receipts_and_remains_closed():
    boundary = load_sealed_boundary_contract(BOUNDARY)
    assert [row["part_seed"] for row in boundary["presealed_receipts"]] == list(EXPECTED_SEEDS)
    assert [row["artifact_id"] for row in boundary["presealed_receipts"]] == [9711004502, 9686345424, 9686776074]
    assert [row["receipt_digest"] for row in boundary["presealed_receipts"]] == [
        "9f6924552193af5ea4ee92e5cf6d653238a5e4dcb3cc2f7d5a46ef300b887b03",
        "842f8cb42b4ffe315792f5dac22e96e4f3b2faa16b62cd06eb056d5fe7514978",
        "bbb714de74e72e2f94f96fd6cf364ac49c3640657689c96c66bb59c860fbfdf1",
    ]
    assert boundary["execution_boundary"]["sealed_execution_allowed"] is False
    assert boundary["execution_boundary"]["workflow_dispatch_allowed"] is False
    assert boundary["execution_boundary"]["sealed_ecological_outcomes_read"] is False


def test_v284_sealed_boundary_inherits_exact_v283_decision_thresholds():
    boundary = load_sealed_boundary_contract(BOUNDARY)
    invariants = boundary["scientific_invariants"]
    assert invariants["prediction_guardrail_mean_presence_rank_delta_vs_auc_min"] == PREDICTION_DELTA_FLOOR
    assert invariants["ecological_nondomination_minimum_parts"] == ECO_NONDOMINATED_MIN_PARTS
    assert invariants["strict_ecological_improvement_minimum_parts"] == ECO_STRICT_IMPROVEMENT_MIN_PARTS
    assert invariants["process_modal_status_fraction_min"] == PROCESS_MODAL_FRACTION_MIN
    assert invariants["primary_denominator"] == 3
    assert invariants["model_random_state"] == 0
    assert invariants["selection_process_numpy_seed"] == 0


def test_truth_blind_gate_validates_receipt_provenance_without_authorizing_sealed_execution(tmp_path):
    boundary_path, receipts, outer = _synthetic_boundary(tmp_path)
    output = tmp_path / "gate.json"
    gate = build_truth_blind_input_gate(
        boundary_path=boundary_path,
        receipt_paths=receipts,
        outer_artifacts=outer,
        output_path=output,
    )
    assert gate["full_primary_denominator_presealed"] is True
    assert gate["sealed_workflow_implementation_review_ready"] is True
    assert gate["sealed_execution_authorized"] is False
    assert gate["sealed_ecological_outcomes_read"] is False
    assert gate["scientific_promotion_allowed"] is False
    assert gate["product_b_unblocked"] is False
    assert output.exists()


def test_truth_blind_gate_rejects_any_opened_or_retuned_receipt(tmp_path):
    boundary = copy.deepcopy(load_sealed_boundary_contract(BOUNDARY))
    receipt = _synthetic_receipt(boundary, EXPECTED_SEEDS[0])
    expected = boundary["presealed_receipts"][0]
    expected["receipt_digest"] = receipt["receipt_digest"]
    verify_presealed_receipt_payload(receipt, boundary=boundary)

    opened = copy.deepcopy(receipt)
    opened["sealed_ecological_outcomes_read"] = True
    body = dict(opened)
    body.pop("receipt_digest")
    opened["receipt_digest"] = hashlib.sha256(_canonical(body)).hexdigest()
    expected["receipt_digest"] = opened["receipt_digest"]
    with pytest.raises(ValueError, match="sealed/promotion boundary"):
        verify_presealed_receipt_payload(opened, boundary=boundary)


def test_truth_blind_gate_rejects_incomplete_full_denominator(tmp_path):
    boundary = copy.deepcopy(load_sealed_boundary_contract(BOUNDARY))
    receipt = _synthetic_receipt(boundary, EXPECTED_SEEDS[0])
    receipt["full_denominator"]["logical_group_shards"] = 251
    body = dict(receipt)
    body.pop("receipt_digest")
    receipt["receipt_digest"] = hashlib.sha256(_canonical(body)).hexdigest()
    boundary["presealed_receipts"][0]["receipt_digest"] = receipt["receipt_digest"]
    with pytest.raises(ValueError, match="full denominator"):
        verify_presealed_receipt_payload(receipt, boundary=boundary)
