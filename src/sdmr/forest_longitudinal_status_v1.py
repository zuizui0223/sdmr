"""Forest tree census observation-status contracts (codebook only).

BCI 2026 and Harvard Forest HF453 statuses are source-specific. Merely
normalizing codes is not mortality inference. Do not load original census
response rows before a separate source/identity/protocol freeze. In
particular 'missing' is NOT dead, 'future recruit' is NOT an observed
absence, and a BCI stem label is NOT stable across censuses.
"""
from __future__ import annotations

from dataclasses import dataclass

BCI = "bci_dryad_2026_aug31"
HARVARD = "harvard_hf453_2026_v1"

STATUS_SCHEMAS: dict[str, dict[str, tuple[str, str]]] = {
    BCI: {
        "alive": ("alive", "source_reported"),
        "dead": ("reported_dead_mixed", "found_or_inferred_unknown"),
        "missing": ("missing", "unresolved"),
        "future recruit": ("not_yet_recruited", "not_at_risk"),
    },
    HARVARD: {
        "A": ("alive", "source_reported"),
        "AU": ("alive_with_health_issue", "source_reported"),
        "DC": ("observed_dead", "dead_down"),
        "DS": ("observed_dead", "dead_standing"),
        "DN": ("reported_dead_unfound", "not_directly_observed"),
    },
}
BCI_CENSUS_LABELS = frozenset({2004, 2014, 2025})
HARVARD_CENSUS_LABELS = frozenset({2021, 2022, 2023, 2024})


@dataclass(frozen=True)
class TreeStatus:
    source: str
    raw_code: str
    meaning: str
    certainty: str


@dataclass(frozen=True)
class TransitionAdmissibility:
    source: str
    first_year: int
    next_year: int
    status: str
    actual_exposure_time_established: bool
    population_mortality_estimated: bool
    biological_result_opening_authorized: bool


def map_tree_status(source: str, raw_status: str) -> TreeStatus:
    """Use exact published codes, no guessing from numeric or unknown labels."""
    if source not in STATUS_SCHEMAS:
        raise ValueError("unknown tree status source")
    if not isinstance(raw_status, str):
        raise ValueError("source status code must be literal string")
    if raw_status not in STATUS_SCHEMAS[source]:
        raise ValueError("unregistered original tree status label")
    meaning, certainty = STATUS_SCHEMAS[source][raw_status]
    return TreeStatus(source, raw_status, meaning, certainty)


def source_tree_identity(source: str, plot: str, tag: str, *,
                         stem_tag: str | None = None) -> tuple[str, str, str]:
    """A BCI tree requires plot+tag; never track a multi-stem ID over censuses."""
    if source not in STATUS_SCHEMAS:
        raise ValueError("unknown tree identity source")
    if not isinstance(plot, str) or not plot.strip():
        raise ValueError("physical plot required")
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("individual tree tag required")
    if source == BCI and stem_tag is not None:
        raise ValueError("BCI individual stems cannot be linked across censuses")
    return (source, plot, tag)


def classify_census_transition(
    source: str, first_year: int, next_year: int,
    first_status: str, next_status: str,
) -> TransitionAdmissibility:
    """Classify source-labeled transition without asserting a death hazard.

    Actual visit dates and original at-risk opportunities remain compulsory
    for real interval hazards; census year labels alone are insufficient.
    """
    allowed = BCI_CENSUS_LABELS if source == BCI else (
        HARVARD_CENSUS_LABELS if source == HARVARD else set()
    )
    if (first_year not in allowed or next_year not in allowed or
            next_year <= first_year):
        raise ValueError("invalid source census chronological order")
    start = map_tree_status(source, first_status)
    finish = map_tree_status(source, next_status)
    if start.meaning == "not_yet_recruited":
        disposition = "not_at_risk_until_recruitment"
    elif start.meaning not in ("alive", "alive_with_health_issue"):
        disposition = "start_state_not_verified_at_risk"
    elif finish.meaning in ("alive", "alive_with_health_issue"):
        disposition = "observed_alive_at_next_census"
    elif finish.meaning == "observed_dead":
        disposition = "source_observed_dead_candidate"
    elif finish.meaning in ("reported_dead_mixed", "reported_dead_unfound"):
        disposition = "reported_death_not_directly_certified"
    elif finish.meaning == "missing":
        disposition = "missing_outcome_not_automatically_death"
    else:
        disposition = "invalid_or_unresolved_transition"
    return TransitionAdmissibility(
        source=source, first_year=first_year, next_year=next_year,
        status=disposition,
        actual_exposure_time_established=False,
        population_mortality_estimated=False,
        biological_result_opening_authorized=False,
    )
