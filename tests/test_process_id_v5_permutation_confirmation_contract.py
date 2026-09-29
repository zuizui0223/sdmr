import json
from pathlib import Path

CONTRACT=Path("configs/sdmr_v5_permutation_gate_confirmation_v1.json")

def test_v5_confirmation_contract_is_frozen_before_validation_outcome():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"]=="frozen_pending_validation_prerequisite"
    assert payload["validation_prerequisite"]["workflow_run"]==36070724122
    assert payload["validation_prerequisite"]["required_terminal_decision"]=="passed"
    assert payload["validation_prerequisite"]["outcome_not_opened_when_contract_frozen"] is True
    assert payload["seeds"]==list(range(52001,52051))
    assert payload["reserved_future_prospective"]==list(range(53001,53021))

    gate=payload["permutation_gate"]
    assert gate["n_permutations"]==999
    assert gate["alpha"]==0.001
    assert gate["permutation_seed"]==0
    assert gate["require_positive_gain_over_null"] is True

    finite=payload["finite_architecture"]
    assert finite["multiplier"]==8
    assert finite["n_occurrences"]==1440
    assert finite["n_background"]==4800
    assert finite["hgb_profile"]=="shallow3"
    assert finite["split_mode"]=="random_cell"

    conf=payload["confirmation_gate"]
    assert conf["w7_max_authorized_count"]==0
    assert conf["informative_control_min_authorized_count_each"]==48
    assert conf["informative_control_denominator_each"]==50
    assert conf["strict_conjunction"] is True
    assert conf["no_rule_change"] is True

    assert payload["reserved_future_prospective_open"] is False
    assert payload["fresh_empirical_open"] is False
    assert payload["activation_status"]=="blocked"
