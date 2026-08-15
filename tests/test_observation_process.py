import numpy as np

from sdmr.known_truth_scenarios import simulate_known_truth_plant_niche
from sdmr.observation_process import inverse_observation_propensity_weights


def test_no_observation_predictors_returns_identity_weights():
    sim = simulate_known_truth_plant_niche(
        "gaussian",
        seed=3,
        n_cells=800,
        n_occurrences=100,
        n_target_group=300,
    )
    result = inverse_observation_propensity_weights(
        sim.occurrences.iloc[:60],
        sim.target_group.iloc[:180],
        sim.occurrences.iloc[60:],
        (),
    )
    assert np.allclose(result.weights, 1.0)
    assert result.effective_sample_size == len(result.weights)
    assert result.maximum_normalized_weight == 1.0


def test_inverse_observation_weights_transport_focal_recording_bias_toward_target_group():
    sim = simulate_known_truth_plant_niche(
        "observation_confounded",
        seed=11,
        n_cells=3000,
        n_occurrences=360,
        n_target_group=1200,
        focal_recording_bias_strength=4.0,
    )
    train_presence = sim.occurrences.iloc[:220].reset_index(drop=True)
    evaluation_presence = sim.occurrences.iloc[220:].reset_index(drop=True)
    train_background = sim.target_group.iloc[:800].reset_index(drop=True)

    result = inverse_observation_propensity_weights(
        train_presence,
        train_background,
        evaluation_presence,
        ("recording_bias",),
    )
    x = evaluation_presence["recording_bias"].to_numpy(float)
    reference_mean = float(train_background["recording_bias"].mean())
    unweighted_error = abs(float(np.mean(x)) - reference_mean)
    weighted_mean = float(np.average(x[np.isfinite(result.weights)], weights=result.weights[np.isfinite(result.weights)]))
    weighted_error = abs(weighted_mean - reference_mean)

    assert weighted_error < unweighted_error
    assert result.effective_sample_size > 5
    assert np.isclose(np.nanmean(result.weights), 1.0)
    assert result.maximum_normalized_weight >= 1.0


def test_observation_weights_are_fitted_without_ecological_predictors():
    sim = simulate_known_truth_plant_niche(
        "observation_confounded",
        seed=19,
        n_cells=1800,
        n_occurrences=220,
        n_target_group=700,
        focal_recording_bias_strength=3.5,
    )
    train_presence = sim.occurrences.iloc[:140].reset_index(drop=True)
    evaluation_presence = sim.occurrences.iloc[140:].reset_index(drop=True)
    train_background = sim.target_group.iloc[:500].reset_index(drop=True)

    baseline = inverse_observation_propensity_weights(
        train_presence,
        train_background,
        evaluation_presence,
        ("recording_bias",),
    )
    changed = evaluation_presence.copy()
    changed["temperature"] = changed["temperature"] * 100.0 + 999.0
    changed["water"] = -changed["water"] * 50.0
    repeated = inverse_observation_propensity_weights(
        train_presence,
        train_background,
        changed,
        ("recording_bias",),
    )
    assert np.allclose(baseline.weights, repeated.weights, equal_nan=True)
