import numpy as np
import pandas as pd

from sdmr.context_geometry_v17 import context_geometry_features


def _frames(seed=1):
    rng = np.random.default_rng(seed)
    n = 240
    q1 = rng.normal(size=n)
    q2 = rng.normal(size=n)
    p1 = 0.8 * q1 - 0.4 * q2 + rng.normal(scale=0.2, size=n)
    p2 = -0.2 * q1 + 0.7 * q2 + rng.normal(scale=0.2, size=n)
    ref = pd.DataFrame({"p1": p1, "p2": p2, "q1": q1, "q2": q2})
    m = 60
    tq1 = rng.normal(loc=1.2, size=m)
    tq2 = rng.normal(loc=-0.8, size=m)
    tp1 = 0.8 * tq1 - 0.4 * tq2 + rng.normal(loc=0.5, scale=0.35, size=m)
    tp2 = -0.2 * tq1 + 0.7 * tq2 + rng.normal(loc=-0.4, scale=0.35, size=m)
    tgt = pd.DataFrame({"p1": tp1, "p2": tp2, "q1": tq1, "q2": tq2})
    return ref, tgt


def test_context_geometry_is_background_only_and_finite():
    ref, tgt = _frames()
    out = context_geometry_features(
        ref,
        tgt,
        process_predictors=("p1", "p2"),
        conditioning_predictors=("q1", "q2"),
        degree=2,
        ridge_alpha=1e-3,
    )
    assert out.n_reference == len(ref)
    assert out.n_target == len(tgt)
    vals = [
        out.conditional_residual_shift,
        out.conditional_residual_scale_ratio,
        out.conditional_target_r2,
        out.process_support_shift,
        out.conditioning_support_shift,
    ]
    assert all(np.isfinite(v) for v in vals)
    assert out.conditional_residual_shift > 0
    assert out.process_support_shift > 0
    assert out.conditioning_support_shift > 0


def test_context_geometry_supports_single_process_predictor_without_broadcasting():
    ref, tgt = _frames()
    out = context_geometry_features(
        ref,
        tgt,
        process_predictors=("p1",),
        conditioning_predictors=("q1", "q2"),
        degree=2,
        ridge_alpha=1e-3,
    )
    vals = [
        out.conditional_residual_shift,
        out.conditional_residual_scale_ratio,
        out.conditional_target_r2,
        out.process_support_shift,
        out.conditioning_support_shift,
    ]
    assert all(np.isfinite(v) for v in vals)
    assert out.n_reference == len(ref)
    assert out.n_target == len(tgt)


def test_context_geometry_fails_closed_for_small_target():
    ref, tgt = _frames()
    out = context_geometry_features(
        ref,
        tgt.iloc[:2],
        process_predictors=("p1", "p2"),
        conditioning_predictors=("q1", "q2"),
        minimum_target_rows=5,
    )
    assert np.isnan(out.conditional_residual_shift)
    assert out.n_target == 2


def test_process_and_conditioning_sets_must_be_disjoint():
    ref, tgt = _frames()
    try:
        context_geometry_features(
            ref,
            tgt,
            process_predictors=("p1", "q1"),
            conditioning_predictors=("q1", "q2"),
        )
    except ValueError:
        return
    raise AssertionError("expected overlap to fail closed")
