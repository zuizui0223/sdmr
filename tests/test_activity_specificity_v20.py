import json
from pathlib import Path

from sdmr.activity_specificity_v20_development import _config

ROOT=Path(__file__).resolve().parents[1]


def test_v20_contract_is_development_only_and_frozen():
    cfg=_config()
    assert cfg["development_only"] is True
    assert cfg["eligible_for_prospective_performance_claim"] is False
    assert cfg["consumed_seed_denominator"] == list(range(16001,16011))
    assert cfg["true_processes"] == ["temperature","water"]
    assert cfg["false_processes"] == ["seasonality","noise"]
    assert cfg["combined_gate"] == "geometry_gate_and_activity_gate"
    assert cfg["new_scientific_thresholds_allowed"] is False
    assert cfg["post_outcome_rule_changes_allowed"] is False


def test_v20_does_not_authorize_fresh_validation():
    cfg=json.loads((ROOT/"configs"/"activity_specificity_v20_development.json").read_text())
    assert cfg["fresh_known_truth_validation_authorized"] is False
    assert cfg["fresh_empirical_validation_authorized"] is False
