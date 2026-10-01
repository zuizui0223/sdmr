import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_prospective_kt_v2.json")


def test_prospective_kt_v2_reuses_unopened_v1_science_exactly():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["program"] == "sdmr-v3-prospective-known-truth-v2"
    assert payload["status"] == "frozen_pending_development_prerequisite"
    assert payload["predecessor"]["disposition"] == "aborted_unopened"
    assert payload["development_prerequisite"]["workflow_run"] == 35992320576
    assert payload["development_prerequisite"]["outcome_not_opened_when_contract_frozen"] is True
    assert payload["development_prerequisite"]["scientific_settings_unchanged_from_v1"] is True

    assert payload["seeds"]["values"] == list(range(33001, 33021))
    assert payload["seeds"]["count"] == 20
    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS

    assert payload["stage_p"]["hgb_profile"] == "shallow3"
    assert payload["stage_p"]["split_mode"] == "random_cell"
    assert payload["stage_p"]["multiplier"] == 8
    assert payload["stage_p"]["n_occurrences"] == 1440
    assert payload["stage_p"]["n_background"] == 4800
    assert payload["stage_p"]["margin"] == 0.01
    assert payload["stage_p"]["adequacy_floor"] == -0.75
    assert payload["stage_p"]["full_system_information_gate"]["information_boundary"] == 0.0

    gates = payload["gate_vector"]
    assert gates["KT-B"]["minimum"] == 0.80
    assert gates["KT-C"]["maximum"] == 0.01
    assert gates["KT-D"]["max_overresolution_rate_among_odo_unresolved"] == 0.0
    assert gates["KT-D"]["max_structural_refusal_violation_rate"] == 0.0
    assert gates["KT-E"]["max_sharp_rate_among_odo_unavailable"] == 0.0
    assert gates["KT-E"]["max_favorable_positive_rate_among_odo_unavailable"] == 0.0
    assert gates["KT-E"]["min_non_w7_full_system_information_adequacy"] == 0.95
    assert gates["KT-E"]["max_w7_full_system_information_adequacy"] == 0.0
    assert gates["KT-F"]["max_stage_p_positive_to_spatial_replaceable_contradiction_rate"] == 0.05

    assert payload["activation_status"] == "blocked"
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False
