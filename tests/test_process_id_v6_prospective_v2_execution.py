import json
from pathlib import Path

PROFILE=Path("configs/sdmr_v6_prospective_kt_v2_execution.json")
CONTRACT=Path("configs/sdmr_v6_prospective_kt_v2.json")

def test_v6_prospective_v2_execution_is_frozen_and_blocked():
    x=json.loads(PROFILE.read_text(encoding="utf-8"))
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert x["program"]=="sdmr-v6-prospective-known-truth-v2-execution"
    assert x["status"]=="frozen_blocked"
    assert x["scientific_contract_path"]=="configs/sdmr_v6_prospective_kt_v2.json"
    assert x["scientific_contract_blob_sha"]=="bdef009362fb4bd6025e616743605bd9787a5008"
    assert [s for block in x["sharding"]["seed_blocks"] for s in block]==list(range(74001,74021))
    assert x["sharding"]["expected_shards"]==32
    assert x["prerequisites"]["validation"]["terminal_passed"] is True
    assert x["prerequisites"]["confirmation"]["terminal_passed"] is True
    assert x["prerequisites"]["integration"]["terminal_passed"] is False
    assert x["activation_status"]=="blocked"
    assert x["prospective_outcomes_opened"] is False
    assert x["fresh_empirical_open"] is False

    assert c["status"]=="frozen_pending_integration_v2_prerequisite"
    assert c["seeds"]==list(range(74001,74021))
    assert c["informative_controls"]==[
        "unique_process","redundant_representation","shared_carrier",
        "null_correlated","interaction","geographic_shift"
    ]
    assert c["report_only_world"]=="observation_confounded"
    assert c["null_world"]=="omitted_driver"
    assert c["gate_vector"]["KT-E"]["minimum_each_informative_control_authorization_rate"]==0.95
    assert c["gate_vector"]["KT-E"]["maximum_w7_authorized_count"]==0
    assert c["activation_status"]=="blocked"
    assert c["prospective_outcomes_opened"] is False
