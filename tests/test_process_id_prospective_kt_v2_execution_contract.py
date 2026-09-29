import json
from pathlib import Path


PROFILE = Path("configs/sdmr_v3_prospective_kt_v2_execution.json")


def test_prospective_execution_profile_is_frozen_but_blocked():
    payload = json.loads(PROFILE.read_text(encoding="utf-8"))

    assert payload["status"] == "frozen_blocked"
    assert payload["scientific_contract_path"] == "configs/sdmr_v3_prospective_kt_v2.json"
    assert payload["scientific_contract_blob_sha"] == "496ec8b208cb44150fff4a9384c49109f87c7b26"
    assert payload["activation_status"] == "blocked"
    assert payload["prospective_outcomes_opened"] is False
    assert payload["fresh_empirical_open"] is False

    sampling = payload["sampling"]
    assert sampling["multiplier"] == 8
    assert sampling["sampling_replicate"] == 0
    assert sampling["with_replacement"] is True
    assert sampling["world_index_order"] == [
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "observation_confounded",
        "omitted_driver",
        "geographic_shift",
    ]

    blocks = payload["sharding"]["seed_blocks"]
    assert len(blocks) == 4
    assert [seed for block in blocks for seed in block] == list(range(33001,33021))
    assert payload["sharding"]["expected_shards"] == 32

    assert payload["stage_p"]["split_mode"] == "random_cell"
    assert payload["stage_p"]["require_full_system_information"] is True
    assert payload["stage_t"]["split_mode"] == "spatial"
    assert payload["stage_t"]["require_full_system_information"] is False
    assert payload["stage_t"]["uses_same_sample_as_stage_p"] is True

    assert payload["prerequisite"]["workflow_run"] == 35992320576
    assert payload["prerequisite"]["terminal_review_receipt_required"] is True
