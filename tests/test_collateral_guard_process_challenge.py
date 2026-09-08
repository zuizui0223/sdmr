import numpy as np
import pandas as pd

from sdmr.collateral_guard_process_challenge import fit_collateral_guard_process_challenge
from sdmr.interval_evidence_process_challenge import (
    INCOMPLETE_EVIDENCE,
    INDETERMINATE_EVIDENCE,
    INFERIOR_EVIDENCE,
    NONINFERIOR_EVIDENCE,
)
from sdmr.model import ModelSpec


def _tables(seed=71):
    rng = np.random.default_rng(seed)
    n = 240
    groups = np.tile(np.arange(8), n // 8)
    bt = rng.normal(size=n)
    bw = rng.normal(size=n)
    bs = 0.8 * bt - 0.45 * bw + rng.normal(scale=0.35, size=n)
    pt = rng.normal(1.0, 0.9, size=n)
    pw = rng.normal(0.8, 0.9, size=n)
    ps = 0.8 * pt - 0.45 * pw + rng.normal(scale=0.35, size=n)
    background = pd.DataFrame(
        {
            "temperature": bt,
            "water": bw,
            "seasonality": bs,
            "noise": rng.normal(size=n),
        }
    )
    presence = pd.DataFrame(
        {
            "temperature": pt,
            "water": pw,
            "seasonality": ps,
            "noise": rng.normal(size=n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "temperature", "process": "temperature", "role": "direct"},
            {"predictor": "water", "process": "water", "role": "direct"},
            {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
            {"predictor": "noise", "process": "noise", "role": "direct"},
        ]
    )
    return presence, background, groups.copy(), groups.copy(), registry


def test_v7_exports_specific_routes_and_truth_blind_collateral_audit():
    p, b, pg, bg, registry = _tables()
    fit = fit_collateral_guard_process_challenge(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("temperature", "water", "seasonality", "noise"),
        process_registry=registry,
        process_universe=("temperature", "water", "seasonality", "noise"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.01,
        relative_noninferiority_margin=0.02,
        density_noninferiority_margin=0.01,
        purge_degree=2,
        purge_ridge_alpha=1.0,
        collateral_sem_multiplier=1.0,
    )
    assert len(fit.process_specific_route_summary) == 4
    assert len(fit.process_specific_fold_evidence) == 16
    assert set(fit.process_summary["process"]) == {
        "temperature",
        "water",
        "seasonality",
        "noise",
    }
    assert {
        "raw_relative_evidence_state",
        "relative_evidence_state",
        "collateral_guard_pass",
        "competing_process_predictors",
    }.issubset(fit.process_specific_route_summary.columns)
    assert set(fit.process_specific_route_summary["relative_evidence_state"]).issubset(
        {
            NONINFERIOR_EVIDENCE,
            INFERIOR_EVIDENCE,
            INDETERMINATE_EVIDENCE,
            INCOMPLETE_EVIDENCE,
        }
    )
    assert {
        "process_specific_unguarded_status",
        "v6_status",
        "collateral_guard_pass",
        "status_changed_from_v6",
    }.issubset(fit.process_summary.columns)
    assert set(fit.specificity_audit["audit_role"]) == {
        "target_erasure",
        "collateral_preservation",
    }
    assert not {"presence", "generating_truth", "expected_true_process"}.intersection(
        fit.specificity_audit.columns
    )


def test_v7_prediction_model_is_inherited_from_v6_not_retuned_by_guard():
    p, b, pg, bg, registry = _tables(seed=81)
    fit = fit_collateral_guard_process_challenge(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("temperature", "water", "seasonality", "noise"),
        process_registry=registry,
        process_universe=("temperature", "water", "seasonality", "noise"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
    )
    a = fit.predict_relative_suitability(p.iloc[:20])
    b_scores = fit.v6_fit.predict_relative_suitability(p.iloc[:20])
    assert np.allclose(a, b_scores, equal_nan=True)
