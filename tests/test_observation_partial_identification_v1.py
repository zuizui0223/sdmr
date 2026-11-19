"""Synthetic-only exact partial-identification tests; no real source opens."""
from fractions import Fraction as Q
from itertools import product

import pytest

from sdmr.observation_partial_identification_v1 import (
    BinaryOpportunity, exact_selection_counterexample_bounds,
    sharp_binary_contrast_bounds,
)


def _bound(a, b, **opts):
    return sharp_binary_contrast_bounds(
        a, b, complete_source_frame_verified=True,
        actual_recorded_negatives_verified=True, **opts,
    )


def test_observation_equivalent_worlds_have_same_wide_sharp_bounds():
    receipt = exact_selection_counterexample_bounds()
    assert receipt["lower"] == "-1/4"
    assert receipt["upper"] == "3/4"
    assert receipt["risk_0"] == ["1/8", "5/8"]
    assert receipt["risk_1"] == ["3/8", "7/8"]
    assert receipt["sign"] == "unresolved_including_zero"
    assert receipt["is_confidence_interval"] is False
    assert receipt["causal_process_identified"] is False
    assert receipt["biological_result_estimated"] is False
    assert receipt["newly_opened_field_responses"] is False


def test_two_sided_sign_robust_examples_and_empty_missing_frame():
    p = _bound(
        BinaryOpportunity("0", 1, 8, 1, 10),
        BinaryOpportunity("1", 8, 1, 1, 10),
    )
    assert (p.lower, p.upper, p.sign) == (
        Q(3, 5), Q(4, 5), "positive_for_all_missing_outcomes"
    )
    n = _bound(
        BinaryOpportunity("0", 8, 1, 1, 10),
        BinaryOpportunity("1", 1, 8, 1, 10),
    )
    assert (n.lower, n.upper, n.sign) == (
        Q(-4, 5), Q(-3, 5), "negative_for_all_missing_outcomes"
    )
    full = _bound(
        BinaryOpportunity("0", 2, 3, 0, 5),
        BinaryOpportunity("1", 3, 2, 0, 5),
    )
    assert (full.lower, full.upper) == (Q(1, 5), Q(1, 5))


def test_near_zero_includes_zero_and_never_promotes_process():
    x = _bound(
        BinaryOpportunity("0", 2, 3, 5, 10),
        BinaryOpportunity("1", 6, 2, 2, 10),
    )
    assert x.lower <= 0 <= x.upper
    assert x.sign == "unresolved_including_zero"
    assert x.causal_process_identified is False


def test_missing_sampling_opportunity_or_real_recorded_zero_refuses_calculation():
    a = BinaryOpportunity("0", 1, 3, 4, 8)
    b = BinaryOpportunity("1", 3, 1, 4, 8)
    for opt in ({}, {"complete_source_frame_verified": True},
                {"actual_recorded_negatives_verified": True},
                {"complete_source_frame_verified": 1,
                 "actual_recorded_negatives_verified": True}):
        result = sharp_binary_contrast_bounds(a, b, **opt)
        assert result.status == "non_admissible_observation_frame"
        assert result.lower is None and result.upper is None
        assert result.sign == "unavailable"


def test_invalid_frame_denominator_missing_and_boolean_counts_are_not_zeros():
    for values in ((1, 3, 3, 8), (1, 3, 5, 8), (0, 0, 0, 0),
                   (True, 3, 4, 8), (-1, 5, 4, 8)):
        with pytest.raises(ValueError):
            BinaryOpportunity("bad", *values)
    with pytest.raises(ValueError, match="stratum identifiers"):
        _bound(BinaryOpportunity("A", 1, 0, 0, 1),
               BinaryOpportunity("A", 0, 1, 0, 1))


def test_sharpness_by_enumerating_all_missing_binary_completions():
    # Exhaustively verifies the algebraic extrema on small census risk sets.
    for n0 in range(1, 6):
        for n1 in range(1, 6):
            for p0 in range(n0 + 1):
                for m0 in range(n0 - p0 + 1):
                    z0 = n0 - p0 - m0
                    a = BinaryOpportunity("0", p0, z0, m0, n0)
                    for p1 in range(n1 + 1):
                        for m1 in range(n1 - p1 + 1):
                            z1 = n1 - p1 - m1
                            b = BinaryOpportunity("1", p1, z1, m1, n1)
                            result = _bound(a, b)
                            feasible = [
                                Q(p1 + y1, n1) - Q(p0 + y0, n0)
                                for y0, y1 in product(
                                    range(m0 + 1), range(m1 + 1)
                                )
                            ]
                            assert result.lower == min(feasible)
                            assert result.upper == max(feasible)
