import json
from pathlib import Path


CONTRACT = Path("configs/sdmr_v3_finite_probability_quality_audit_v1.json")


def test_probability_quality_audit_contract_is_development_only():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001, 23009))
    assert payload["worlds"] == [
        "unique_process", "interaction", "geographic_shift"
    ]
    assert payload["learners"] == ["linear", "hgb"]
    assert payload["split_modes"] == ["spatial", "random_cell"]
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["logistic_C"] == 1.0
    assert payload["prospective_status"] == "not_frozen"
    assert payload["prospective_validation_seeds"] == []
    assert payload["fresh_empirical_open"] is False
