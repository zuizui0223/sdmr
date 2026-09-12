import json
from pathlib import Path

from sdmr.two_tier_process_support_v21_prospective import load_contract

ROOT = Path(__file__).resolve().parents[1]


def test_v21_contract_is_fresh_and_frozen():
    cfg = load_contract()
    assert cfg["fresh_seed_denominator"] == list(range(17001,17011))
    assert cfg["true_processes"] == ["temperature","water"]
    assert cfg["false_processes"] == ["seasonality","noise"]
    assert cfg["supported_rule"] == "context_status_equals_context_contributory"
    assert cfg["high_confidence_supported_rule"] == "supported_and_frozen_v19_geometry_eligible"
    assert cfg["classifier_refit_allowed"] is False
    assert cfg["new_scientific_thresholds_allowed"] is False
    assert cfg["post_outcome_rule_changes_allowed"] is False


def test_v21_success_criteria_are_precommitted():
    cfg = json.loads((ROOT/"configs"/"two_tier_process_support_v21_prospective.json").read_text())
    assert cfg["success_criteria"]["supported"] == {
        "positive_process_precision_min": 0.90,
        "true_process_positive_rate_min": 0.35,
        "false_process_positive_rate_max": 0.05,
    }
    assert cfg["success_criteria"]["high_confidence_supported"] == {
        "positive_process_precision_min": 0.95,
        "true_process_positive_rate_min": 0.20,
        "false_process_positive_rate_max": 0.02,
    }
    assert cfg["fresh_empirical_validation_authorized_before_terminal"] is False
