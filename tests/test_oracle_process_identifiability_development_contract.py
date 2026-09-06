import json
from pathlib import Path

from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES


CONFIG = Path("configs/oracle_process_identifiability_development.json")


def test_oracle_development_denominator_is_fixed_and_development_only() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["purpose"] == "oracle_observational_identifiability_development_only"
    assert payload["development_only"] is True
    assert payload["eligible_for_prospective_performance_claim"] is False
    assert tuple(payload["families"]) == tuple(KNOWN_TRUTH_FAMILIES)
    assert tuple(payload["seeds"]) == tuple(range(13001, 13011))
    assert payload["n_cases"] == 60
    assert payload["product_a_reopened"] is False
    assert payload["development_seeds_must_never_be_reused_for_future_prospective_validation"] is True


def test_oracle_target_is_independent_of_occurrence_and_learner_outputs() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["truth_target"] == "complete_true_suitability_surface"
    assert payload["occurrence_outcomes_used_by_oracle"] is False
    assert payload["learner_outputs_used_by_oracle"] is False
    assert payload["generating_process_membership_used_by_oracle"] is False
    assert payload["spatial_grouping"]["source"] == "all_environment_cell_coordinates"


def test_oracle_thresholds_are_explicitly_development_heuristics() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    oracle = payload["oracle"]
    assert oracle["n_splits"] == 5
    assert oracle["relative_loss_margin"] == 0.02
    assert oracle["sem_multiplier"] == 1.0
    assert oracle["baseline_r2_floor"] == 0.80
    assert oracle["required_r2_ceiling"] == 0.0
    assert oracle["threshold_status"] == "development_heuristics_not_prospectively_validated"
