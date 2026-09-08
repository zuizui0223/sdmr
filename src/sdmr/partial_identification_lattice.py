"""Partial-identification lattice for process attribution.

v9 separates two estimands that earlier Product-A successors conflated:

- total contribution: does the declared process representation participate in a
  recoverable route under the frozen interval-evidence contract?
- unique contribution: does contribution remain after the target process closure
  is replaced by E[P | other declared processes]?

The resulting state is deliberately set-valued when attribution cannot be made
uniquely from the observed representation. This module performs no model fitting
and introduces no new scientific threshold.
"""
from __future__ import annotations

from dataclasses import dataclass

CONTRIBUTORY = "contributory_under_evidence_contract"
REPLACEABLE = "replaceable_under_evidence_contract"
UNRESOLVED = "unresolved"

UNIQUE_CONTRIBUTORY = "unique_contributory"
SHARED_CANDIDATE = "shared_candidate"
REPLACEABLE_STATE = "replaceable"
UNRESOLVED_STATE = "unresolved"


@dataclass(frozen=True)
class PartialIdentificationState:
    total_status: str
    unique_status: str
    state: str

    @property
    def individually_identified(self) -> bool:
        return self.state == UNIQUE_CONTRIBUTORY

    @property
    def retained_as_candidate(self) -> bool:
        return self.state in {UNIQUE_CONTRIBUTORY, SHARED_CANDIDATE}


def classify_partial_identification(*, total_status: str, unique_status: str) -> PartialIdentificationState:
    """Map total and unique evidence states to the v9 attribution lattice.

    No unresolved input is promoted. A process is individually attributed only
    when the unique conditional-knockout endpoint is contributory. Total-only
    support is retained as a shared candidate rather than forced to a singleton.
    """
    total = str(total_status)
    unique = str(unique_status)

    if unique == CONTRIBUTORY:
        state = UNIQUE_CONTRIBUTORY
    elif total == CONTRIBUTORY and unique in {REPLACEABLE, UNRESOLVED}:
        state = SHARED_CANDIDATE
    elif total == REPLACEABLE and unique == REPLACEABLE:
        state = REPLACEABLE_STATE
    else:
        state = UNRESOLVED_STATE

    return PartialIdentificationState(total_status=total, unique_status=unique, state=state)
