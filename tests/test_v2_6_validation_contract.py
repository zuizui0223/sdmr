from pathlib import Path

import pandas as pd

from sdmr.v2_6_validation_contract import (
    SOURCE_CALIBRATION_ARTIFACT_NAME,
    SOURCE_CALIBRATION_HEAD_SHA,
    SOURCE_CALIBRATION_RUN_ID,
    load_v2_6_validation_contract,
    v2_6_decision,
)

CONFIG = Path("configs/product_a_v2_6_validation_contract.json")


def test_v26_validation_contract_keeps_reserved_truth_and_source_gate():
    c = load_v2_6_validation_contract(CONFIG)
    assert c["source_calibration"]["run_id"] == SOURCE_CALIBRATION_RUN_ID
    assert c["source_calibration"]["head_sha"] == SOURCE_CALIBRATION_HEAD_SHA
    assert c["source_calibration"]["artifact_name"] == SOURCE_CALIBRATION_ARTIFACT_NAME
    seeds = [row["seed"] for panel in c["validation"].values() for row in panel]
    assert sorted(seeds) == [501, 502, 503, 511, 512, 513, 521, 522, 523]
    assert c["boundary_certificate"]["minimum_complete_calibration_taxa_per_key"] == 2
    assert c["worker_contract"]["validation_role_offset"] == 5000000


def _summary(process=True, boundary=True):
    rows = []
    for panel in ("panel_D1", "panel_D2", "panel_D3"):
        rows.append({
            "panel": panel,
            "n_validation_taxa": 3,
            "n_complete_process_certificates": 3,
            "n_complete_boundary_certificates": 3,
            "n_calibrated_response_keys": 9,
            "n_complete_calibrated_intervals": 9,
            "total_false_required_processes": 0 if process else 1,
            "minimum_possible_process_recall": 1.0 if process else 0.8,
            "complete_adequate_boundary_coverage": 0.8,
            "v2_6_calibrated_boundary_coverage": 0.8 if boundary else 0.7,
        })
    return pd.DataFrame(rows)


def test_v26_decision_states_are_frozen():
    assert v2_6_decision(_summary(True, True)).iloc[0]["decision"] == "v2_6_supported"
    assert v2_6_decision(_summary(True, False)).iloc[0]["decision"] == "v2_6_process_only"
    assert v2_6_decision(_summary(False, True)).iloc[0]["decision"] == "v2_6_boundary_only"
    assert v2_6_decision(_summary(False, False)).iloc[0]["decision"] == "v2_6_not_supported"
