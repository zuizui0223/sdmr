import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/"results"/"sdmr_nonlinear_effort_v2_prospective_result.json"

def test_nonlinear_effort_result_is_complete_and_bounded():
    r=json.loads(R.read_text())
    assert r["authoritative_execution"]["workflow_run"] == 38351952478
    assert r["audit"]["finite_fit_records_checked"] == 4536
    assert r["audit"]["full_system_permutation_pvalues_independently_verified"] == 216
    assert r["boundaries"]["original_M5_evidence_changed"] is False
    assert r["boundaries"]["original_real_v5_promotion"] == "failed_closed"
    assert r["boundaries"]["method_promotion_authorized"] is False

def test_primary_nonlinear_pair_improves_positive_recovery_but_not_overresolution():
    r=json.loads(R.read_text())["primary_effort_unavailable"]
    assert r["spatial"]["baseline_hgb_l2"]["positive_recovered"] == [0,12]
    assert r["spatial"]["nonlinear_hgb_rf"]["positive_recovered"] == [4,12]
    assert r["spatial"]["baseline_hgb_l2"]["overresolved_unresolved"] == [1,3]
    assert r["spatial"]["nonlinear_hgb_rf"]["overresolved_unresolved"] == [1,3]
    assert r["random_cell"]["baseline_hgb_l2"]["false_positive_replaceable"] == [0,75]
    assert r["random_cell"]["nonlinear_hgb_rf"]["false_positive_replaceable"] == [0,75]

def test_observation_confounded_unsafe_case_is_preserved():
    u=json.loads(R.read_text())["primary_effort_unavailable"]["unsafe_case"]
    assert u == {
      "world":"observation_confounded",
      "seed":92003,
      "process":"thermal",
      "oracle_state":"unresolved",
      "random_cell_baseline_state":"contributory",
      "random_cell_nonlinear_state":"contributory",
      "spatial_baseline_state":"contributory",
      "spatial_nonlinear_state":"contributory"
    }

def test_known_effort_is_marked_secondary_different_universe():
    r=json.loads(R.read_text())["secondary_known_effort_upper_bound"]
    assert "Different representation universe" in r["interpretation_boundary"]
    assert r["random_cell"]["nonlinear_hgb_rf"]["overresolved_unresolved"] == [3,3]
    assert r["spatial"]["nonlinear_hgb_rf"]["overresolved_unresolved"] == [1,3]
