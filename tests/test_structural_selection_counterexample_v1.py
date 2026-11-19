"""Exact, no-data regression tests for the source-selection nonidentifiability proof."""
from fractions import Fraction as F

from sdmr.structural_selection_counterexample_v1 import (
    exact_counterexample, verify_exact_counterexample,
)


def test_same_complete_observed_distribution_different_ecological_truth():
    ecology, selection = exact_counterexample()
    assert ecology.ecological_contrast() == F(1, 2)
    assert selection.ecological_contrast() == F(0)
    assert ecology.observed_record() == selection.observed_record()
    assert ecology.observed_opportunity() == selection.observed_opportunity()


def test_exact_joint_probabilities_and_equal_observed_effort():
    ecology, selection = exact_counterexample()
    expected = [F(3, 16), F(1, 16), F(1, 16), F(3, 16)]
    assert [r[2] for r in ecology.observed_record()] == expected
    assert [r[2] for r in selection.observed_record()] == expected
    for world in (ecology, selection):
        opportunity = world.observed_opportunity()
        assert [r[2] for r in opportunity] == [F(1, 4)] * 4
        assert sum(r[2] for r in world.observed_record()) == F(1, 2)
        assert sum(r[2] for r in opportunity) == 1


def test_receipt_nonpromotion_and_no_real_source_access():
    receipt = verify_exact_counterexample()
    assert receipt["fully_observed_x_s_and_y_when_recorded_identical"]
    assert receipt["population_contrast_ecological_world"] == "1/2"
    assert receipt["population_contrast_selection_only_world"] == "0"
    assert receipt["exact_observed_probabilities_x_y_s1"] == {
        "x0_y0": "3/16", "x0_y1": "1/16",
        "x1_y0": "1/16", "x1_y1": "3/16",
    }
    assert receipt["exact_observed_probabilities_x_s0"] == {
        "x0": "1/4", "x1": "1/4",
    }
    assert receipt["no_field_responses_loaded"] is True
    assert receipt["no_fitted_models"] is True
    assert receipt["not_empirical_process_identification"] is True
