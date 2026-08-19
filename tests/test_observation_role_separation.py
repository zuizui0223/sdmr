import numpy as np
import pandas as pd

from sdmr.model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from sdmr.niche_recovery_cv import RecoveryCandidate


def _biased_training(seed=3):
    rng = np.random.default_rng(seed)
    n_b = 800
    n_p = 260
    background = pd.DataFrame(
        {
            "temperature": rng.normal(0, 1, n_b),
            "recording_bias": rng.normal(0, 1, n_b),
        }
    )
    # Occurrences prefer a biological temperature optimum and are also much more
    # likely to be recorded at high recording_bias.
    pool = pd.DataFrame(
        {
            "temperature": rng.normal(0, 1, 6000),
            "recording_bias": rng.normal(0, 1, 6000),
        }
    )
    t = pool["temperature"].to_numpy()
    r = pool["recording_bias"].to_numpy()
    weights = np.exp(-0.5 * ((t - 0.45) / 0.55) ** 2 + 1.8 * r)
    weights /= weights.sum()
    occurrences = pool.iloc[rng.choice(len(pool), size=n_p, replace=False, p=weights)].reset_index(drop=True)
    return occurrences, background


def test_ecological_score_is_invariant_to_evaluation_recording_bias_values():
    occurrences, background = _biased_training()
    predictors = ("temperature", "recording_bias")
    model = fit_relative_suitability_model(
        occurrences,
        background,
        predictors,
        model_spec=ModelSpec(C=1.0, degree=2, penalty="l2"),
    )
    temperature = np.linspace(-1.5, 1.5, 80)
    low_bias = pd.DataFrame({"temperature": temperature, "recording_bias": -2.5})
    high_bias = pd.DataFrame({"temperature": temperature, "recording_bias": 2.5})

    full_low = score_relative_suitability(model, low_bias, predictors)
    full_high = score_relative_suitability(model, high_bias, predictors)
    assert np.mean(np.abs(full_low - full_high)) > 0.05

    eco_low = score_ecological_suitability(
        model,
        low_bias,
        predictors,
        observation_predictors=("recording_bias",),
        observation_reference=background,
    )
    eco_high = score_ecological_suitability(
        model,
        high_bias,
        predictors,
        observation_predictors=("recording_bias",),
        observation_reference=background,
    )
    assert np.allclose(eco_low, eco_high, rtol=0, atol=1e-12)
    assert np.ptp(eco_low) > 0.05


def test_observer_only_model_has_constant_ecological_surface_after_marginalization():
    occurrences, background = _biased_training(8)
    predictors = ("recording_bias",)
    model = fit_relative_suitability_model(occurrences, background, predictors)
    frame = pd.DataFrame({"temperature": np.linspace(-2, 2, 50)})
    ecological = score_ecological_suitability(
        model,
        frame,
        predictors,
        observation_predictors=("recording_bias",),
        observation_reference=background,
    )
    assert np.all(np.isfinite(ecological))
    assert np.ptp(ecological) < 1e-12


def test_recovery_candidate_rejects_undeclared_model_predictor_role():
    try:
        RecoveryCandidate(
            "bad",
            ("temperature",),
            ModelSpec(),
            observation_predictors=("recording_bias",),
        )
    except ValueError as exc:
        assert "not model predictors" in str(exc)
    else:
        raise AssertionError("RecoveryCandidate accepted an observation role absent from model predictors")
