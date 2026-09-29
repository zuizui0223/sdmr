import json
from pathlib import Path

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


V2 = Path("configs/sdmr_v3_process_id_development_v2.json")
V3 = Path("configs/sdmr_v3_process_id_development_v3.json")


def test_development_v3_changes_only_declared_logic_and_learner_capacity():
    v2 = json.loads(V2.read_text(encoding="utf-8"))
    v3 = json.loads(V3.read_text(encoding="utf-8"))

    assert v3["status"] == "development_only"
    assert v3["product_a_boundary"] == "closed_not_reopened"
    assert v3["development_predecessor"] == "sdmr-v3-process-identification-development-v2"
    assert v3["seeds"] == v2["seeds"] == list(range(23001, 23009))
    assert tuple(v3["worlds"]) == tuple(v2["worlds"]) == KNOWN_TRUTH_WORLDS

    for key in ("n_cells", "n_occurrences", "n_background", "n_splits", "oracle"):
        assert v3[key] == v2[key]

    for key in ("margin", "sem_multiplier", "adequacy_floor", "logistic_C", "fit_class_weight"):
        assert v3["occurrence"][key] == v2["occurrence"][key]

    assert v3["occurrence"]["learner"] == "quadratic"
    assert v3["shared_closure_abstention"] == "all_sharp_states"
    assert v3["prospective_status"] == "not_frozen"
    assert v3["prospective_validation_seeds"] == []
    assert v3["fresh_empirical_open"] is False
    assert v3["seeds_reused_only_as_burned_development_evidence"] is True
