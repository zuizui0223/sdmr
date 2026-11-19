"""Exact Gaussian counterexample: spatial association need not identify a temporal process.

Mathematical demonstration only, NOT an empirical analysis or a new causal
identification theorem. Conditional on independent Gaussian components,

    B_it = U_i + V_it
    Y_it = U_i + beta * V_it + E_it,

where U_i is persistent site quality, V_it is within-site structure variation,
and E_it is independent residual variation. Single-time (B,Y) moments can be
identical for worlds with different within-site beta.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class GaussianStructureWorld:
    site_variance: Fraction
    within_variance: Fraction
    within_beta: Fraction
    residual_variance: Fraction

    def __post_init__(self) -> None:
        if any(
            x < 0 for x in (
                self.site_variance, self.within_variance, self.residual_variance
            )
        ):
            raise ValueError("variance components must be nonnegative")
        if self.within_variance == 0:
            raise ValueError("within-site variance must be positive")

    def snapshot_moments(self) -> tuple[Fraction, Fraction, Fraction]:
        """Exact (Var(B), Var(Y), Cov(B,Y)) of a one-time Gaussian snapshot."""
        u, v, beta, e = (
            self.site_variance, self.within_variance,
            self.within_beta, self.residual_variance,
        )
        return (u + v, u + beta * beta * v + e, u + beta * v)

    def within_site_slope(self) -> Fraction:
        """Temporal within-site slope under the stated independent-noise world."""
        return self.within_beta


def observationally_identical_counterexamples() -> dict[str, GaussianStructureWorld]:
    """Three exactly snapshot-equivalent worlds with 0, positive, negative slopes."""
    return {
        "persistent_site_proxy": GaussianStructureWorld(
            Fraction(1), Fraction(1), Fraction(0), Fraction(1)
        ),
        "positive_within_site": GaussianStructureWorld(
            Fraction(1, 2), Fraction(3, 2), Fraction(1, 3), Fraction(4, 3)
        ),
        "negative_within_site": GaussianStructureWorld(
            Fraction(4, 3), Fraction(2, 3), Fraction(-1, 2), Fraction(1, 2)
        ),
    }


def verify_snapshot_nonidentifiability() -> tuple[Fraction, Fraction, Fraction]:
    worlds = observationally_identical_counterexamples()
    unique_moments = {world.snapshot_moments() for world in worlds.values()}
    unique_within_slopes = {world.within_site_slope() for world in worlds.values()}
    if len(unique_moments) != 1 or len(unique_within_slopes) != 3:
        raise AssertionError("counterexample no longer demonstrates nonidentifiability")
    return next(iter(unique_moments))
