import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_full_system_gate_audit_v1.json")


def test_full_system_gate_audit_contract_freezes_natural_zero_boundary():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"]=="development_only"
    assert payload["product_a_boundary"]=="closed_not_reopened"
    assert payload["seeds"]==list(range(23001,23009))
    assert tuple(payload["worlds"])==KNOWN_TRUTH_WORLDS
    assert payload["split_modes"]==["spatial","random_cell"]
    assert payload["sampling_replicates"]==[0,1,2]
    assert payload["multiplier"]==8
    assert payload["hgb_profile"]=="shallow3"
    assert payload["n_occurrences"]==180
    assert payload["n_background"]==600
    assert payload["n_splits"]==3
    assert payload["sem_multiplier"]==1.0
    assert payload["adequacy_floor"]==-0.75
    assert payload["null_information_boundary"]==0.0
    assert payload["null_balanced_log_score"]=="-log(2)"
    assert payload["odo_target"]["state_key_sha256"]=="966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d"
    assert payload["odo_target"]["unavailable_world"]=="omitted_driver"
    assert payload["prospective_status"]=="not_frozen"
    assert payload["fresh_empirical_open"] is False
