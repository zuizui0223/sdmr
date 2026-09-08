import numpy as np
import pandas as pd

from sdmr.conditional_residual_randomization_process_challenge import (
    fit_conditional_residual_randomization_process_challenge,
)
from sdmr.model import ModelSpec


def _tables(seed=177, n=240):
    rng = np.random.default_rng(seed)
    groups = np.tile(np.arange(8), n // 8)
    bw = rng.normal(size=n)
    bs = rng.normal(size=n)
    bt = 0.8 * bw + 0.3 * bs + rng.normal(scale=0.35, size=n)
    pw = rng.normal(0.7, 0.9, size=n)
    ps = rng.normal(size=n)
    pt = 0.8 * pw + 0.3 * ps + 0.9 + rng.normal(scale=0.35, size=n)
    background = pd.DataFrame({"temperature": bt, "water": bw, "soil": bs})
    presence = pd.DataFrame({"temperature": pt, "water": pw, "soil": ps})
    registry = pd.DataFrame([
        {"predictor": "temperature", "process": "temperature", "role": "direct"},
        {"predictor": "water", "process": "water", "role": "direct"},
        {"predictor": "soil", "process": "soil", "role": "direct"},
    ])
    return presence, background, groups.copy(), groups.copy(), registry


def test_v9_exports_randomized_routes_and_preserves_non_target_predictors():
    p, b, pg, bg, registry = _tables()
    fit = fit_conditional_residual_randomization_process_challenge(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("temperature", "water", "soil"),
        process_registry=registry,
        process_universe=("temperature", "water", "soil"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        randomization_seed=90401,
    )
    assert len(fit.randomized_route_summary) == 3
    assert len(fit.randomized_fold_evidence) == 12
    assert fit.intervention_audit["complete"].astype(bool).all()
    assert fit.intervention_audit["non_target_predictors_unchanged"].astype(bool).all()
    assert (fit.intervention_audit["residual_bank_rows"] > 0).all()
    assert set(fit.process_summary["process"]) == {"temperature", "water", "soil"}
    assert fit.selection_receipt != fit.v5_fit.selection_receipt


def test_v9_prediction_model_stays_inherited_from_v5():
    p, b, pg, bg, registry = _tables(seed=192)
    fit = fit_conditional_residual_randomization_process_challenge(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("temperature", "water", "soil"),
        process_registry=registry,
        process_universe=("temperature", "water", "soil"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
    )
    assert np.allclose(
        fit.predict_relative_suitability(p.iloc[:20]),
        fit.v5_fit.predict_relative_suitability(p.iloc[:20]),
        equal_nan=True,
    )
