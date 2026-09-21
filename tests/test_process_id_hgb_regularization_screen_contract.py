import json
from pathlib import Path


CONTRACT = Path("configs/sdmr_v3_hgb_regularization_screen_v1.json")


def test_hgb_regularization_screen_contract_forbids_process_based_selection():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001, 23009))
    assert payload["worlds"] == [
        "unique_process", "interaction", "geographic_shift"
    ]
    assert payload["split_modes"] == ["spatial", "random_cell"]
    assert payload["profiles"] == ["current", "shallow7", "shallow3", "early7"]
    assert payload["adequacy_floor"] == -0.75
    assert payload["tie_margin"] == 0.005
    assert payload["selection_uses_process_recovery"] is False
    assert payload["prospective_status"] == "not_frozen"
    assert payload["prospective_validation_seeds"] == []
    assert payload["fresh_empirical_open"] is False
