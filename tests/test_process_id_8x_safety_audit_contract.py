import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_8x_safety_audit_v1.json")


def test_8x_safety_contract_freezes_candidate_regime_and_targets():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001,23009))
    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["split_modes"] == ["spatial","random_cell"]
    assert payload["sampling_replicates"] == [0,1,2]
    assert payload["multiplier"] == 8
    assert payload["hgb_profile"] == "shallow3"
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["margin"] == 0.01
    assert payload["adequacy_floor"] == -0.75
    assert payload["sem_multiplier"] == 1.0
    assert payload["odo_target"]["state_key_sha256"] == "966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d"
    assert payload["screen_target"]["selected_profile"] == "shallow3"
    assert payload["screen_target"]["selection_used_process_recovery"] is False
    assert payload["power_tail_target"]["workflow_run"] == 35981741906
    assert payload["prospective_status"] == "not_frozen"
    assert payload["fresh_empirical_open"] is False


def test_8x_safety_contract_pins_world_level_odo_hashes():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    hashes = payload["odo_target"]["world_state_sha256"]
    assert set(hashes) == set(KNOWN_TRUTH_WORLDS)
    assert hashes["unique_process"] == "a0e22591d236e96d367ded8c07f8731407364e1bdf0b8e8ee500d53e9c871a15"
    assert hashes["interaction"] == "a065a0fe568e9b7e789995a7e5a0568cf4d94c1896649aa52498a96ad42807d3"
    assert hashes["omitted_driver"] == "920ad11a7852ca900082dde7b91c038ae308c92af105b01ff9cf9bdb5c55616a"
