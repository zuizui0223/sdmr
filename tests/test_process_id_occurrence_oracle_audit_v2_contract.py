import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


V1 = Path("configs/sdmr_v3_occurrence_distribution_oracle_audit_v1.json")
V2 = Path("configs/sdmr_v3_occurrence_distribution_oracle_audit_v2.json")


def test_occurrence_oracle_audit_v2_changes_only_crossfit_mode():
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    v2 = json.loads(V2.read_text(encoding="utf-8"))

    assert v2["status"] == "development_only"
    assert v2["product_a_boundary"] == "closed_not_reopened"
    assert v2["development_predecessor"] == v1["program"]
    assert v2["seeds"] == v1["seeds"] == list(range(23001, 23009))
    assert tuple(v2["worlds"]) == tuple(v1["worlds"]) == KNOWN_TRUTH_WORLDS

    for key in ("n_cells", "n_occurrences", "n_background", "n_splits", "truth_oracle", "finite"):
        assert v2[key] == v1[key]

    for key in ("margin", "sem_multiplier", "adequacy_floor", "approximation_tolerance"):
        assert v2["occurrence_oracle"][key] == v1["occurrence_oracle"][key]

    assert v2["occurrence_oracle"]["split_mode"] == "random"
    assert v2["seeds_reused_only_as_burned_development_evidence"] is True
    assert v2["prospective_status"] == "not_frozen"
    assert v2["prospective_validation_seeds"] == []
    assert v2["fresh_empirical_open"] is False
