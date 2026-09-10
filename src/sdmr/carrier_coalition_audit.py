"""Background-only carrier-coalition audit for v12.

A v9 shared candidate may be replaceable by the joint information in several
other declared processes even when no single process transports enough
information about the target on its own. This module enumerates process
coalitions before any ecological outcome comparison and returns inclusion-
minimal coalitions whose union closure predicts the target closure across
pre-existing background blocks.
"""
from __future__ import annotations

from itertools import combinations
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .environmental_decorrelation_audit import audit_environmental_decorrelation


COALITION_COLUMNS = (
    "target_process",
    "coalition_processes",
    "coalition_size",
    "coalition_predictors",
    "structurally_disjoint",
    "n_complete_blocks",
    "median_heldout_r2",
    "eligible_coalition",
    "minimal_eligible_coalition",
    "n_separating_blocks",
    "separating_blocks",
)


def _union_predictors(processes: Sequence[str], closures: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    values: list[str] = []
    for process in processes:
        if process not in closures:
            raise KeyError(f"missing closure for process: {process}")
        for predictor in closures[process]:
            predictor = str(predictor)
            if predictor not in values:
                values.append(predictor)
    if not values:
        raise ValueError("coalition closure must not be empty")
    return tuple(values)


def audit_carrier_coalitions(
    background: pd.DataFrame,
    block_labels: Sequence[int],
    *,
    target_process: str,
    process_universe: Sequence[str],
    closures: Mapping[str, Sequence[str]],
    minimum_complete_blocks: int = 3,
    minimum_median_heldout_r2: float = 0.0,
    degree: int = 2,
    ridge_alpha: float = 1.0,
    material_r2_drop: float = 0.10,
    sem_multiplier: float = 1.0,
    minimum_complete_rows_per_block: int = 10,
) -> pd.DataFrame:
    """Enumerate background-defined carrier coalitions and flag minimal ones."""
    target = str(target_process)
    processes = tuple(str(x) for x in process_universe)
    if target not in processes:
        raise ValueError("target_process must belong to process_universe")
    if int(minimum_complete_blocks) < 3:
        raise ValueError("minimum_complete_blocks must be >= 3")
    target_predictors = tuple(str(x) for x in closures[target])
    others = tuple(x for x in processes if x != target)
    rows: list[dict[str, object]] = []

    for size in range(1, len(others) + 1):
        for coalition in combinations(others, size):
            competitor_predictors = _union_predictors(coalition, closures)
            disjoint = not bool(set(target_predictors) & set(competitor_predictors))
            n_complete = 0
            median_r2 = float("nan")
            separating: tuple[int, ...] = ()
            if disjoint:
                try:
                    audit = audit_environmental_decorrelation(
                        background,
                        block_labels,
                        target_process=target,
                        competitor_process="+".join(coalition),
                        target_predictors=target_predictors,
                        competitor_predictors=competitor_predictors,
                        degree=int(degree),
                        ridge_alpha=float(ridge_alpha),
                        material_r2_drop=float(material_r2_drop),
                        sem_multiplier=float(sem_multiplier),
                        minimum_complete_rows_per_block=int(minimum_complete_rows_per_block),
                    )
                    finite = audit.block_table.loc[audit.block_table["complete"].astype(bool), "heldout_r2"].to_numpy(float)
                    finite = finite[np.isfinite(finite)]
                    n_complete = int(len(finite))
                    if n_complete:
                        median_r2 = float(np.median(finite))
                    separating = tuple(int(x) for x in audit.separating_blocks)
                except ValueError:
                    pass
            eligible = bool(
                disjoint
                and n_complete >= int(minimum_complete_blocks)
                and np.isfinite(median_r2)
                and median_r2 > float(minimum_median_heldout_r2)
            )
            rows.append({
                "target_process": target,
                "coalition_processes": "+".join(coalition),
                "coalition_size": int(size),
                "coalition_predictors": ",".join(competitor_predictors),
                "structurally_disjoint": bool(disjoint),
                "n_complete_blocks": n_complete,
                "median_heldout_r2": median_r2,
                "eligible_coalition": eligible,
                "minimal_eligible_coalition": False,
                "n_separating_blocks": int(len(separating)) if eligible else 0,
                "separating_blocks": ",".join(str(x) for x in separating) if eligible else "",
            })

    result = pd.DataFrame(rows, columns=COALITION_COLUMNS)
    eligible_sets = {
        frozenset(str(row.coalition_processes).split("+"))
        for row in result.itertuples(index=False)
        if bool(row.eligible_coalition)
    }
    minimal: list[bool] = []
    for row in result.itertuples(index=False):
        if not bool(row.eligible_coalition):
            minimal.append(False)
            continue
        current = frozenset(str(row.coalition_processes).split("+"))
        has_eligible_proper_subset = any(other < current for other in eligible_sets)
        minimal.append(not has_eligible_proper_subset)
    result["minimal_eligible_coalition"] = minimal
    return result
