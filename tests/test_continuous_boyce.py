import numpy as np

from sdmr.metrics import continuous_boyce_index


def test_continuous_boyce_is_positive_when_presences_concentrate_at_high_suitability():
    fit = np.linspace(0.0, 1.0, 2001)
    obs = np.linspace(0.65, 1.0, 301)
    score = continuous_boyce_index(obs, fit)
    assert np.isfinite(score)
    assert score > 0.8


def test_continuous_boyce_is_negative_for_counter_prediction():
    fit = np.linspace(0.0, 1.0, 2001)
    obs = np.linspace(0.0, 0.35, 301)
    score = continuous_boyce_index(obs, fit)
    assert np.isfinite(score)
    assert score < -0.8


def test_continuous_boyce_reports_nan_when_fit_has_no_suitability_range():
    fit = np.ones(100)
    obs = np.ones(20)
    assert np.isnan(continuous_boyce_index(obs, fit))


def test_continuous_boyce_supports_hirzel_style_duplicate_retention_sensitivity():
    fit = np.linspace(0.0, 1.0, 1001)
    obs = np.concatenate((np.linspace(0.45, 0.65, 60), np.linspace(0.8, 1.0, 80)))
    current_ecospat_style = continuous_boyce_index(
        obs, fit, remove_successive_duplicates=True
    )
    retain_duplicates = continuous_boyce_index(
        obs, fit, remove_successive_duplicates=False
    )
    assert np.isfinite(current_ecospat_style)
    assert np.isfinite(retain_duplicates)
    assert -1.0 <= current_ecospat_style <= 1.0
    assert -1.0 <= retain_duplicates <= 1.0
