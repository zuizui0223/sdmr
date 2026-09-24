import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT=Path("configs/sdmr_v3_stage_p_safety_audit_v3.json")


def test_stage_p_safety_v3_contract_freezes_null_information_gate():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"]=="development_only"
    assert payload["product_a_boundary"]=="closed_not_reopened"
    assert payload["stage"]=="P"
    assert payload["split_mode"]=="random_cell"
    assert payload["require_full_system_information"] is True
    assert payload["full_system_gate"]["information_boundary"]==0
    assert payload["full_system_gate"]["sem_multiplier"]==1.0
    assert payload["full_system_gate"]["absolute_adequacy_floor"]==-0.75
    assert payload["seeds"]==list(range(23001,23009))
    assert tuple(payload["worlds"])==KNOWN_TRUTH_WORLDS
    assert payload["sampling_replicates"]==[0,1,2]
    assert payload["multiplier"]==8
    assert payload["hgb_profile"]=="shallow3"
    assert payload["odo_target"]["state_key_sha256"]=="966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d"
    assert payload["power_tail_target"]["canonical_positive_state_sha256"]=="16fcea7cc49c64bb3f90f7f6f43fd93803286bc740f2b6eab228c6760666ebe5"
    assert payload["prospective_status"]=="not_frozen"
    assert payload["fresh_empirical_open"] is False
