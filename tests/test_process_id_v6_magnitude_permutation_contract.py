import json
from pathlib import Path


CONTRACT=Path("configs/sdmr_v6_magnitude_permutation_validation_v1.json")


def test_v6_validation_contract_is_frozen_before_outcomes():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["status"]=="development_only_frozen_before_outcomes"
    assert payload["predecessor_terminal_failure"]=="INT-E_W7_false_authorization_1_of_20"

    assert payload["seeds"]["validation"]==list(range(71001,71101))
    assert payload["seeds"]["confirmation"]==list(range(72001,72051))
    assert payload["seeds"]["integration"]==list(range(73001,73021))
    assert payload["seeds"]["reserved_future_prospective"]==list(range(74001,74021))

    gate=payload["authorization_gate"]
    assert gate["n_permutations"]==999
    assert gate["alpha"]==0.001
    assert gate["permutation_seed"]==0
    assert gate["minimum_gain_over_null"]==0.01

    finite=payload["finite_architecture"]
    assert finite["multiplier"]==8
    assert finite["n_occurrences"]==1440
    assert finite["n_background"]==4800
    assert finite["hgb_profile"]=="shallow3"
    assert finite["split_mode"]=="random_cell"

    validation=payload["validation_gate"]
    assert validation["w7_max_authorized_count"]==0
    assert validation["informative_control_min_authorized_count_each"]==95
    assert validation["informative_control_denominator_each"]==100

    assert payload["fresh_empirical_open"] is False
