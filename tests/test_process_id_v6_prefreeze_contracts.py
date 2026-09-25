import json
from pathlib import Path

INTEGRATION=Path("configs/sdmr_v6_full_pipeline_integration_v1.json")
PROSPECTIVE=Path("configs/sdmr_v6_prospective_kt_v1.json")

def test_v6_integration_and_prospective_contracts_are_prefrozen():
    integration=json.loads(INTEGRATION.read_text(encoding="utf-8"))
    prospective=json.loads(PROSPECTIVE.read_text(encoding="utf-8"))

    assert integration["status"]=="frozen_blocked_by_gate_validation"
    assert integration["seeds"]==list(range(73001,73021))
    assert integration["prospective_reserved_seeds"]==list(range(74001,74021))
    assert integration["stage_p"]["authorization_gate"]["minimum_gain_over_null"]==0.01
    assert integration["stage_p"]["authorization_gate"]["alpha"]==0.001
    assert integration["integration_open"] is False
    assert integration["prospective_open"] is False

    assert prospective["status"]=="frozen_pending_integration_prerequisite"
    assert prospective["seeds"]==list(range(74001,74021))
    assert prospective["stage_p"]["authorization_gate"]["minimum_gain_over_null"]==0.01
    assert prospective["gate_vector"]["KT-B"]["minimum"]==0.80
    assert prospective["gate_vector"]["KT-C"]["maximum"]==0.01
    assert prospective["gate_vector"]["KT-E"]["max_w7_authorized_count"]==0
    assert prospective["activation_status"]=="blocked"
    assert prospective["prospective_outcomes_opened"] is False
    assert prospective["fresh_empirical_open"] is False
