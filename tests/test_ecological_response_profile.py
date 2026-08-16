import numpy as np
import pandas as pd

from sdmr.ecological_response_profile import ecological_response_profile


def test_response_profile_reports_center_breadth_limits_and_curve():
    x = np.linspace(-2.0, 2.0, 101)
    environment = pd.DataFrame({"temperature": x})
    suitability = np.exp(-0.5 * ((x - 0.5) / 0.6) ** 2)
    profile = ecological_response_profile(
        environment,
        suitability,
        ("temperature",),
        n_bins=10,
    )
    row = profile.summary.iloc[0]
    assert row["predictor"] == "temperature"
    assert 0.35 < row["niche_center"] < 0.65
    assert row["lower_limit"] < row["niche_center"] < row["upper_limit"]
    assert 0.2 < row["niche_breadth_sd"] < 0.9
    assert 0.2 < row["marginal_optimum"] < 0.8
    assert row["marginal_direction_changes"] >= 1
    assert row["n_curve_bins"] == len(profile.curves)


def test_monotonic_response_keeps_direction_as_diagnostic_not_category():
    x = np.linspace(0.0, 1.0, 100)
    environment = pd.DataFrame({"water": x})
    profile = ecological_response_profile(
        environment,
        0.1 + x,
        ("water",),
        n_bins=10,
    )
    row = profile.summary.iloc[0]
    assert row["marginal_rank_correlation"] > 0.99
    assert row["marginal_direction_changes"] == 0
    assert "response_shape_class" not in profile.summary.columns


def test_suitability_is_mass_not_required_to_be_probability():
    environment = pd.DataFrame({"soil": np.arange(20, dtype=float)})
    profile = ecological_response_profile(
        environment,
        np.linspace(1.0, 100.0, 20),
        ("soil",),
        n_bins=5,
    )
    assert np.isfinite(profile.summary.loc[0, "niche_center"])


def test_observation_predictors_can_be_excluded_by_caller():
    environment = pd.DataFrame(
        {
            "temperature": np.linspace(-1.0, 1.0, 30),
            "recording_bias": np.linspace(1.0, -1.0, 30),
        }
    )
    profile = ecological_response_profile(
        environment,
        np.ones(30),
        ("temperature",),
        n_bins=5,
    )
    assert set(profile.summary["predictor"]) == {"temperature"}
    assert "recording_bias" not in set(profile.curves["predictor"])
