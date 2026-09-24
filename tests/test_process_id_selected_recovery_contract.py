import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_selected_nonlinear_recovery_v1.json")


def test_selected_recovery_contract_freezes_screen_and_odo_targets():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["seeds"] == list(range(23001, 23009))
    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["learners"] == ["linear", "quadratic", "hgb"]
    assert payload["split_modes"] == ["spatial", "random_cell"]
    assert payload["hgb_profile"] == "shallow3"
    assert payload["n_cells"] == 1600
    assert payload["n_occurrences"] == 180
    assert payload["n_background"] == 600
    assert payload["n_splits"] == 3
    assert payload["margin"] == 0.01
    assert payload["adequacy_floor"] == -0.75
    assert payload["sem_multiplier"] == 1.0
    assert payload["odo_target"]["workflow_run"] == 35495871747
    assert payload["odo_target"]["artifact_id"] == 10601311224
    assert payload["odo_target"]["artifact_digest"] == "sha256:bc67412ccf10e40cd5039f204410bf31f96773de4d0f808268e2773e9192488c"
    assert payload["odo_target"]["state_key_sha256"] == "966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d"
    assert payload["screen_target"]["workflow_run"] == 35608090218
    assert payload["screen_target"]["artifact_id"] == 10644928842
    assert payload["screen_target"]["artifact_digest"] == "sha256:1a07609267cfba8ef443f3a956cf7015a2caf8db65a7af9e63b0a48c3157edaf"
    assert payload["screen_target"]["selected_profile"] == "shallow3"
    assert payload["screen_target"]["selection_used_process_recovery"] is False
    assert payload["prospective_status"] == "not_frozen"
    assert payload["fresh_empirical_open"] is False
