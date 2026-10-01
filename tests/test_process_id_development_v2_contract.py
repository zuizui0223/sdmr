import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


V1 = Path("configs/sdmr_v3_process_id_development_v1.json")
V2 = Path("configs/sdmr_v3_process_id_development_v2.json")


def test_development_v2_preserves_v1_science_profile_except_equal_prior_fit_fix():
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    v2 = json.loads(V2.read_text(encoding="utf-8"))

    assert v2["status"] == "development_only"
    assert v2["product_a_boundary"] == "closed_not_reopened"
    assert v2["seeds"] == v1["seeds"] == list(range(23001, 23009))
    assert tuple(v2["worlds"]) == tuple(v1["worlds"]) == KNOWN_TRUTH_WORLDS
    for key in ("n_cells", "n_occurrences", "n_background", "n_splits", "oracle"):
        assert v2[key] == v1[key]

    assert v2["occurrence"]["margin"] == v1["occurrence"]["margin"]
    assert v2["occurrence"]["sem_multiplier"] == v1["occurrence"]["sem_multiplier"]
    assert v2["occurrence"]["adequacy_floor"] == v1["occurrence"]["adequacy_floor"]
    assert v2["occurrence"]["logistic_C"] == v1["occurrence"]["logistic_C"]
    assert v2["occurrence"]["fit_class_weight"] == "balanced"

    assert v2["development_predecessor"] == "sdmr-v3-process-identification-development-v1"
    assert v2["change_reason"] == "align_logistic_fit_prior_with_equal_prior_balanced_log_score"
    assert v2["prospective_status"] == "not_frozen"
    assert v2["fresh_empirical_open"] is False


def test_development_v2_does_not_create_new_seed_evidence():
    v2 = json.loads(V2.read_text(encoding="utf-8"))
    assert v2["seeds_reused_only_as_burned_development_evidence"] is True
    assert v2["prospective_validation_seeds"] == []
