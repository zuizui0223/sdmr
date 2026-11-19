"""Sharp finite-population binary-outcome bounds under unknown recording selection.

Methodological algebra only; no forest, GBIF, or biological outcome rows loaded.
The source frame/recorded-zero eligibility declaration is the responsibility of
a *separate* original-source and observation process audit.

Target: associational conditional mean contrast E[Y|X=1]-E[Y|X=0].
It is NOT an average causal effect, and does NOT identify ecological mechanisms.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q


@dataclass(frozen=True)
class BinaryOpportunity:
    """One stratum of a COMPLETE sampling opportunity frame.

    A 'recorded_negative' must be an actually assessed negative outcome,
    not a site absent from GBIF, a failed sequence, an unfound stem, or a
    survey without verified effort. One eligible physical risk-event is
    counted once; repeated observation events require their own design.
    """

    stratum: str
    recorded_positive: int
    recorded_negative: int
    outcome_unobserved: int
    eligible_total: int

    def __post_init__(self) -> None:
        if not isinstance(self.stratum, str) or not self.stratum.strip():
            raise ValueError("nonempty stratum name required")
        for field in (
            "recorded_positive", "recorded_negative", "outcome_unobserved",
            "eligible_total",
        ):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field} must be a nonnegative integer")
        if self.eligible_total < 1:
            raise ValueError("eligible_total must be positive")
        if (
            self.recorded_positive + self.recorded_negative
            + self.outcome_unobserved != self.eligible_total
        ):
            raise ValueError(
                "recorded positive + recorded negative + unobserved "
                "must equal entire eligible risk-set denominator"
            )

    @property
    def risk_lower(self) -> Q:
        return Q(self.recorded_positive, self.eligible_total)

    @property
    def risk_upper(self) -> Q:
        return Q(
            self.recorded_positive + self.outcome_unobserved,
            self.eligible_total,
        )

    @property
    def inclusion_rate(self) -> Q:
        return Q(
            self.recorded_positive + self.recorded_negative,
            self.eligible_total,
        )


@dataclass(frozen=True)
class BinaryContrastBounds:
    """Exact *identification* interval, not a frequentist confidence interval."""

    status: str
    lower: Q | None
    upper: Q | None
    sign: str
    conditional_risk_0: tuple[Q, Q] | None
    conditional_risk_1: tuple[Q, Q] | None
    target: str = "associational_conditional_mean_difference"
    causal_process_identified: bool = False
    biological_result_estimated: bool = False
    newly_opened_field_responses: bool = False

    def receipt(self) -> dict[str, object]:
        stringify = lambda x: str(x) if x is not None else None
        return {
            "schema": "sdmr.binary_observation_partial_identification.v1",
            "status": self.status,
            "lower": stringify(self.lower),
            "upper": stringify(self.upper),
            "sign": self.sign,
            "risk_0": (
                [str(x) for x in self.conditional_risk_0]
                if self.conditional_risk_0 is not None else None
            ),
            "risk_1": (
                [str(x) for x in self.conditional_risk_1]
                if self.conditional_risk_1 is not None else None
            ),
            "target": self.target,
            "causal_process_identified": self.causal_process_identified,
            "biological_result_estimated": self.biological_result_estimated,
            "newly_opened_field_responses": self.newly_opened_field_responses,
            "requires_independently_verified_sampling_opportunity": True,
            "is_confidence_interval": False,
        }


def sharp_binary_contrast_bounds(
    group_0: BinaryOpportunity,
    group_1: BinaryOpportunity,
    *,
    complete_source_frame_verified: bool = False,
    actual_recorded_negatives_verified: bool = False,
) -> BinaryContrastBounds:
    """Sharp ignorance bounds allowing *arbitrary* Y-dependent missingness.

    For x=0,1, let p_x be recorded positives, n_x recorded negatives,
    m_x missing outcomes and N_x=p_x+n_x+m_x.
    Then P(Y=1|X=x) belongs to [p_x/N_x,(p_x+m_x)/N_x].
    The contrast's sharp interval is [lower_1-upper_0,upper_1-lower_0].
    This assumes binary Y, complete risk-set frame, and no structural
    restrictions on missing outcomes; it makes NO no-MNAR assumption.

    Both safety declarations are externally audited prerequisites, not
    something these aggregate counts can prove themselves. A non-admissible
    call returns no numerical bounds or biological claims.
    """
    if group_0.stratum == group_1.stratum:
        raise ValueError("stratum identifiers must differ")
    if (
        complete_source_frame_verified is not True
        or actual_recorded_negatives_verified is not True
    ):
        return BinaryContrastBounds(
            status="non_admissible_observation_frame",
            lower=None, upper=None, sign="unavailable",
            conditional_risk_0=None, conditional_risk_1=None,
        )
    lower = group_1.risk_lower - group_0.risk_upper
    upper = group_1.risk_upper - group_0.risk_lower
    sign = (
        "positive_for_all_missing_outcomes" if lower > 0
        else "negative_for_all_missing_outcomes" if upper < 0
        else "unresolved_including_zero"
    )
    return BinaryContrastBounds(
        status="sharp_partial_identification_only",
        lower=lower, upper=upper, sign=sign,
        conditional_risk_0=(group_0.risk_lower, group_0.risk_upper),
        conditional_risk_1=(group_1.risk_lower, group_1.risk_upper),
    )


def exact_selection_counterexample_bounds() -> dict[str, object]:
    """Matches two observationally equivalent synthetic worlds, no new draws."""
    from sdmr.structural_selection_counterexample_v1 import exact_counterexample

    ecology, selection_only = exact_counterexample()
    if ecology.observed_record() != selection_only.observed_record():
        raise AssertionError("counterexample observed records differ")
    if ecology.observed_opportunity() != selection_only.observed_opportunity():
        raise AssertionError("counterexample observation opportunities differ")
    # Conditional on X=x, both worlds have 8/16 risk units in each group
    # under a common denominator. The scale of the count table is arbitrary.
    result = sharp_binary_contrast_bounds(
        BinaryOpportunity("X0", 1, 3, 4, 8),
        BinaryOpportunity("X1", 3, 1, 4, 8),
        complete_source_frame_verified=True,
        actual_recorded_negatives_verified=True,
    )
    assert result.lower == Q(-1, 4) and result.upper == Q(3, 4)
    assert result.lower <= ecology.ecological_contrast() <= result.upper
    assert result.lower <= selection_only.ecological_contrast() <= result.upper
    return result.receipt()
