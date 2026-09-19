"""Adapter from the existing truth-surface oracle to SDMR v3 process states."""
from __future__ import annotations

import pandas as pd

from ...oracle_process_identifiability import (
    ORACLE_CONTESTED,
    ORACLE_CONTRIBUTORY,
    ORACLE_REPLACEABLE,
    ORACLE_REQUIRED,
    ORACLE_UNAVAILABLE,
    oracle_process_identifiability,
)
from ...process_information_closure import process_information_closure
from ..states import apply_identical_closure_abstention
from .worlds import KnownTruthWorld


_ORACLE_STATE_MAP = {
    ORACLE_REPLACEABLE: "replaceable",
    ORACLE_CONTRIBUTORY: "contributory",
    ORACLE_REQUIRED: "required",
    ORACLE_CONTESTED: "unresolved",
    ORACLE_UNAVAILABLE: "unavailable",
}


def map_oracle_state(raw_state: str) -> str:
    """Map the historical oracle labels into the SDMR v3 state space."""

    try:
        return _ORACLE_STATE_MAP[str(raw_state)]
    except KeyError as exc:
        raise ValueError(f"unknown oracle state: {raw_state!r}") from exc


def apply_shared_carrier_abstention(states: pd.DataFrame) -> pd.DataFrame:
    """Compatibility wrapper for the generic identical-closure abstention rule."""

    return apply_identical_closure_abstention(states)


def evaluate_oracle_states(
    world: KnownTruthWorld,
    *,
    n_splits: int = 5,
    margin: float = 0.02,
    sem_multiplier: float = 1.0,
    baseline_r2_floor: float = 0.80,
    required_r2_ceiling: float = 0.0,
) -> pd.DataFrame:
    """Evaluate representation-conditioned truth-surface process states."""

    result = oracle_process_identifiability(
        world.environment,
        world.true_suitability,
        world.spatial_groups,
        world.process_registry,
        predictor_universe=world.predictor_universe,
        process_universe=world.process_universe,
        n_splits=int(n_splits),
        relative_loss_margin=float(margin),
        sem_multiplier=float(sem_multiplier),
        baseline_r2_floor=float(baseline_r2_floor),
        required_r2_ceiling=float(required_r2_ceiling),
    )

    rows = []
    summary = result.process_summary.copy()
    for process in world.process_universe:
        match = summary.loc[summary["process"].astype(str).eq(str(process))]
        if len(match) != 1:
            raise ValueError(f"oracle returned {len(match)} rows for process {process!r}")
        raw = str(match.iloc[0]["oracle_status"])
        closure = process_information_closure(world.process_registry, str(process))
        rows.append({
            "process": str(process),
            "state": map_oracle_state(raw),
            "oracle_raw_state": raw,
            "closure_predictors": ",".join(closure),
            "reason": raw,
            "selection_receipt": result.selection_receipt,
        })
    return apply_shared_carrier_abstention(pd.DataFrame(rows))
