"""Exact finite counterexample: ecological signal vs outcome-dependent recording.

This is an algebraic, synthetic-only result. It reopens no frozen seed,
model fit, observed forest response or Product-A/Model-5 endpoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F


@dataclass(frozen=True)
class BinaryObservationWorld:
    name: str
    # P(Y=1 | X=x), where P(X=0)=P(X=1)=1/2.
    ecological_response: tuple[F, F]
    # P(S=1 | X=x, Y=y), keyed by (x,y), with Y observed only if S=1.
    inclusion: tuple[tuple[F, F], tuple[F, F]]

    def observed_record(self) -> tuple[tuple[F, F, F], ...]:
        """Exact probabilities of (X=x,S=1,Y=y), no rounding."""
        out = []
        for x in (0, 1):
            for y in (0, 1):
                py = self.ecological_response[x] if y else 1 - self.ecological_response[x]
                out.append((F(x), F(y), F(1, 2) * py * self.inclusion[x][y]))
        return tuple(out)

    def observed_opportunity(self) -> tuple[tuple[F, F, F], ...]:
        """Observed (X=x,S=s) mass, with Y unobserved for S=0."""
        out = []
        for x in (0, 1):
            ps1 = sum(
                (self.ecological_response[x] if y else 1 - self.ecological_response[x])
                * self.inclusion[x][y] for y in (0, 1)
            )
            out.extend(((F(x), F(0), F(1, 2) * (1 - ps1)),
                        (F(x), F(1), F(1, 2) * ps1)))
        return tuple(out)

    def ecological_contrast(self) -> F:
        return self.ecological_response[1] - self.ecological_response[0]


def exact_counterexample() -> tuple[BinaryObservationWorld, BinaryObservationWorld]:
    """A real ecological difference and pure recording selection look identical."""
    ecological = BinaryObservationWorld(
        name="real_ecological_response_ignorable_recording",
        ecological_response=(F(1, 4), F(3, 4)),
        inclusion=((F(1, 2), F(1, 2)), (F(1, 2), F(1, 2))),
    )
    selection_only = BinaryObservationWorld(
        name="zero_ecological_response_outcome_dependent_recording",
        ecological_response=(F(1, 2), F(1, 2)),
        inclusion=((F(3, 4), F(1, 4)), (F(1, 4), F(3, 4))),
    )
    return ecological, selection_only


def verify_exact_counterexample() -> dict[str, object]:
    a, b = exact_counterexample()
    # Full observed data are (X,S), plus Y if and only if S=1.
    same_records = a.observed_record() == b.observed_record()
    same_opportunity = a.observed_opportunity() == b.observed_opportunity()
    if not (same_records and same_opportunity):
        raise AssertionError("counterexample did not attain exact observable equivalence")
    if not (a.ecological_contrast() == F(1, 2) and b.ecological_contrast() == 0):
        raise AssertionError("ecological ground truths are not different")
    p_xs1 = [row[2] for row in a.observed_opportunity() if row[1] == 1]
    if p_xs1 != [F(1, 4), F(1, 4)]:
        raise AssertionError("marginal observation opportunities differ by X")

    return {
        "schema": "sdmr.structural_selection_nonidentifiability.v1",
        "fully_observed_x_s_and_y_when_recorded_identical": True,
        "exact_observed_probabilities_x_y_s1": {
            f"x{int(x)}_y{int(y)}": str(p) for x, y, p in a.observed_record()
        },
        "exact_observed_probabilities_x_s0": {
            f"x{int(x)}": str(p)
            for x, s, p in a.observed_opportunity() if s == 0
        },
        "marginal_recording_probability_by_x": ["1/2", "1/2"],
        "population_contrast_ecological_world": str(a.ecological_contrast()),
        "population_contrast_selection_only_world": str(b.ecological_contrast()),
        "no_field_responses_loaded": True,
        "no_fitted_models": True,
        "not_empirical_process_identification": True,
    }
