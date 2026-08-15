import numpy as np
import pandas as pd

from sdmr.known_truth_response import (
    known_truth_process_profile,
    known_truth_response_profile,
)


def test_perfect_prediction_recovers_surface_response_optimum_and_limits():
    x = np.linspace(-2.0, 2.0, 1200)
    water = np.sin(x) + np.linspace(-0.5, 0.5, len(x))
    environment = pd.DataFrame({"temperature": x, "water": water})
    truth = np.exp(-0.5 * (((x - 0.4) / 0.55) ** 2 + ((water + 0.2) / 0.8) ** 2))

    profile = known_truth_response_profile(
        environment,
        truth,
        truth,
        ("temperature", "water"),
    )

    assert profile.truth_surface_rank > 0.999999
    assert profile.truth_surface_nrmse < 1e-12
    assert profile.response_curve_error < 1e-12
    assert profile.optimum_error < 1e-12
    assert profile.lower_limit_error < 1e-12
    assert profile.upper_limit_error < 1e-12


def test_wrong_response_surface_is_detected_even_when_scores_are_finite():
    rng = np.random.default_rng(7)
    environment = pd.DataFrame(
        {
            "temperature": rng.normal(0, 1, 1800),
            "water": rng.normal(0, 1, 1800),
        }
    )
    t = environment["temperature"].to_numpy()
    w = environment["water"].to_numpy()
    truth = np.exp(-0.5 * (((t - 0.6) / 0.5) ** 2 + ((w + 0.3) / 0.7) ** 2))
    wrong = np.exp(-0.5 * (((t + 0.9) / 0.5) ** 2 + ((w - 0.8) / 0.7) ** 2))

    good = known_truth_response_profile(environment, truth, truth, ("temperature", "water"))
    bad = known_truth_response_profile(environment, wrong, truth, ("temperature", "water"))

    assert good.truth_surface_rank > bad.truth_surface_rank
    assert good.truth_surface_nrmse < bad.truth_surface_nrmse
    assert good.response_curve_error < bad.response_curve_error
    assert good.optimum_error < bad.optimum_error
    assert good.lower_limit_error < bad.lower_limit_error
    assert good.upper_limit_error < bad.upper_limit_error


def test_process_recovery_treats_temperature_proxy_as_same_process():
    proxy = known_truth_process_profile(
        ("temp_proxy", "water"),
        ("temperature", "water"),
    )
    contaminated = known_truth_process_profile(
        ("temperature", "water", "recording_bias"),
        ("temperature", "water"),
    )

    assert proxy.driver_process_precision == 1.0
    assert proxy.driver_process_recall == 1.0
    assert proxy.driver_process_f1 == 1.0
    assert contaminated.driver_process_recall == 1.0
    assert contaminated.driver_process_precision < 1.0
    assert contaminated.driver_process_f1 < 1.0
