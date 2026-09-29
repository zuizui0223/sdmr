import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_8x_safety_audit_v2.json")


def test_8x_safety_v2_is_seed_index_correction_only():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"]=="development_only"
    assert payload["product_a_boundary"]=="closed_not_reopened"
    assert payload["correction_of"]=="sdmr-v3-8x-safety-audit-v1"
    assert payload["sampling_seed_world_index_mode"]=="frozen_global_world_order"
    assert payload["seeds"]==list(range(23001,23009))
    assert tuple(payload["worlds"])==KNOWN_TRUTH_WORLDS
    assert payload["split_modes"]==["spatial","random_cell"]
    assert payload["sampling_replicates"]==[0,1,2]
    assert payload["multiplier"]==8
    assert payload["hgb_profile"]=="shallow3"
    assert payload["margin"]==0.01
    assert payload["adequacy_floor"]==-0.75
    assert payload["sem_multiplier"]==1.0
    assert payload["odo_target"]["state_key_sha256"]=="966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d"
    assert payload["power_tail_target"]["canonical_positive_state_sha256"]["random_cell"]=="16fcea7cc49c64bb3f90f7f6f43fd93803286bc740f2b6eab228c6760666ebe5"
    assert payload["power_tail_target"]["canonical_positive_state_sha256"]["spatial"]=="fed1a0826856918e5cbe56d75308a45a70b7ff4558c1727bd8c7cfa86eb0f7d5"
    assert payload["prospective_status"]=="not_frozen"
    assert payload["fresh_empirical_open"] is False
