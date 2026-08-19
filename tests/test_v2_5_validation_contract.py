import pandas as pd

from sdmr.v2_5_validation_contract import (
    load_v2_5_validation_contract,
    v2_5_decision,
)


def _summary(**overrides):
    rows=[]
    for panel in ("panel_D1", "panel_D2", "panel_D3"):
        row={
            "panel": panel,
            "n_validation_taxa": 3,
            "n_complete_process_certificates": 3,
            "n_complete_boundary_certificates": 3,
            "n_calibrated_response_keys": 21,
            "n_complete_calibrated_intervals": 21,
            "total_false_required_processes": 0,
            "minimum_possible_process_recall": 1.0,
            "complete_adequate_boundary_coverage": 0.50,
            "v2_5_calibrated_boundary_coverage": 0.60,
        }
        row.update(overrides)
        rows.append(row)
    return pd.DataFrame(rows)


def test_validation_contract_is_frozen_before_fresh_truth():
    payload=load_v2_5_validation_contract(
        "configs/product_a_v2_5_validation_contract.json"
    )
    assert payload["validation_truth_read_before_all_products_frozen"] is False
    assert payload["worker_contract"]["n_worker_cells"] == 54
    assert payload["boundary_certificate"]["validation_truth_used_for_calibration"] is False


def test_supported_requires_both_process_and_boundary_support():
    decision=v2_5_decision(_summary()).iloc[0]
    assert decision["decision"] == "v2_5_supported"
    assert bool(decision["all_panels_available"])
    assert bool(decision["process_support"])
    assert bool(decision["boundary_support"])
    assert not bool(decision["scientific_promotion_allowed"])


def test_missing_calibrated_key_is_unavailable_not_negative_support():
    decision=v2_5_decision(_summary(n_complete_calibrated_intervals=20)).iloc[0]
    assert decision["decision"] == "v2_5_unavailable"
    assert not bool(decision["all_panels_available"])


def test_false_required_process_blocks_process_support():
    decision=v2_5_decision(_summary(total_false_required_processes=1)).iloc[0]
    assert decision["decision"] == "v2_5_boundary_only"
    assert not bool(decision["process_support"])
    assert bool(decision["boundary_support"])


def test_boundary_must_not_underperform_complete_adequate_comparator():
    decision=v2_5_decision(
        _summary(v2_5_calibrated_boundary_coverage=0.49)
    ).iloc[0]
    assert decision["decision"] == "v2_5_process_only"
    assert bool(decision["process_support"])
    assert not bool(decision["boundary_support"])
