import numpy as np
import pandas as pd

from sdmr.process_proxy_audit import audit_process_proxy_reconstructability


def test_proxy_audit_finds_reconstructive_predictor_without_mutating_registry() -> None:
    rng = np.random.default_rng(123)
    n = 360
    thermal = rng.normal(size=n)
    frame = pd.DataFrame(
        {
            "thermal": thermal,
            "thermal_proxy": 0.92 * thermal + rng.normal(0, 0.12, n),
            "water": rng.normal(size=n),
            "noise": rng.normal(size=n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "thermal", "process": "thermal", "role": "direct"},
            {"predictor": "thermal_proxy", "process": "other", "role": "direct"},
            {"predictor": "water", "process": "water", "role": "direct"},
            {"predictor": "noise", "process": "noise", "role": "direct"},
        ]
    )
    before = registry.copy(deep=True)
    audit = audit_process_proxy_reconstructability(
        frame,
        registry,
        process_universe=("thermal", "other", "water", "noise"),
        predictor_universe=("thermal", "thermal_proxy", "water", "noise"),
        n_splits=5,
        degree=2,
    )
    thermal_candidates = audit.candidate_summary.loc[
        audit.candidate_summary["target_process"].eq("thermal")
    ].set_index("candidate_predictor")
    assert thermal_candidates.loc["thermal_proxy", "univariate_cv_r2"] > 0.85
    assert thermal_candidates.loc["thermal_proxy", "abs_spearman"] > 0.9
    assert thermal_candidates.loc["noise", "univariate_cv_r2"] < 0.15
    assert not audit.candidate_summary["auto_frozen"].astype(bool).any()
    assert audit.candidate_summary["requires_human_review"].astype(bool).all()
    pd.testing.assert_frame_equal(registry, before)


def test_proxy_audit_reports_joint_residual_reconstructability() -> None:
    rng = np.random.default_rng(77)
    n = 400
    a = rng.normal(size=n)
    b = rng.normal(size=n)
    target = 0.8 * a - 0.7 * b + rng.normal(0, 0.12, n)
    frame = pd.DataFrame({"target": target, "a": a, "b": b, "noise": rng.normal(size=n)})
    registry = pd.DataFrame(
        [
            {"predictor": "target", "process": "target_process", "role": "direct"},
            {"predictor": "a", "process": "a_process", "role": "direct"},
            {"predictor": "b", "process": "b_process", "role": "direct"},
            {"predictor": "noise", "process": "noise", "role": "direct"},
        ]
    )
    audit = audit_process_proxy_reconstructability(
        frame,
        registry,
        process_universe=("target_process", "a_process", "b_process", "noise"),
        predictor_universe=("target", "a", "b", "noise"),
        n_splits=5,
        degree=1,
    )
    row = audit.process_summary.set_index("process").loc["target_process"]
    assert row["mean_anchor_reconstruction_cv_r2"] > 0.9
    assert row["outcome_used"] is False or not bool(row["outcome_used"])
    assert row["registry_modified"] is False or not bool(row["registry_modified"])


def test_proxy_audit_can_use_spatial_or_other_predeclared_groups() -> None:
    rng = np.random.default_rng(5)
    n = 240
    groups = np.repeat(np.arange(8), n // 8)
    thermal = rng.normal(size=n)
    frame = pd.DataFrame(
        {
            "thermal": thermal,
            "proxy": thermal + rng.normal(0, 0.2, n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "thermal", "process": "thermal", "role": "direct"},
            {"predictor": "proxy", "process": "other", "role": "direct"},
        ]
    )
    audit = audit_process_proxy_reconstructability(
        frame,
        registry,
        process_universe=("thermal", "other"),
        predictor_universe=("thermal", "proxy"),
        groups=groups,
        n_splits=4,
        degree=1,
    )
    assert audit.n_splits == 4
    assert audit.process_summary.set_index("process").loc[
        "thermal", "max_anchor_reconstruction_cv_r2"
    ] > 0.8
