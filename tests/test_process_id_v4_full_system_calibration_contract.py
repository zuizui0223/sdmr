import json
from pathlib import Path

from sdmr.process_id.known_truth.full_system_calibration import (
    INFORMATIVE_CONTROL_WORLDS,
)


CONTRACT = Path("configs/sdmr_v4_full_system_gate_calibration_v1.json")


def test_v4_full_system_calibration_contract_is_frozen_before_outcomes():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["status"]=="development_only_frozen_before_outcomes"
    assert payload["predecessor_terminal_failure"]=="KT-E"
    assert payload["product_a_boundary"]=="closed_not_reopened"

    assert payload["seeds"]["calibration"]==list(range(41001,41101))
    assert payload["seeds"]["confirmation"]==list(range(42001,42051))
    assert payload["seeds"]["reserved_future_prospective"]==list(range(43001,43021))
    assert payload["seed_use"]=={
        "calibration_open":False,
        "confirmation_open":False,
        "reserved_future_prospective_open":False,
    }

    assert tuple(payload["informative_controls"])==INFORMATIVE_CONTROL_WORLDS
    assert payload["report_only_world"]=="observation_confounded"
    assert payload["null_world"]=="omitted_driver"

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

    assert payload["candidate_multipliers"]==[1.0,1.645,1.96,2.326,2.576,3.09]
    assert payload["calibration_selection"]["max_w7_false_authorization_rate"]==0.01
    assert payload["calibration_selection"]["min_each_informative_control_authorization_rate"]==0.95
    assert payload["calibration_selection"]["selection_rule"]=="smallest_candidate_multiplier_satisfying_all_constraints"

    confirmation=payload["confirmation_gate"]
    assert confirmation["w7_max_authorized_count"]==0
    assert confirmation["informative_control_min_authorized_count_each"]==48
    assert confirmation["informative_control_denominator_each"]==50
    assert confirmation["strict_conjunction"] is True
    assert confirmation["no_reselection"] is True

    assert payload["fresh_empirical_open"] is False
