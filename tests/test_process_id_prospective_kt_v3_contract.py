import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


CONTRACT = Path("configs/sdmr_v3_prospective_kt_v3.json")
EXECUTION = Path("configs/sdmr_v3_prospective_kt_v3_execution.json")


def test_prospective_kt_v3_inherits_v2_science_and_rebinds_only_prerequisite():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["program"] == "sdmr-v3-prospective-known-truth-v3"
    assert payload["status"] == "frozen_pending_development_prerequisite"
    assert payload["predecessor"]["program"] == "sdmr-v3-prospective-known-truth-v2"
    assert payload["predecessor"]["disposition"] == "aborted_unopened"
    assert payload["development_prerequisite"]["workflow_run"] == 35997608669
    assert payload["development_prerequisite"]["source_scientific_shard_run"] == 35992320576
    assert payload["development_prerequisite"]["source_scientific_shards_recomputed"] is False
    assert payload["development_prerequisite"]["scientific_settings_inherited_unchanged_from_v2"] is True

    assert payload["seeds"]["values"] == list(range(33001,33021))
    assert tuple(payload["worlds"]) == KNOWN_TRUTH_WORLDS
    assert payload["expected_odo_counts_total"] == {
        "positive": 80,
        "replaceable": 700,
        "unresolved": 60,
        "unavailable": 120,
        "structural_refusal": 60,
    }

    stage_p = payload["stage_p"]
    assert stage_p["hgb_profile"] == "shallow3"
    assert stage_p["split_mode"] == "random_cell"
    assert stage_p["multiplier"] == 8
    assert stage_p["n_occurrences"] == 1440
    assert stage_p["n_background"] == 4800
    assert stage_p["margin"] == 0.01
    assert stage_p["adequacy_floor"] == -0.75
    assert stage_p["sem_multiplier"] == 1.0
    assert stage_p["full_system_information_gate"]["required"] is True

    gates = payload["gate_vector"]
    assert gates["KT-B"]["minimum"] == 0.80
    assert gates["KT-C"]["maximum"] == 0.01
    assert gates["KT-D"]["max_overresolution_rate_among_odo_unresolved"] == 0.0
    assert gates["KT-D"]["max_structural_refusal_violation_rate"] == 0.0
    assert gates["KT-E"]["max_sharp_rate_among_odo_unavailable"] == 0.0
    assert gates["KT-E"]["max_favorable_positive_rate_among_odo_unavailable"] == 0.0
    assert gates["KT-E"]["min_non_w7_full_system_information_adequacy"] == 0.95
    assert gates["KT-E"]["max_w7_full_system_information_adequacy"] == 0.0

    assert payload["activation_status"] == "blocked"
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False


def test_prospective_kt_v3_execution_profile_is_frozen_and_blocked():
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))

    assert payload["program"] == "sdmr-v3-prospective-known-truth-v3-execution-profile"
    assert payload["status"] == "frozen_blocked"
    assert payload["scientific_contract_path"] == "configs/sdmr_v3_prospective_kt_v3.json"
    assert payload["scientific_contract_blob_sha"] == "73bb1ac9e5b1357d4c278712176e65286bd3bb6b"

    assert payload["sampling"]["multiplier"] == 8
    assert payload["sampling"]["sampling_replicate"] == 0
    assert payload["sampling"]["with_replacement"] is True
    assert payload["sharding"]["expected_shards"] == 32
    assert [seed for block in payload["sharding"]["seed_blocks"] for seed in block] == list(range(33001,33021))

    assert payload["stage_p"]["split_mode"] == "random_cell"
    assert payload["stage_p"]["require_full_system_information"] is True
    assert payload["stage_t"]["split_mode"] == "spatial"
    assert payload["stage_t"]["require_full_system_information"] is False

    assert payload["prerequisite"]["workflow_run"] == 35997608669
    assert payload["prerequisite"]["source_scientific_shard_run"] == 35992320576
    assert payload["prerequisite"]["source_scientific_shards_recomputed"] is False
    assert payload["activation_status"] == "blocked"
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False
