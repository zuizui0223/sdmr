import numpy as np
import pandas as pd

from sdmr.known_truth import (
    evaluate_known_truth_recovery,
    generate_known_truth_niche,
    sample_virtual_occurrences,
)


def _environment(seed=7, n=2500):
    rng = np.random.default_rng(seed)
    temp = rng.normal(0, 1, n)
    water = 0.45 * temp + rng.normal(0, 0.9, n)
    proxy = temp + rng.normal(0, 0.15, n)
    noise = rng.normal(0, 1, n)
    return pd.DataFrame({"temp": temp, "water": water, "temp_proxy": proxy, "noise": noise})


def test_perfect_known_truth_recovery_beats_shifted_niche():
    env = _environment()
    truth = generate_known_truth_niche(
        env,
        ["temp", "water"],
        family="gaussian",
        centers={"temp": 0.4, "water": -0.3},
        widths={"temp": 0.7, "water": 0.8},
    )
    shifted = generate_known_truth_niche(
        env,
        ["temp", "water"],
        family="gaussian",
        centers={"temp": -1.0, "water": 0.9},
        widths={"temp": 0.7, "water": 0.8},
    )

    perfect = evaluate_known_truth_recovery(
        env,
        truth,
        truth.suitability,
        estimated_processes=["temp", "water"],
    )
    wrong = evaluate_known_truth_recovery(
        env,
        truth,
        shifted.suitability,
        estimated_processes=["temp_proxy", "noise"],
    )

    assert perfect.truth_surface_rank > 0.999
    assert perfect.truth_surface_error < 1e-12
    assert perfect.centroid_error < 1e-12
    assert perfect.breadth_log_sd_error < 1e-12
    assert perfect.limit_quantile_error < 1e-12
    assert perfect.driver_process_f1 == 1.0

    assert wrong.truth_surface_rank < perfect.truth_surface_rank
    assert wrong.truth_surface_error > perfect.truth_surface_error
    assert wrong.centroid_error > perfect.centroid_error
    assert wrong.limit_quantile_error > perfect.limit_quantile_error
    assert wrong.driver_process_f1 == 0.0


def test_virtual_niche_supports_asymmetry_interaction_and_sampling_bias():
    env = _environment(seed=11, n=1800)
    asymmetric = generate_known_truth_niche(
        env,
        ["temp"],
        family="asymmetric",
        centers={"temp": 0.2},
        left_widths={"temp": 0.35},
        right_widths={"temp": 1.1},
    )
    interacting = generate_known_truth_niche(
        env,
        ["temp", "water"],
        family="interaction",
        centers={"temp": 0.0, "water": 0.0},
        widths={"temp": 1.0, "water": 1.0},
        interaction_strength=0.45,
    )

    assert np.nanmax(asymmetric.suitability) == 1.0
    assert np.nanmax(interacting.suitability) == 1.0
    assert np.nanmin(interacting.suitability) >= 0.0

    # Bias toward larger temp values changes the observation process without
    # changing the hidden ecological truth.
    bias = np.exp(0.7 * env["temp"].to_numpy())
    sampled = sample_virtual_occurrences(env, asymmetric, 120, sampling_bias=bias, random_state=3)
    assert len(sampled) == 120
    assert sampled["virtual_reference_index"].is_unique
    assert sampled["virtual_truth_suitability"].between(0, 1).all()
