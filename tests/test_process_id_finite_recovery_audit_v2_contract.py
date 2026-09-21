import json
from pathlib import Path


V1 = Path("configs/sdmr_v3_finite_recovery_audit_v1.json")
V2 = Path("configs/sdmr_v3_finite_recovery_audit_v2.json")


def test_finite_recovery_v2_changes_only_hgb_weight_scale_contract():
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    v2 = json.loads(V2.read_text(encoding="utf-8"))

    assert v2["program"] == "sdmr-v3-finite-recovery-audit-v2"
    assert v2["development_predecessor"] == v1["program"]
    assert v2["change_reason"] == "hgb_balanced_weights_preserve_empirical_loss_scale"
    assert v2["hgb_weight_scale"] == "empirical_n"

    for key in (
        "status",
        "product_a_boundary",
        "seeds_reused_only_as_burned_development_evidence",
        "seeds",
        "worlds",
        "omitted_world_reason",
        "n_cells",
        "n_occurrences",
        "n_background",
        "n_splits",
        "baseline_learners",
        "sample_multipliers",
        "sampling_replicates",
        "margin",
        "adequacy_floor",
        "sem_multiplier",
        "logistic_C",
        "odo_target",
        "prospective_status",
        "prospective_validation_seeds",
        "fresh_empirical_open",
    ):
        assert v2[key] == v1[key]
