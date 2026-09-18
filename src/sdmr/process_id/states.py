"""Abstention-aware process-state classification for SDMR v3."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


PROCESS_STATES = (
    "replaceable",
    "contributory",
    "required",
    "unresolved",
    "unavailable",
)

_REQUIRED_COLUMNS = (
    "route",
    "complete",
    "full_adequate",
    "knockout_adequate",
    "delta_mean",
    "delta_sem",
)


def _require_boolean_column(values: pd.Series, *, name: str) -> pd.Series:
    if values.isna().any():
        raise ValueError(f"{name} must contain explicit boolean values")
    if not all(isinstance(value, (bool, np.bool_)) for value in values.tolist()):
        raise ValueError(f"{name} must contain only boolean values")
    return values.astype(bool)


def classify_process_state(
    evidence: pd.DataFrame,
    *,
    margin: float,
    adequacy_floor: float,
    sem_multiplier: float = 1.0,
) -> str:
    """Classify one process from matched full-versus-knockout route evidence.

    delta_mean uses a loss convention: positive values mean that removing
    the process made ecological reconstruction worse. A process is called
    replaceable only when at least one adequate process-free route has an
    upper uncertainty bound no larger than margin. Positive process states
    require positive evidence that every declared route is meaningfully
    worse; incomplete or interval-indeterminate evidence therefore abstains.

    adequacy_floor is part of the public scientific contract. Route-level
    adequacy is supplied explicitly in the evidence table so this function
    validates, but does not recompute, that threshold decision.
    """

    if not isinstance(evidence, pd.DataFrame) or evidence.empty:
        raise ValueError("evidence must be a non-empty pandas DataFrame")

    missing = [column for column in _REQUIRED_COLUMNS if column not in evidence.columns]
    if missing:
        raise KeyError(f"evidence missing columns: {missing}")

    margin = float(margin)
    adequacy_floor = float(adequacy_floor)
    sem_multiplier = float(sem_multiplier)
    if not math.isfinite(margin) or margin < 0:
        raise ValueError("margin must be finite and non-negative")
    if not math.isfinite(adequacy_floor):
        raise ValueError("adequacy_floor must be finite")
    if not math.isfinite(sem_multiplier) or sem_multiplier < 0:
        raise ValueError("sem_multiplier must be finite and non-negative")

    data = evidence.loc[:, list(_REQUIRED_COLUMNS)].copy()
    if data["route"].isna().any():
        raise ValueError("route values must be non-empty and unique")
    data["route"] = data["route"].astype(str).str.strip()
    if data["route"].eq("").any():
        raise ValueError("route values must be non-empty and unique")
    if data["route"].duplicated().any():
        raise ValueError("route values must be unique")

    for column in ("complete", "full_adequate", "knockout_adequate"):
        data[column] = _require_boolean_column(data[column], name=column)

    complete = data.loc[data["complete"]].copy()
    if complete.empty:
        return "unresolved"

    delta_mean = pd.to_numeric(complete["delta_mean"], errors="coerce")
    delta_sem = pd.to_numeric(complete["delta_sem"], errors="coerce")
    if not np.isfinite(delta_mean.to_numpy(float)).all():
        raise ValueError("complete rows require finite delta_mean values")
    if not np.isfinite(delta_sem.to_numpy(float)).all():
        raise ValueError("complete rows require finite delta_sem values")
    if (delta_sem < 0).any():
        raise ValueError("delta_sem must be non-negative on complete rows")

    if (~complete["full_adequate"]).any():
        return "unavailable"

    lower = delta_mean - sem_multiplier * delta_sem
    upper = delta_mean + sem_multiplier * delta_sem

    noninferior_witness = complete["knockout_adequate"] & (upper <= margin)
    if bool(noninferior_witness.any()):
        return "replaceable"

    if (~data["complete"]).any():
        return "unresolved"

    if bool((lower <= margin).any()):
        return "unresolved"

    if bool(complete["knockout_adequate"].any()):
        return "contributory"
    return "required"


def apply_identical_closure_abstention(
    states: pd.DataFrame,
    *,
    process_col: str = "process",
    state_col: str = "state",
    closure_col: str = "closure_predictors",
    reason_col: str = "reason",
) -> pd.DataFrame:
    """Abstain from positive unique attribution for literally identical closures."""

    required = {process_col, state_col, closure_col, reason_col}
    missing = sorted(required - set(states.columns))
    if missing:
        raise KeyError(f"state table missing columns: {missing}")
    out = states.copy(deep=True)
    positive = {"contributory", "required"}
    for closure, group in out.groupby(closure_col, sort=False):
        if not str(closure).strip() or len(group) < 2:
            continue
        positive_idx = group.index[group[state_col].isin(positive)]
        if len(positive_idx) < 2:
            continue
        out.loc[positive_idx, state_col] = "unresolved"
        out.loc[positive_idx, reason_col] = "identical_shared_carrier_closure"
    return out
