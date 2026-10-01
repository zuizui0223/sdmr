import json
from pathlib import Path

CONTRACT=Path("configs/sdmr_v6_full_pipeline_integration_v2.json")

def test_v6_integration_v2_fixes_only_authorization_scope():
    x=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert x["program"]=="sdmr-v6-full-pipeline-integration-v2"
    assert x["status"]=="frozen_pending_execution"
    assert x["seeds"]==list(range(75001,75021))
    assert x["prospective_reserved_seeds"]==list(range(74001,74021))
    assert x["informative_controls"]==[
        "unique_process","redundant_representation","shared_carrier",
        "null_correlated","interaction","geographic_shift"
    ]
    assert x["report_only_world"]=="observation_confounded"
    assert x["null_world"]=="omitted_driver"
    assert x["stage_p"]["authorization_gate"]["minimum_gain_over_null"]==0.01
    assert x["stage_p"]["authorization_gate"]["alpha"]==0.001
    assert x["stage_p"]["margin"]==0.01
    assert x["gate_vector"]["INT-B"]["minimum_positive_recovery"]==0.8
    assert x["gate_vector"]["INT-C"]["maximum_false_positive_rate"]==0.01
    assert x["gate_vector"]["INT-E"]["minimum_each_informative_control_authorization_rate"]==0.95
    assert "minimum_non_w7_authorization_rate" not in x["gate_vector"]["INT-E"]
    assert x["gate_vector"]["INT-E"]["maximum_w7_authorized_count"]==0
    assert x["gate_vector"]["INT-F"]["maximum_stage_p_positive_to_spatial_replaceable_contradiction_rate"]==0.05
    assert x["integration_open"] is False
    assert x["prospective_open"] is False
    assert x["fresh_empirical_open"] is False
