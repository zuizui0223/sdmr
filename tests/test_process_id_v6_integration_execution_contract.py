import json
from pathlib import Path

PROFILE=Path("configs/sdmr_v6_full_pipeline_integration_v1_execution.json")

def test_v6_integration_execution_profile_is_blocked_and_frozen():
    x=json.loads(PROFILE.read_text(encoding="utf-8"))
    assert x["status"]=="frozen_blocked"
    assert x["activation_status"]=="blocked"
    assert x["integration_outcomes_opened"] is False
    assert x["prospective_open"] is False
    assert x["fresh_empirical_open"] is False
    assert [s for block in x["sharding"]["seed_blocks"] for s in block]==list(range(73001,73021))
    assert x["sharding"]["expected_shards"]==32
    assert x["prerequisites"]["validation"]["terminal_passed"] is False
    assert x["prerequisites"]["confirmation"]["terminal_passed"] is False
