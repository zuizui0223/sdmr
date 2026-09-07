import json
from pathlib import Path

from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation.json"


def test_v6_known_truth_denominator_and_information_barriers_are_frozen() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert c["purpose"] == "proxy_closed_route_process_challenge_v6_prospective_known_truth_validation"
    assert c["scientific_run_authorized"] is True
    assert tuple(c["families"]) == tuple(KNOWN_TRUTH_FAMILIES)
    assert tuple(c["seeds"]) == tuple(range(14001, 14011))
    assert c["n_cases"] == 60
    assert c["n_process_cells"] == 300
    assert c["consumed_real_positive_controls_are_excluded_from_validation"] is True
    assert c["consumed_real_positive_control_labels_may_not_calibrate_any_validation_rule"] is True
    assert c["post_outcome_changes_allowed"] is False
    assert c["threshold_relaxation_allowed"] is False
    assert c["seed_replacement_allowed"] is False
    assert c["family_replacement_allowed"] is False
    assert c["failed_or_null_cases_must_remain_in_denominator"] is True
    assert c["product_a_reopened"] is False


def test_v6_scientific_rule_is_frozen_before_truth_is_opened() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    learner = c["learner"]
    assert learner["relative_noninferiority_margin"] == 0.02
    assert learner["density_noninferiority_margin"] == 0.01
    assert learner["purge_degree"] == 2
    assert learner["purge_ridge_alpha"] == 1.0
    specs = {(float(x["C"]), int(x["degree"])) for x in c["model_specs"]}
    assert specs == {(0.1, 1), (1.0, 1), (10.0, 1), (0.1, 2), (1.0, 2), (10.0, 2)}
    assert c["process_registry"] == [
        {"predictor": "temperature", "process": "temperature", "role": "direct"},
        {"predictor": "temp_proxy", "process": "temperature", "role": "proxy"},
        {"predictor": "water", "process": "water", "role": "direct"},
        {"predictor": "soil", "process": "soil", "role": "direct"},
        {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
        {"predictor": "noise", "process": "noise", "role": "direct"},
    ]


def test_v6_reuses_previous_prospective_numeric_guardrails_instead_of_consumed_controls() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    gate = c["primary_process_thresholds"]
    assert gate["source"] == "inherited_numeric_guardrails_from_ecological_identification_learner_validation_successor_v2"
    assert gate["false_required_rate_max"] == 0.02
    assert gate["true_process_recall_min"] == 0.95
    assert gate["process_status_macro_f1_min"] == 0.90
    assert gate["family_true_process_recall_min"] == 0.85
    assert gate["required_claims_must_have_complete_route_evidence"] is True
    assert c["fresh_empirical_validation_required_after_known_truth_support"] is True
