from fractions import Fraction

import pytest

from sdmr.structural_context_oracle import (
    GaussianStructureWorld,
    observationally_identical_counterexamples,
    verify_snapshot_nonidentifiability,
)


def test_three_gaussian_worlds_have_identical_observed_snapshot_distribution():
    worlds = observationally_identical_counterexamples()
    assert set(worlds) == {
        "persistent_site_proxy", "positive_within_site", "negative_within_site"
    }
    assert verify_snapshot_nonidentifiability() == (
        Fraction(2), Fraction(2), Fraction(1)
    )
    assert {world.snapshot_moments() for world in worlds.values()} == {
        (Fraction(2), Fraction(2), Fraction(1))
    }


def test_same_positive_spatial_covariance_has_zero_positive_negative_within_slope():
    worlds = observationally_identical_counterexamples()
    assert worlds["persistent_site_proxy"].within_site_slope() == 0
    assert worlds["positive_within_site"].within_site_slope() == Fraction(1, 3)
    assert worlds["negative_within_site"].within_site_slope() == Fraction(-1, 2)
    assert all(w.snapshot_moments()[2] == 1 for w in worlds.values())


def test_invalid_variance_or_missing_within_support_refused():
    with pytest.raises(ValueError, match="variance"):
        GaussianStructureWorld(Fraction(-1), Fraction(1), Fraction(0), Fraction(1))
    with pytest.raises(ValueError, match="within-site"):
        GaussianStructureWorld(Fraction(1), Fraction(0), Fraction(0), Fraction(1))
