import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"configs"/"sdmr_fresh_empirical_v3_model_freeze.json"
OLD=ROOT/"configs"/"sdmr_fresh_empirical_planning_freeze_v1.json"

def test_v3_freeze_inherits_emp_thresholds_exactly():
    c=json.loads(C.read_text())
    old=json.loads(OLD.read_text())
    g=old["promotion"]["gate_vector"]
    assert c["primary_ecological_metric"]["emp_a_minimum_mean_gain"] == g["EMP-A"]["minimum_mean_gain"] == 0.01
    assert c["primary_ecological_metric"]["emp_b_required_95pct_lower_bound_strictly_above"] == g["EMP-B"]["minimum_lower_bound"] == 0
    assert c["prediction_guardrail"]["noninferiority_margin"] == g["EMP-C"]["noninferiority_margin"] == 0.02
    assert c["process_identification"]["stability"]["emp_d_minimum_stable_fraction"] == g["EMP-D"]["minimum_stable_fraction"] == 0.8
    assert old["promotion"]["gate_vector"]["EMP-E"]["maximum_violation_rate"] == 0
    assert old["promotion"]["gate_vector"]["EMP-F"]["required"] is True

def test_v3_freeze_pins_new_final50_and_no_replacement():
    c=json.loads(C.read_text())
    assert c["cohort"]["exact_taxa"] == 50
    assert c["cohort"]["selected_manifest_sha256"] == "4b49f457bcf8b74969e39144789c8e20a3b9739558475290f0a7abf77d7f9359"
    assert c["cohort"]["support_eligible_candidates"] == 65
    assert c["cohort"]["replacement_after_freeze"] is False

def test_v3_freeze_keeps_answer_check_sealed():
    c=json.loads(C.read_text())
    assert c["data_boundary"]["answer_check_occurrence_coordinates_opened"] is False
    assert c["data_boundary"]["answer_check_environmental_values_opened"] is False
    assert c["data_boundary"]["model_fit_started"] is False
    assert c["feature_prerequisite"]["result_not_used_to_tune_this_contract"] is True

def test_process_method_is_exact_and_abstention_aware():
    c=json.loads(C.read_text())
    p=c["process_identification"]["stage_p"]
    assert p["n_inner_splits"] == 3
    assert p["margin"] == 0.01
    assert p["adequacy_floor"] == -0.75
    assert p["full_system_authorization"]["n_permutations"] == 999
    assert p["full_system_authorization"]["alpha"] == 0.001
    assert c["process_identification"]["stability"]["learner_disagreement"] == "unresolved"
    assert c["sdmr_process_first_prediction"]["representation_refinement"].startswith("not part of the primary")

def test_primary_and_comparator_use_same_hgb_profile():
    c=json.loads(C.read_text())
    h=c["process_identification"]["learner_routes"]["shallow3_hgb"]
    assert h == {
        "role":"primary_prediction_and_stability_route",
        "loss":"log_loss",
        "learning_rate":0.05,
        "max_iter":100,
        "max_leaf_nodes":3,
        "min_samples_leaf":40,
        "l2_regularization":1.0,
        "early_stopping":False,
        "random_state":0,
        "class_balance":"training-only inverse class-frequency sample weights",
    }
    assert c["flat_comparators"]["common_primary_learner"] == "shallow3_hgb"

def test_emp_f_keeps_full_denominator():
    c=json.loads(C.read_text())
    d=c["denominator_and_failure_rules"]
    assert d["declared_taxa"] == 50
    assert d["no_taxon_drop"] is True
    assert d["unavailable_taxon_primary_gain"] == 0.0
    assert d["failed_declared_route_cannot_be_silently_omitted"] is True
