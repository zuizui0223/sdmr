import numpy as np
import pandas as pd

from sdmr.ecological_interpretation import build_ecological_interpretation_bundle
from sdmr.known_truth_response import DEFAULT_PROCESS_ALIASES
from sdmr.known_truth_scenarios import standard_known_truth_candidates


def _environment():
    x = np.linspace(-2.0, 2.0, 120)
    return pd.DataFrame(
        {
            "temperature": x,
            "temp_proxy": 0.9 * x,
            "water": np.sin(x),
            "soil": np.cos(x),
            "recording_bias": np.linspace(-1.0, 1.0, len(x)),
        }
    )


def test_interpretation_bundle_reports_selector_ranges_not_averages():
    env = _environment()
    canonical = np.exp(-0.5 * ((env["temperature"] - 0.3) / 0.7) ** 2)
    robust = np.exp(-0.5 * ((env["temperature"] - 0.5) / 0.8) ** 2)
    bundle = build_ecological_interpretation_bundle(
        "tw_quadratic",
        "climate_soil_quadratic",
        standard_known_truth_candidates(),
        env,
        canonical,
        robust,
        process_groups=DEFAULT_PROCESS_ALIASES,
        n_bins=10,
    )
    assert bundle.certificate.status == "partial_process_consensus"
    assert bundle.shared_response_axes == ("temperature", "water")
    assert bundle.canonical_only_response_axes == ()
    assert bundle.robust_only_response_axes == ("soil",)
    ranges = bundle.response_selector_ranges
    assert set(ranges["predictor"]) == {"temperature", "water"}
    assert "niche_center__selector_min" in ranges.columns
    assert "niche_center__selector_max" in ranges.columns
    assert "niche_center__selector_mean" not in ranges.columns
    assert (ranges["niche_center__selector_max"] >= ranges["niche_center__selector_min"]).all()


def test_process_alias_consensus_does_not_fake_numeric_proxy_comparability():
    env = _environment()
    suitability = np.exp(-0.5 * (env["temperature"] / 0.8) ** 2)
    bundle = build_ecological_interpretation_bundle(
        "tw_quadratic",
        "proxy_water_quadratic",
        standard_known_truth_candidates(),
        env,
        suitability,
        suitability,
        process_groups=DEFAULT_PROCESS_ALIASES,
        n_bins=10,
    )
    assert bundle.certificate.status == "process_consensus_model_uncertainty"
    assert bundle.certificate.stable_process_core == ("temperature", "water")
    # Temperature and temp_proxy are the same process but different numeric axes;
    # only water gets a selector range in common units.
    assert bundle.shared_response_axes == ("water",)
    assert bundle.canonical_only_response_axes == ("temperature",)
    assert bundle.robust_only_response_axes == ("temp_proxy",)
    assert set(bundle.response_selector_ranges["predictor"]) == {"water"}


def test_observation_nuisance_never_appears_as_response_axis():
    env = _environment()
    suitability = np.exp(-0.5 * (env["temperature"] / 0.8) ** 2)
    bundle = build_ecological_interpretation_bundle(
        "niche_plus_observer",
        "niche_plus_observer",
        standard_known_truth_candidates(),
        env,
        suitability,
        suitability,
        process_groups=DEFAULT_PROCESS_ALIASES,
        n_bins=10,
    )
    assert "recording_bias" not in bundle.shared_response_axes
    assert "recording_bias" not in set(bundle.canonical_response.summary["predictor"])
    assert bundle.certificate.stable_process_core == ("temperature", "water")
