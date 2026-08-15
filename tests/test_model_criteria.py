import math

from sdmr.model_criteria import corrected_aic, or10


def test_or10_uses_training_defined_threshold():
    train = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    test = [0.05, 0.25, 0.8, 0.9]
    value = or10(train, test)
    assert value == 0.25


def test_corrected_aic_matches_formula_and_rejects_undefined_small_sample():
    value = corrected_aic(log_likelihood=-10.0, n_parameters=2, n_observations=30)
    expected = 2 * 2 - 2 * (-10.0) + (2 * 2 * 3) / (30 - 2 - 1)
    assert math.isclose(value, expected)
    assert math.isinf(corrected_aic(log_likelihood=-10.0, n_parameters=10, n_observations=11))
