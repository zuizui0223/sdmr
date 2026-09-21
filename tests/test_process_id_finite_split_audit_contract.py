import json
from pathlib import Path


CONFIG=Path("configs/sdmr_v3_finite_split_geometry_audit_v1.json")


def test_finite_split_geometry_contract_is_development_only():
    payload=json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001,23009))
    assert payload["worlds"] == ["unique_process","interaction","geographic_shift"]
    assert payload["learner"] == "hgb"
    assert payload["split_modes"] == ["spatial","random_cell"]
    assert payload["prospective_status"] == "not_frozen"
    assert payload["prospective_validation_seeds"] == []
    assert payload["fresh_empirical_open"] is False


def test_finite_split_geometry_contract_keeps_scientific_thresholds_fixed():
    payload=json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["margin"] == 0.01
    assert payload["adequacy_floor"] == -0.75
    assert payload["sem_multiplier"] == 1.0
    assert payload["odo_target"]["workflow_run"] == 35495871747
    assert payload["odo_target"]["artifact_id"] == 10601311224
    assert payload["odo_target"]["split_mode"] == "random"
