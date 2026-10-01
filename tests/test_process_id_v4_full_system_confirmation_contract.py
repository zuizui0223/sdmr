import json
from pathlib import Path

from sdmr.process_id.known_truth.full_system_calibration import (
    INFORMATIVE_CONTROL_WORLDS,
)


CONTRACT=Path("configs/sdmr_v4_full_system_gate_confirmation_v1.json")


def test_v4_confirmation_contract_freezes_selected_multiplier_and_unused_panel():
    payload=json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["program"]=="sdmr-v4-full-system-gate-confirmation-v1"
    assert payload["status"]=="frozen_pending_confirmation"
    assert payload["product_a_boundary"]=="closed_not_reopened"

    source=payload["calibration_source"]
    assert source["workflow_run"]==36014081688
    assert source["artifact_id"]==10814773861
    assert source["artifact_digest"]=="sha256:77024e0489f55fa2e4a229c667372503f95a71a9b20f66a42956b4c23846fbf6"
    assert source["selected_multiplier"]==1.0
    assert source["calibration_passed"] is True

    assert payload["selected_multiplier"]==1.0
    assert payload["reselection_forbidden"] is True
    assert payload["seeds"]==list(range(42001,42051))
    assert payload["reserved_future_prospective"]==list(range(43001,43021))
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

    gate=payload["confirmation_gate"]
    assert gate["w7_max_authorized_count"]==0
    assert gate["informative_control_min_authorized_count_each"]==48
    assert gate["informative_control_denominator_each"]==50
    assert gate["strict_conjunction"] is True
    assert gate["no_reselection"] is True

    assert payload["confirmation_open"] is False
    assert payload["reserved_future_prospective_open"] is False
    assert payload["fresh_empirical_open"] is False
