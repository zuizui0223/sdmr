import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_occurrence_distribution_oracle_audit_v1.json")


def test_occurrence_oracle_audit_contract_is_development_only_and_complete():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001, 23009))
    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["prospective_status"] == "not_frozen"
    assert payload["prospective_validation_seeds"] == []
    assert payload["fresh_empirical_open"] is False


def test_occurrence_oracle_audit_contract_freezes_all_three_levels():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3

    assert payload["truth_oracle"] == {
        "margin": 0.02,
        "sem_multiplier": 1.0,
        "baseline_r2_floor": 0.70,
        "required_r2_ceiling": 0.0,
    }
    assert payload["occurrence_oracle"] == {
        "margin": 0.01,
        "sem_multiplier": 1.0,
        "adequacy_floor": -0.75,
        "approximation_tolerance": 0.01,
    }
    assert payload["finite"] == {
        "margin": 0.01,
        "sem_multiplier": 1.0,
        "adequacy_floor": -0.75,
        "logistic_C": 1.0,
        "learners": ["linear", "quadratic"],
        "fit_class_weight": "balanced",
    }
