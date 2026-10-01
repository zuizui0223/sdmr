import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_prospective_kt_v1.json")


def test_prospective_kt_v1_freezes_unused_seed_denominator_and_architecture():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["status"] == "frozen_pending_development_prerequisite"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["development_prerequisite"]["workflow_run"] == 35991170328
    assert payload["development_prerequisite"]["outcome_not_opened_when_contract_frozen"] is True

    assert payload["seeds"]["values"] == list(range(33001, 33021))
    assert payload["seeds"]["count"] == 20
    assert payload["seeds"]["replacement_policy"] == "forbidden_after_any_prospective_outcome_access"

    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["expected_odo_counts_total"] == {
        "positive": 80,
        "replaceable": 700,
        "unresolved": 60,
        "unavailable": 120,
        "structural_refusal": 60,
    }

    stage_p = payload["stage_p"]
    assert stage_p["learner"] == "hgb"
    assert stage_p["hgb_profile"] == "shallow3"
    assert stage_p["split_mode"] == "random_cell"
    assert stage_p["multiplier"] == 8
    assert stage_p["n_occurrences"] == 1440
    assert stage_p["n_background"] == 4800
    assert stage_p["margin"] == 0.01
    assert stage_p["adequacy_floor"] == -0.75
    assert stage_p["sem_multiplier"] == 1.0
    assert stage_p["full_system_information_gate"]["required"] is True
    assert stage_p["full_system_information_gate"]["information_boundary"] == 0.0

    assert payload["stage_t"]["split_mode"] == "spatial"
    assert payload["stage_t"]["retroactive_stage_p_state_change"] is False


def test_prospective_kt_v1_freezes_strict_gate_vector():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
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
    assert gates["KT-F"]["max_spatial_structural_refusal_violation_rate"] == 0.0


def test_prospective_kt_v1_is_still_unopened_and_blocked():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False
    assert payload["activation_status"] == "blocked"
