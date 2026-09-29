import json
from pathlib import Path


CONFIG = Path("configs/sdmr_v3_finite_recovery_audit_v1.json")


def test_finite_recovery_audit_contract_is_development_only():
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["prospective_status"] == "not_frozen"
    assert payload["prospective_validation_seeds"] == []
    assert payload["fresh_empirical_open"] is False
    assert payload["seeds"] == list(range(23001, 23009))


def test_finite_recovery_audit_freezes_odo_target_and_factorial_profile():
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["odo_target"]["workflow_run"] == 35495871747
    assert payload["odo_target"]["artifact_id"] == 10601311224
    assert payload["odo_target"]["split_mode"] == "random"
    assert payload["odo_target"]["approximation_tolerance"] == 0.01
    assert payload["worlds"] == [
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "observation_confounded",
        "geographic_shift",
    ]
    assert payload["baseline_learners"] == ["linear", "quadratic", "hgb"]
    assert payload["sample_multipliers"] == [1, 2, 4]
    assert payload["sampling_replicates"] == [0, 1, 2]
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["margin"] == 0.01
    assert payload["adequacy_floor"] == -0.75
    assert payload["sem_multiplier"] == 1.0
