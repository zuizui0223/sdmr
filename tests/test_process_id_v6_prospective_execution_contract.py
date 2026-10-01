import json
from pathlib import Path

PROFILE=Path("configs/sdmr_v6_prospective_kt_v1_execution.json")

def test_v6_prospective_execution_profile_is_blocked_and_frozen():
    x=json.loads(PROFILE.read_text(encoding="utf-8"))
    assert x["program"]=="sdmr-v6-prospective-known-truth-v1-execution"
    assert x["status"]=="frozen_blocked"
    assert x["scientific_contract_path"]=="configs/sdmr_v6_prospective_kt_v1.json"
    assert x["scientific_contract_blob_sha"]=="4e2e5d502a5d04bd1912f8483a0bbbe2feb4bf73"
    assert x["activation_status"]=="blocked"
    assert x["prospective_outcomes_opened"] is False
    assert x["fresh_empirical_open"] is False
    assert [s for block in x["sharding"]["seed_blocks"] for s in block]==list(range(74001,74021))
    assert x["sharding"]["expected_shards"]==32
    assert x["prerequisites"]["validation"]["terminal_passed"] is True
    assert x["prerequisites"]["confirmation"]["terminal_passed"] is False
    assert x["prerequisites"]["integration"]["terminal_passed"] is False
