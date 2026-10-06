import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/"configs"/"sdmr_fresh_empirical_v5_model_design.json"
PLANNING=ROOT/"configs"/"sdmr_fresh_empirical_planning_freeze_v1.json"


def _model():
    return json.loads(MODEL.read_text())


def test_v5_model_design_freezes_before_cohort_binding_and_fit():
    c=_model()
    assert c["status"]=="model_design_frozen_before_final50_numeric_features_and_model_fit"
    assert c["cohort_binding"]["exact_taxa"]==50
    assert c["cohort_binding"]["binding_status"]=="pending_preeligibility_terminal_pass"
    assert c["feature_prerequisite"]["result_not_used_to_tune_this_contract"] is True


def test_v5_model_design_inherits_emp_thresholds_exactly():
    c=_model()
    p=json.loads(PLANNING.read_text())
    g=p["promotion"]["gate_vector"]
    assert c["primary_ecological_metric"]["emp_a_minimum_mean_gain"]==g["EMP-A"]["minimum_mean_gain"]==0.01
    assert c["primary_ecological_metric"]["emp_b_required_95pct_lower_bound_strictly_above"]==g["EMP-B"]["minimum_lower_bound"]==0
    assert c["prediction_guardrail"]["noninferiority_margin"]==g["EMP-C"]["noninferiority_margin"]==0.02
    assert c["process_identification"]["stability"]["emp_d_minimum_stable_fraction"]==g["EMP-D"]["minimum_stable_fraction"]==0.8
    assert g["EMP-E"]["maximum_violation_rate"]==0
    assert g["EMP-F"]["required"] is True


def test_v5_model_design_keeps_same_primary_and_comparator_learner():
    c=_model()
    h=c["process_identification"]["learner_routes"]["shallow3_hgb"]
    assert h["max_leaf_nodes"]==3
    assert h["learning_rate"]==0.05
    assert h["max_iter"]==100
    assert h["min_samples_leaf"]==40
    assert h["l2_regularization"]==1
    assert h["early_stopping"] is False
    assert c["flat_comparators"]["common_primary_learner"]=="shallow3_hgb"
    assert c["sdmr_process_first_prediction"]["primary_learner"]=="shallow3_hgb"


def test_v5_model_design_keeps_answer_check_last():
    c=_model()
    order=c["answer_check_opening_order"]
    assert order[0].startswith("preeligibility")
    assert order[1].startswith("feature gate")
    assert "only then materialize answer-check" in order[4]
    d=c["denominator_and_failure_rules"]
    assert d["declared_taxa"]==50
    assert d["no_taxon_drop"] is True
    assert d["no_taxon_replacement"] is True
    assert d["failed_declared_route_cannot_be_silently_omitted"] is True


def test_v5_model_design_keeps_process_abstention_and_spatial_split():
    c=_model()
    stage=c["process_identification"]["stage_p"]
    assert stage["split_mode"]=="spatial"
    assert stage["n_inner_splits"]==3
    assert stage["margin"]==0.01
    assert stage["adequacy_floor"]==-0.75
    assert stage["full_system_authorization"]["n_permutations"]==999
    assert stage["full_system_authorization"]["alpha"]==0.001
    assert c["process_identification"]["stability"]["learner_disagreement"]=="unresolved"
