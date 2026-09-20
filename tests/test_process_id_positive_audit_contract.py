import json
from pathlib import Path


CONTRACT = Path("configs/sdmr_v3_positive_evidence_audit_v1.json")


def test_positive_audit_contract_is_diagnostic_only_and_reuses_burned_evidence():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "diagnostic_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001, 23009))
    assert payload["worlds"] == ["unique_process", "interaction", "geographic_shift"]
    assert payload["learners"] == ["linear", "quadratic"]
    assert payload["prospective_status"] == "not_frozen"
    assert payload["fresh_empirical_open"] is False


def test_positive_audit_contract_inherits_v3_scientific_settings_without_retuning():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["oracle"] == {
        "margin": 0.02,
        "sem_multiplier": 1.0,
        "baseline_r2_floor": 0.70,
        "required_r2_ceiling": 0.0,
    }
    assert payload["occurrence"] == {
        "margin": 0.01,
        "sem_multiplier": 1.0,
        "adequacy_floor": -0.75,
        "logistic_C": 1.0,
        "fit_class_weight": "balanced",
    }
