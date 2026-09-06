import numpy as np
import pandas as pd

from sdmr.model import ModelSpec
from sdmr.process_challenge_learner import (
    CONTRIBUTORY,
    REPLACEABLE,
    REQUIRED,
    fit_process_challenge_learner,
)


def _strong_and_redundant_tables(seed: int = 7):
    rng = np.random.default_rng(seed)
    n = 240
    groups = np.tile(np.arange(8), n // 8)
    presence = pd.DataFrame(
        {
            "x_primary": rng.normal(1.6, 0.75, n),
            "x_backup": rng.normal(0.75, 0.95, n),
            "x_noise": rng.normal(0.0, 1.0, n),
        }
    )
    background = pd.DataFrame(
        {
            "x_primary": rng.normal(0.0, 1.0, n),
            "x_backup": rng.normal(0.0, 1.0, n),
            "x_noise": rng.normal(0.0, 1.0, n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "x_primary", "process": "primary", "role": "direct"},
            {"predictor": "x_backup", "process": "backup", "role": "direct"},
            {"predictor": "x_noise", "process": "noise", "role": "direct"},
        ]
    )
    return presence, background, groups.copy(), groups.copy(), registry


def _required_tables(seed: int = 19):
    rng = np.random.default_rng(seed)
    n = 192
    groups = np.tile(np.arange(8), n // 8)
    presence = pd.DataFrame(
        {
            "x_thermal": rng.normal(1.7, 0.40, n),
            "x_water": rng.normal(0.0, 1.0, n),
            "recording_bias": rng.normal(2.0, 0.45, n),
        }
    )
    background = pd.DataFrame(
        {
            "x_thermal": rng.normal(-1.7, 0.40, n),
            "x_water": rng.normal(0.0, 1.0, n),
            "recording_bias": rng.normal(0.0, 1.0, n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "x_thermal", "process": "thermal", "role": "direct"},
            {"predictor": "x_water", "process": "water", "role": "direct"},
        ]
    )
    return presence, background, groups.copy(), groups.copy(), registry


def test_process_challenge_separates_contribution_from_replaceability() -> None:
    p, b, pg, bg, registry = _strong_and_redundant_tables()
    fit = fit_process_challenge_learner(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("x_primary", "x_backup", "x_noise"),
        process_registry=registry,
        process_universe=("primary", "backup", "noise"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.01,
        relative_noninferiority_margin=0.02,
    )
    status = fit.process_summary.set_index("process")["status"].to_dict()
    assert status["primary"] == CONTRIBUTORY
    assert status["noise"] == REPLACEABLE
    assert bool(fit.process_summary.set_index("process").loc["primary", "process_detected"])
    assert not bool(fit.process_summary.set_index("process").loc["noise", "process_detected"])
    assert {
        "mean_prediction_delta_vs_baseline",
        "prediction_delta_lower",
        "mean_ecological_delta_vs_baseline",
        "ecological_delta_lower",
        "relative_noninferior",
    }.issubset(fit.route_summary.columns)


def test_process_challenge_preserves_required_state_and_observation_separation() -> None:
    p, b, pg, bg, registry = _required_tables()
    fit = fit_process_challenge_learner(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("x_thermal", "x_water"),
        observation_predictors=("recording_bias",),
        process_registry=registry,
        process_universe=("thermal", "water"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.03,
        relative_noninferiority_margin=0.02,
    )
    status = fit.process_summary.set_index("process")["status"].to_dict()
    assert status["thermal"] == REQUIRED
    assert status["water"] == REPLACEABLE
    assert "recording_bias" not in set(fit.process_summary["process"])


def test_prediction_uses_single_canonical_winner_not_adequate_model_average() -> None:
    p, b, pg, bg, registry = _strong_and_redundant_tables(seed=11)
    fit = fit_process_challenge_learner(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("x_primary", "x_backup", "x_noise"),
        process_registry=registry,
        process_universe=("primary", "backup", "noise"),
        model_specs=(
            ModelSpec(C=0.1, degree=1, random_state=0),
            ModelSpec(C=1.0, degree=1, random_state=0),
            ModelSpec(C=10.0, degree=1, random_state=0),
        ),
        n_splits=4,
        relative_noninferiority_margin=0.02,
    )
    admitted = dict(fit.base_fit.fitted_models)
    assert fit.prediction_model_label in admitted
    scores = fit.predict_relative_suitability(p.iloc[:12])
    assert scores.shape == (12,)
    assert np.isfinite(scores).all()
    assert fit.selection_receipt != fit.base_fit.selection_receipt
