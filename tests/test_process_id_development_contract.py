import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_process_id_development_v1.json")


def test_development_contract_is_burned_and_not_prospective():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["seeds"] == list(range(23001, 23009))
    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["prospective_status"] == "not_frozen"
    assert payload["fresh_empirical_open"] is False
    assert payload["product_a_boundary"] == "closed_not_reopened"


def test_development_contract_freezes_execution_profile():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["oracle"]["margin"] == 0.02
    assert payload["oracle"]["sem_multiplier"] == 1.0
    assert payload["oracle"]["baseline_r2_floor"] == 0.70
    assert payload["oracle"]["required_r2_ceiling"] == 0.0
    assert payload["occurrence"]["margin"] == 0.01
    assert payload["occurrence"]["sem_multiplier"] == 1.0
    assert payload["occurrence"]["adequacy_floor"] == -0.75
    assert payload["occurrence"]["logistic_C"] == 1.0
