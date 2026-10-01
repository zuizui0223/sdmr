import json
from pathlib import Path


CONTRACT=Path("configs/sdmr_v5_prospective_kt_v1.json")
EXECUTION=Path("configs/sdmr_v5_prospective_kt_v1_execution.json")


def test_v5_prospective_contract_is_frozen_before_integration_outcome():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["program"]=="sdmr-v5-prospective-known-truth-v1"
    assert payload["status"]=="frozen_pending_integration_prerequisite"
    assert payload["product_a_boundary"]=="closed_not_reopened"

    assert payload["prerequisites"]["validation"]["terminal_passed"] is True
    assert payload["prerequisites"]["confirmation"]["terminal_passed"] is True
    assert payload["prerequisites"]["integration"]["required_terminal_decision"]=="passed"
    assert payload["prerequisites"]["integration"]["outcome_not_opened_when_contract_frozen"] is True

    assert payload["seeds"]==list(range(53001,53021))
    assert payload["replacement_policy"]=="forbidden_after_any_prospective_outcome_access"
    assert payload["expected_odo_counts_total"]=={
        "positive":80,
        "replaceable":700,
        "unresolved":60,
        "unavailable":120,
        "structural_refusal":60,
    }

    stage_p=payload["stage_p"]
    assert stage_p["multiplier"]==8
    assert stage_p["n_occurrences"]==1440
    assert stage_p["n_background"]==4800
    assert stage_p["n_splits"]==3
    assert stage_p["hgb_profile"]=="shallow3"
    assert stage_p["split_mode"]=="random_cell"
    assert stage_p["margin"]==0.01
    assert stage_p["adequacy_floor"]==-0.75

    perm=stage_p["permutation_gate"]
    assert perm["n_permutations"]==999
    assert perm["alpha"]==0.001
    assert perm["permutation_seed"]==0
    assert perm["require_positive_gain_over_null"] is True

    gates=payload["gate_vector"]
    assert gates["KT-B"]["minimum"]==0.80
    assert gates["KT-C"]["maximum"]==0.01
    assert gates["KT-D"]["max_overresolution_rate_among_odo_unresolved"]==0.0
    assert gates["KT-D"]["max_structural_refusal_violation_rate"]==0.0
    assert gates["KT-E"]["max_sharp_rate_among_odo_unavailable"]==0.0
    assert gates["KT-E"]["max_favorable_positive_rate_among_odo_unavailable"]==0.0
    assert gates["KT-E"]["max_w7_authorized_count"]==0
    assert gates["KT-E"]["min_non_w7_full_system_authorization_rate"]==0.95
    assert gates["KT-F"]["max_stage_p_positive_to_spatial_replaceable_contradiction_rate"]==0.05

    assert payload["activation_status"]=="blocked"
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False


def test_v5_prospective_execution_profile_is_blocked_and_complete():
    payload=json.loads(EXECUTION.read_text(encoding="utf-8"))

    assert payload["program"]=="sdmr-v5-prospective-known-truth-v1-execution"
    assert payload["status"]=="frozen_blocked"
    assert payload["scientific_contract_path"]=="configs/sdmr_v5_prospective_kt_v1.json"
    assert payload["scientific_contract_blob_sha"]=="d61025bef92049da1c121e053403cf75dd64a396"

    blocks=payload["sharding"]["seed_blocks"]
    assert len(blocks)==4
    assert [seed for block in blocks for seed in block]==list(range(53001,53021))
    assert payload["sharding"]["expected_shards"]==32

    assert payload["odo_v2"]=={
        "n_splits":3,
        "margin":0.01,
        "sem_multiplier":1.0,
        "adequacy_floor":-0.75,
        "approximation_tolerance":0.01,
        "split_mode":"random",
    }

    assert payload["prerequisites"]["validation"]["terminal_passed"] is True
    assert payload["prerequisites"]["confirmation"]["terminal_passed"] is True
    assert payload["prerequisites"]["integration"]["terminal_passed"] is False
    assert payload["activation_status"]=="blocked"
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False
