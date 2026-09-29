"""Freeze many-to-many process-information registries for SDMR v3."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import pandas as pd

from ..process_information_closure import normalize_process_information_registry
from .taxonomy import DEFAULT_PLANT_PROCESSES


@dataclass(frozen=True)
class FrozenProcessRegistry:
    table: pd.DataFrame
    processes: tuple[str, ...]
    predictors: tuple[str, ...]
    digest: str


def _unique_nonempty(values, *, name):
    result = tuple(str(value).strip() for value in values)
    if not result or any(not value for value in result):
        raise ValueError(f"{name} must contain non-empty values")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique values")
    return result


def freeze_process_registry(
    registry: pd.DataFrame,
    *,
    predictor_universe,
    process_universe=DEFAULT_PLANT_PROCESSES,
) -> FrozenProcessRegistry:
    """Normalize and fingerprint a frozen process-information registry."""

    processes = _unique_nonempty(process_universe, name="process_universe")
    predictors = _unique_nonempty(predictor_universe, name="predictor_universe")
    normalized = normalize_process_information_registry(
        registry.copy(deep=True),
        process_universe=processes,
        predictor_universe=predictors,
    )
    canonical = normalized.loc[:, ["predictor", "process", "role"]].copy()
    canonical = canonical.sort_values(
        ["process", "role", "predictor"], kind="mergesort"
    ).reset_index(drop=True)
    payload = (
        "processes=" + "|".join(processes) + "\n"
        + "predictors=" + "|".join(predictors) + "\n"
        + canonical.to_csv(index=False)
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return FrozenProcessRegistry(
        table=canonical,
        processes=processes,
        predictors=predictors,
        digest=digest,
    )
