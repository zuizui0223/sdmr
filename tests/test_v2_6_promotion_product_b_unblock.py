from pathlib import Path
import json

import pandas as pd

from sdmr.v2_6_promotion_product_b_unblock import (
    apply_promotion_and_unblock,
    load_promotion_contract,
)

CONFIG = Path("configs/product_a_v2_6_promotion_product_b_v2_unblock_contract.json")


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
    a_emp_decision = "empirical_confirmation_supported" if a_emp_supported else "empirical_confirmation_not_supported"
    _write_json(a_emp / "contract.json", {
        "purpose": "product_a_v2_6_independent_empirical_confirmation_decision",
        "decision": a_emp_decision,
        "n_parts": 6,
        "known_truth_thresholds_retuned_from_empirical_outcomes": False,
        "empirical_thresholds_retuned_after_sealed_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    })
    pd.DataFrame([{
        "decision": a_emp_decision,
        "all_empirical_evidence_available": True,
        "prediction_guardrail": a_emp_supported,
        "ecological_support": a_emp_supported,
        "process_reproducibility_support": a_emp_supported,
    }]).to_csv(a_emp / "decision.csv", index=False)

    b = tmp_path / "b"; b.mkdir()
    b_decision = "product_b_v2_known_truth_supported" if b_supported else "product_b_v2_known_truth_not_supported"
    _write_json(b / "contract.json", {
        "purpose": "product_b_v2_fresh_known_truth_decision",
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


def test_promotion_contract_is_preoutcome_and_threshold_free():
    c = load_promotion_contract(CONFIG)
    assert c["contract_frozen_before_empirical_product_a_outcome"] is True
    assert c["contract_frozen_before_product_b_v2_known_truth_outcome"] is True
    assert c["new_postoutcome_scientific_thresholds"] is False
    assert c["known_truth_product_a_source"]["head_sha"] == "715f62ef453636e0e60a4a04d3fa71fdbfdf57a9"
    assert c["independent_empirical_product_a_source"]["run_id"] == 32323931807
    assert c["fresh_known_truth_product_b_v2_source"]["run_id"] == 32345246380


def test_all_predeclared_support_promotes_a_and_unblocks_b(tmp_path):
    a_kt, a_emp, b = _sources(tmp_path)
    out = tmp_path / "out"
    result = apply_promotion_and_unblock(
        contract_path=CONFIG,
        product_a_known_truth_dir=a_kt,
        product_a_empirical_dir=a_emp,
        product_b_known_truth_dir=b,
        output_dir=out,
    )
    assert result["decision"] == "product_a_v2_6_promoted_product_b_v2_unblocked"
    assert result["product_a_v2_6_promoted"] is True
    assert result["product_b_v2_unblocked"] is True
    protocol = json.loads((out / "promoted_product_a_v2_6_protocol.json").read_text())
    unblock = json.loads((out / "product_b_v2_formal_unblock_contract.json").read_text())
    assert protocol["promoted"] is True
    assert protocol["product"]["fundamental_niche_claim_allowed"] is False
    assert unblock["empirical_product_b_execution_allowed"] is True


def test_product_b_failure_does_not_revoke_a_promotion(tmp_path):
    a_kt, a_emp, b = _sources(tmp_path, b_supported=False)
    out = tmp_path / "out"
    result = apply_promotion_and_unblock(
        contract_path=CONFIG,
        product_a_known_truth_dir=a_kt,
        product_a_empirical_dir=a_emp,
        product_b_known_truth_dir=b,
        output_dir=out,
    )
    assert result["decision"] == "product_a_v2_6_promoted_product_b_v2_blocked"
    assert result["product_a_v2_6_promoted"] is True
    assert result["product_b_v2_unblocked"] is False


def test_product_a_empirical_failure_keeps_b_blocked(tmp_path):
    a_kt, a_emp, b = _sources(tmp_path, a_emp_supported=False, b_supported=True)
    out = tmp_path / "out"
    result = apply_promotion_and_unblock(
        contract_path=CONFIG,
        product_a_known_truth_dir=a_kt,
        product_a_empirical_dir=a_emp,
        product_b_known_truth_dir=b,
        output_dir=out,
    )
    assert result["decision"] == "product_a_v2_6_not_promoted_product_b_v2_blocked"
    assert result["product_a_v2_6_promoted"] is False
    assert result["product_b_v2_unblocked"] is False
