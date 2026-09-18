import json
from pathlib import Path


CONTRACT = Path("configs/sdmr_v3_process_id_phase1_contract.json")


def test_phase1_contract_keeps_product_a_closed_and_fresh_empirical_unopened():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "development_only"
    assert payload["product_a_boundary"] == "closed_not_reopened"
    assert payload["product_a_terminal_decision"] == "empirical_confirmation_not_supported"
    assert payload["product_a_promotion_decision"] == "not_promoted"
    assert payload["fresh_empirical_open"] is False
    assert payload["prospective_known_truth_status"] == "not_run"


def test_phase1_contract_freezes_world_names_and_burned_development_seeds():
    from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS

    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert tuple(payload["known_truth_worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["burned_development_seeds"] == list(range(13001, 13011))
    assert payload["prospective_validation_seeds"] == []


def test_phase1_contract_points_to_authoritative_design_spec():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["design_spec"] == "docs/superpowers/specs/2026-09-18-sdmr-v3-process-identification-design.md"
    assert "PASS" not in json.dumps(payload)


def test_phase1_public_api_exports_core_components():
    from sdmr.process_id import (
        DEFAULT_PLANT_PROCESSES,
        PROCESS_STATES,
        OccurrenceProcessEvaluation,
        classify_process_state,
        evaluate_occurrence_processes,
        freeze_process_registry,
    )
    from sdmr.process_id.known_truth import (
        KNOWN_TRUTH_WORLDS,
        KnownTruthGateDecision,
        evaluate_known_truth_gate,
        evaluate_oracle_states,
        simulate_process_world,
    )

    assert len(DEFAULT_PLANT_PROCESSES) == 6
    assert len(PROCESS_STATES) == 5
    assert len(KNOWN_TRUTH_WORLDS) == 8
    assert OccurrenceProcessEvaluation.__name__ == "OccurrenceProcessEvaluation"
    assert KnownTruthGateDecision.__name__ == "KnownTruthGateDecision"
    assert all(callable(x) for x in (
        classify_process_state,
        evaluate_occurrence_processes,
        freeze_process_registry,
        evaluate_known_truth_gate,
        evaluate_oracle_states,
        simulate_process_world,
    ))
