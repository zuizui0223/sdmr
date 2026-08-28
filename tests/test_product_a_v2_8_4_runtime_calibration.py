import hashlib
import json
from pathlib import Path

import pytest

from sdmr.v2_8_4_runtime_calibration import (
    BARRIER_KEYS,
    GROUPS,
    M_NAMES,
    RECEIPT_PURPOSE,
    aggregate_receipts,
    load_contract,
    write_group_receipt,
)


CONTRACT = Path("configs/product_a_v2_8_4_runtime_calibration_contract.json")
WORKFLOW = Path(".github/workflows/product-a-v2-8-4-runtime-calibration.yml")
MODULE = Path("src/sdmr/v2_8_4_runtime_calibration.py")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _technical_receipt(M: str, group: str, *, status: str = "completed") -> dict:
    contract = load_contract(CONTRACT)
    return {
        "purpose": RECEIPT_PURPOSE,
        "calibration_id": contract["calibration_id"],
        "M": M,
        "evaluation_group": group,
        "status": status,
        "return_code": 0 if status == "completed" else 124,
        "wall_elapsed_seconds": 1200.0,
        "environment_digest": "e" * 64,
        "source_artifact_id": contract["source_materialization"]["artifact_id"],
        "source_artifact_digest": contract["source_materialization"]["artifact_digest"],
        "sealed_artifact_downloaded": False,
        "sealed_ecological_outcomes_read": False,
        "telemetry_used_for_scientific_selection": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }


def test_runtime_calibration_contract_is_exactly_presealed_and_runtime_only():
    c = load_contract(CONTRACT)
    assert c["tracks_issue"] == 170
    assert c["runtime_only"] is True
    assert c["source_materialization"]["artifact_id"] == 9634639012
    assert c["source_materialization"]["artifact_digest"] == (
        "sha256:8c73ff8e3b031b682fe79c65e2330fb4a533bf48fcfadfc82825f3a9ce440831"
    )
    assert c["workload_selection"]["uses_only_operational_timeout_evidence"] is True
    assert c["workload_selection"]["uses_scientific_outcomes"] is False
    assert c["workload_selection"]["uses_sealed_outcomes"] is False
    assert c["workload"]["cell_count"] == 21
    assert c["workload"]["model_pool_metrics_may_be_uploaded"] is False
    assert c["execution_boundary"]["calibration_result_authorizes_scientific_execution"] is False
    assert c["execution_boundary"]["scientific_presealed_execution_allowed"] is False
    assert c["execution_boundary"]["sealed_execution_allowed"] is False
    assert c["execution_boundary"]["scientific_promotion_allowed"] is False
    assert c["execution_boundary"]["product_b_unblocked"] is False
    for key in (
        "runtime_implementation",
        "calibration_module",
        "workflow",
        "runtime_design",
        "scientific_contract",
        "process_registry",
        "taxon_registry",
    ):
        path = Path(c["workload"][f"{key}_path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == c["workload"][f"{key}_sha256"]


def test_runtime_calibration_workflow_is_pinned_and_cannot_dispatch_or_upload_scores():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch" not in text
    for sha in load_contract(CONTRACT)["runtime_environment"]["github_actions"].values():
        assert f"@{sha}" in text
    for M in M_NAMES:
        assert M in text
    for group in GROUPS:
        assert group in text
    assert "name: v283-fresh-part-2026082201" in text
    assert "pattern: v284-runtime-calibration-receipt-*" in text
    assert "path: receipt/receipt.json" in text
    assert "path: group-output" not in text
    assert "v283-fresh-sealed" not in text


def test_group_receipt_reads_contract_and_telemetry_but_not_scientific_score_files(tmp_path):
    c = load_contract(CONTRACT)
    group_root = tmp_path / "group"
    group_contract = {
        "scientific_execution_id": c["workload"]["calibration_execution_id"],
        "logical_shard_id": "technical-logical-id",
        "part_seed": c["workload"]["part_seed"],
        "taxon_index": c["workload"]["taxon_index"],
        "taxon": c["workload"]["taxon"],
        "M": M_NAMES[0],
        "evaluation_group": GROUPS[0],
        **{key: False for key in BARRIER_KEYS},
    }
    telemetry = {
        "logical_shard_id": "technical-logical-id",
        "phase": "deterministic_model_pool_group",
        "procedure": "frozen_deterministic_procedure_library",
        "outer_fold": "all",
        "inner_step": "all",
        "candidate_count": 3,
        "fit_count": 48,
        "elapsed_seconds": 600.0,
        "checkpoint_digest": "c" * 64,
        "scientific_selection_input": False,
    }
    _write_json(group_root / "contract.json", group_contract)
    _write_json(group_root / "telemetry.json", telemetry)
    environment = tmp_path / "environment.json"
    _write_json(environment, {"environment_digest": "e" * 64})
    receipt = write_group_receipt(
        contract_path=CONTRACT,
        group_output_dir=group_root,
        environment_receipt_path=environment,
        M_name=M_NAMES[0],
        evaluation_group=GROUPS[0],
        return_code=0,
        wall_elapsed_seconds=620,
        output_path=tmp_path / "receipt.json",
    )
    assert receipt["status"] == "completed"
    assert receipt["runtime_elapsed_seconds"] == 600.0
    assert receipt["scientific_promotion_allowed"] is False
    assert "fold_metrics.csv" not in MODULE.read_text(encoding="utf-8")
    assert "selection_trace.csv" not in MODULE.read_text(encoding="utf-8")


def test_exact_21_cell_aggregate_proposes_timeout_without_promotion(tmp_path):
    for M in M_NAMES:
        for group in GROUPS:
            _write_json(tmp_path / M / group / "receipt.json", _technical_receipt(M, group))
    result = aggregate_receipts(
        contract_path=CONTRACT,
        receipts_root=tmp_path,
        output_path=tmp_path / "decision.json",
    )
    assert result["status"] == "calibration_complete_timeout_proposal_ready_for_separate_freeze"
    assert result["cell_count"] == 21
    assert result["environment_consistent_across_all_cells"] is True
    assert result["proposed_scientific_group_timeout_minutes"] == 75
    assert result["proposal_requires_separate_environment_and_timeout_freeze"] is True
    assert result["scientific_promotion_allowed"] is False
    assert result["product_b_unblocked"] is False


def test_aggregate_fails_closed_on_incomplete_denominator(tmp_path):
    _write_json(tmp_path / "one" / "receipt.json", _technical_receipt(M_NAMES[0], GROUPS[0]))
    with pytest.raises(ValueError, match="denominator is incomplete"):
        aggregate_receipts(
            contract_path=CONTRACT,
            receipts_root=tmp_path,
            output_path=tmp_path / "decision.json",
        )
