import json
from pathlib import Path

CONTRACT=Path("configs/sdmr_v5_permutation_gate_validation_v1.json")

def test_v5_permutation_validation_contract_is_frozen_before_outcomes():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"]=="development_only_frozen_before_outcomes"
    assert payload["predecessor_terminal_failure"]=="W7_false_authorization_2_of_50"
    assert payload["seeds"]["validation"]==list(range(51001,51101))
    assert payload["seeds"]["confirmation"]==list(range(52001,52051))
    assert payload["seeds"]["reserved_future_prospective"]==list(range(53001,53021))
    assert payload["seed_use"]=={
        "validation_open":False,
        "confirmation_open":False,
        "reserved_future_prospective_open":False,
    }

    finite=payload["finite_architecture"]
    assert finite["multiplier"]==8
    assert finite["n_occurrences"]==1440
    assert finite["n_background"]==4800
    assert finite["n_cells"]==1600
    assert finite["n_splits"]==3
    assert finite["learner"]=="hgb"
    assert finite["hgb_profile"]=="shallow3"
    assert finite["split_mode"]=="random_cell"
    assert finite["adequacy_floor"]==-0.75

    gate=payload["permutation_gate"]
    assert gate["n_permutations"]==999
    assert gate["alpha"]==0.001
    assert gate["permutation_seed"]==0
    assert gate["alternative"]=="greater"
    assert gate["require_positive_gain_over_null"] is True

    val=payload["validation_gate"]
    assert val["w7_max_authorized_count"]==0
    assert val["informative_control_min_authorized_count_each"]==95
    assert val["informative_control_denominator_each"]==100
    assert val["strict_conjunction"] is True

    conf=payload["confirmation_gate"]
    assert conf["w7_max_authorized_count"]==0
    assert conf["informative_control_min_authorized_count_each"]==48
    assert conf["informative_control_denominator_each"]==50
    assert conf["no_rule_change"] is True

    assert payload["fresh_empirical_open"] is False
