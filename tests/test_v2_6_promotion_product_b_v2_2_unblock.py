from pathlib import Path
import json

import pandas as pd

from sdmr.v2_6_promotion_product_b_v2_2_unblock import (
    apply_promotion_and_unblock,
    load_promotion_contract,
)

CONFIG = Path("configs/product_a_v2_6_promotion_product_b_v2_2_unblock_contract.json")


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _sources(tmp_path: Path, *, a_emp_supported: bool = True, b_supported: bool = True):
    a_kt = tmp_path / "a_kt"; a_kt.mkdir()
    _write_json(a_kt / "contract.json", {
        "purpose": "product_a_v2_6_predeclared_fresh_validation_decision",
        "decision": "v2_6_supported",
        "all_process_and_boundary_products_written_before_truth_read": True,
        "process_support": True,
        "boundary_support": True,
        "validation_generating_truth_read_after_product_freeze": True,
        "candidate_selection_performed_during_validation": False,
        "scientific_threshold_tuning_performed_during_validation": False,
        "validation_truth_used_for_calibration": False,
        "product_b_unblocked": False,
        "scientific_promotion_allowed": False,
        "known_truth_result_directly_allows_empirical_promotion": False,
    })
    a_emp = tmp_path / "a_emp"; a_emp.mkdir()
    a_decision = "empirical_confirmation_supported" if a_emp_supported else "empirical_confirmation_not_supported"
    _write_json(a_emp / "contract.json", {
        "purpose": "product_a_v2_6_independent_empirical_confirmation_decision",
        "decision": a_decision,
        "n_parts": 6,
        "known_truth_thresholds_retuned_from_empirical_outcomes": False,
        "empirical_thresholds_retuned_after_sealed_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    })
    pd.DataFrame([{
        "decision": a_decision,
        "all_empirical_evidence_available": True,
        "prediction_guardrail": a_emp_supported,
        "ecological_support": a_emp_supported,
        "process_reproducibility_support": a_emp_supported,
    }]).to_csv(a_emp / "decision.csv", index=False)
    b = tmp_path / "b"; b.mkdir()
    b_decision = "product_b_v2_known_truth_supported" if b_supported else "product_b_v2_known_truth_not_supported"
    _write_json(b / "contract.json", {
        "purpose": "product_b_v2_2_fresh_known_truth_decision",
        "decision": b_decision,
        "generating_process_truth_opened_after_pretruth_freeze": True,
        "process_losses_frozen_before_generating_truth_audit": True,
        "thresholds_retuned_after_truth": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "product_b_formally_unblocked": False,
        "scientific_empirical_product_b_claim_allowed": False,
    })
    pd.DataFrame([{
        "decision": b_decision,
        "universal_process_recall": 1.0 if b_supported else 0.5,
        "mean_taxon_process_precision": 0.9 if b_supported else 0.6,
    }]).to_csv(b / "decision.csv", index=False)
    return a_kt, a_emp, b


def test_v22_promotion_contract_pins_exact_recovery_source_before_outcome():
    c = load_promotion_contract(CONFIG)
    assert c["contract_frozen_before_product_b_v2_2_known_truth_outcome"] is True
    assert c["product_b_v2_2_source_frozen_before_outcome"] is True
    assert c["new_postoutcome_scientific_thresholds"] is False
    b = c["fresh_known_truth_product_b_v2_2_source"]
    assert b["version"] == "v2.2-recovery"
    assert b["scientific_identity"] == "Product-B-v2.2"
    assert b["scientific_contract_changed_from_88580599"] is False
    assert b["implementation_sha"] == "daaf207d1574befbc703ace02a82971d4980a865"
    assert b["frozen_ref"] == "frozen/product-b-v2-2-recovery-daaf207d"
    assert b["workflow_file"] == "product-b-v2-2-known-truth-recovery.yml"
    assert b["artifact_name"] == "product-b-v2-2-fresh-known-truth-decision"
    assert b["requires_single_run_for_frozen_source"] is True
    assert b["predecessor_run_id"] == 32422606768
    assert b["predecessor_failure_stage"] == "frozen-method-source"
    assert b["predecessor_fresh_taxa_generated"] is False
    assert b["predecessor_generating_truth_opened"] is False
    assert b["predecessor_failure_reason"] == "artifact_redirect_authorization_401"


def test_supported_sources_promote_a_and_unblock_v22(tmp_path):
    a_kt, a_emp, b = _sources(tmp_path)
    out = tmp_path / "out"
    result = apply_promotion_and_unblock(
        contract_path=CONFIG,
        product_a_known_truth_dir=a_kt,
        product_a_empirical_dir=a_emp,
        product_b_known_truth_dir=b,
        output_dir=out,
    )
    assert result["decision"] == "product_a_v2_6_promoted_product_b_v2_2_unblocked"
    assert result["product_a_v2_6_promoted"] is True
    assert result["product_b_v2_2_unblocked"] is True
    unblock = json.loads((out / "product_b_v2_2_formal_unblock_contract.json").read_text())
    assert unblock["empirical_product_b_execution_allowed"] is True
    assert unblock["product"]["product"] == "Product-B-v2.2"


def test_v22_failure_keeps_b_blocked_without_revoking_a(tmp_path):
    a_kt, a_emp, b = _sources(tmp_path, b_supported=False)
    result = apply_promotion_and_unblock(
        contract_path=CONFIG,
        product_a_known_truth_dir=a_kt,
        product_a_empirical_dir=a_emp,
        product_b_known_truth_dir=b,
        output_dir=tmp_path / "out",
    )
    assert result["product_a_v2_6_promoted"] is True
    assert result["product_b_v2_2_unblocked"] is False


def test_a_empirical_failure_keeps_v22_blocked(tmp_path):
    a_kt, a_emp, b = _sources(tmp_path, a_emp_supported=False)
    result = apply_promotion_and_unblock(
        contract_path=CONFIG,
        product_a_known_truth_dir=a_kt,
        product_a_empirical_dir=a_emp,
        product_b_known_truth_dir=b,
        output_dir=tmp_path / "out",
    )
    assert result["product_a_v2_6_promoted"] is False
    assert result["product_b_v2_2_unblocked"] is False
