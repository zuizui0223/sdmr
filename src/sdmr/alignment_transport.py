"""Source-environment trained conditional-alignment transport primitive for v15.

This module is development-only infrastructure. It fits the existing conditional
shared-information knockout on one background source environment and applies the
frozen map to disjoint target frames. It accepts no occurrence outcomes,
suitability values, biological labels, or generating-process truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import pandas as pd

from .conditional_shared_information_knockout import (
    ConditionalSharedInformationKnockout,
    fit_conditional_shared_information_knockout,
    verify_retained_predictors_unchanged,
)


@dataclass(frozen=True)
class AlignmentTransportMap:
    process: str
    source_block: int
    process_predictors: tuple[str, ...]
    conditioning_predictors: tuple[str, ...]
    knockout: ConditionalSharedInformationKnockout

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        return self.knockout.transform(frame)


def fit_alignment_transport_map(
    background: pd.DataFrame,
    background_blocks,
    *,
    source_block: int,
    process: str,
    process_predictors: Sequence[str],
    conditioning_predictors: Sequence[str],
    degree: int = 2,
    ridge_alpha: float = 1.0,
    minimum_complete_rows: int = 10,
) -> AlignmentTransportMap:
    """Fit P<-Q only on rows belonging to one declared source block."""
    blocks = pd.Series(background_blocks, index=background.index)
    source = background.loc[blocks.eq(int(source_block))].copy()
    if len(source) < int(minimum_complete_rows):
        raise ValueError(
            f"source block needs at least {int(minimum_complete_rows)} background rows; found {len(source)}"
        )
    knockout = fit_conditional_shared_information_knockout(
        source,
        process=str(process),
        process_predictors=process_predictors,
        conditioning_predictors=conditioning_predictors,
        degree=int(degree),
        ridge_alpha=float(ridge_alpha),
        minimum_complete_rows=int(minimum_complete_rows),
    )
    return AlignmentTransportMap(
        process=str(process),
        source_block=int(source_block),
        process_predictors=tuple(str(x) for x in process_predictors),
        conditioning_predictors=tuple(str(x) for x in conditioning_predictors),
        knockout=knockout,
    )


def verify_transport_retained_predictors(
    before: pd.DataFrame,
    after: pd.DataFrame,
    *,
    ecological_predictors: Sequence[str],
    process_predictors: Sequence[str],
) -> bool:
    p = set(str(x) for x in process_predictors)
    retained = tuple(str(x) for x in ecological_predictors if str(x) not in p)
    return verify_retained_predictors_unchanged(
        before,
        after,
        retained_predictors=retained,
    )
