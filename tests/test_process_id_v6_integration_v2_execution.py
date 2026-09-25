import json
from pathlib import Path

PROFILE=Path("configs/sdmr_v6_full_pipeline_integration_v2_execution.json")

def test_v6_integration_v2_execution_is_frozen_and_blocked():
    x=json.loads(PROFILE.read_text(encoding="utf-8"))
    assert x["program"]=="sdmr-v6-full-pipeline-integration-v2-execution"
    assert x["status"]=="frozen_blocked"
    assert [s for block in x["sharding"]["seed_blocks"] for s in block]==list(range(75001,75021))
    assert x["sharding"]["expected_shards"]==32
    assert x["prerequisites"]["validation"]["terminal_passed"] is True
    assert x["prerequisites"]["confirmation"]["terminal_passed"] is True
    assert x["activation_status"]=="blocked"
    assert x["integration_outcomes_opened"] is False
    assert x["prospective_open"] is False
    assert x["fresh_empirical_open"] is False
