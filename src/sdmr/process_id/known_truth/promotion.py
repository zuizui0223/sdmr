"""Strict KT-A through KT-F promotion gate for SDMR v3."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from .worlds import KNOWN_TRUTH_WORLDS


@dataclass(frozen=True)
class KnownTruthGateDecision:
    passed: bool
    gates: dict[str, bool]
    metrics: dict[str, float]
    reasons: tuple[str, ...]


def _probability(value, *, name):
    x = float(value)
    if not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return x


def _bool_series(values: pd.Series, *, name: str) -> pd.Series:
    if values.isna().any() or not all(isinstance(value, (bool, np.bool_)) for value in values.tolist()):
        raise ValueError(f"{name} must contain explicit boolean values")
    return values.astype(bool)


def evaluate_known_truth_gate(
    comparison: pd.DataFrame,
    world_summary: pd.DataFrame,
    *,
    min_positive_recovery: float,
    max_false_positive: float,
    max_overresolution: float,
    max_false_unique_attribution: float,
    min_sealed_transfer: float,
) -> KnownTruthGateDecision:
    """Evaluate the known-truth programme by strict conjunction."""

    thresholds = {
        "min_positive_recovery": _probability(min_positive_recovery, name="min_positive_recovery"),
        "max_false_positive": _probability(max_false_positive, name="max_false_positive"),
        "max_overresolution": _probability(max_overresolution, name="max_overresolution"),
        "max_false_unique_attribution": _probability(
            max_false_unique_attribution, name="max_false_unique_attribution"
        ),
        "min_sealed_transfer": _probability(min_sealed_transfer, name="min_sealed_transfer"),
    }

    required_comparison = {
        "world", "seed", "process", "target_state", "occurrence_state",
        "target_positive", "occurrence_positive", "false_positive",
        "overresolved", "unique_attribution_forbidden",
    }
    missing = sorted(required_comparison - set(comparison.columns))
    if missing:
        raise KeyError(f"comparison missing columns: {missing}")
    if comparison.duplicated(["world", "seed", "process"]).any():
        raise ValueError("comparison contains duplicate world/seed/process cells")

    required_summary = {"world", "seed", "oracle_valid", "sealed_transfer_ok"}
    missing_summary = sorted(required_summary - set(world_summary.columns))
    if missing_summary:
        raise KeyError(f"world_summary missing columns: {missing_summary}")
    if world_summary.duplicated(["world", "seed"]).any():
        raise ValueError("world_summary contains duplicate world/seed rows")
    present_worlds = set(world_summary["world"].astype(str))
    required_worlds = set(KNOWN_TRUTH_WORLDS)
    if present_worlds != required_worlds:
        missing_worlds = sorted(required_worlds - present_worlds)
        extra_worlds = sorted(present_worlds - required_worlds)
        raise ValueError(
            "world_summary must contain all and only required known-truth worlds; "
            f"missing={missing_worlds}, extra={extra_worlds}"
        )

    oracle_valid = _bool_series(world_summary["oracle_valid"], name="oracle_valid")
    sealed_transfer = _bool_series(
        world_summary["sealed_transfer_ok"], name="sealed_transfer_ok"
    )

    positive = comparison.loc[comparison["target_state"].isin({"contributory", "required"})]
    replaceable = comparison.loc[comparison["target_state"].eq("replaceable")]
    unresolved = comparison.loc[comparison["target_state"].eq("unresolved")]
    if positive.empty:
        raise ValueError("known-truth comparison has no positive target cells")
    if replaceable.empty:
        raise ValueError("known-truth comparison has no replaceable target cells")
    if unresolved.empty:
        raise ValueError("known-truth comparison has no unresolved target cells")

    positive_recovery = float(positive["occurrence_state"].isin({"contributory", "required"}).mean())
    false_positive_rate = float(replaceable["occurrence_state"].isin({"contributory", "required"}).mean())
    overresolution_rate = float(unresolved["occurrence_state"].isin({"replaceable", "contributory", "required"}).mean())

    forbidden = comparison.loc[comparison["unique_attribution_forbidden"].astype(bool)].copy()
    false_unique_flags = []
    if not forbidden.empty:
        for _, group in forbidden.groupby(["world", "seed"], sort=False):
            if len(group) < 2:
                raise ValueError("unique-attribution-forbidden groups require at least two process cells")
            n_positive = int(group["occurrence_state"].isin({"contributory", "required"}).sum())
            false_unique_flags.append(n_positive == 1)
    if not false_unique_flags:
        raise ValueError("known-truth comparison has no unique-attribution boundary groups")
    false_unique_rate = float(np.mean(false_unique_flags))
    sealed_transfer_rate = float(sealed_transfer.mean())

    metrics = {
        "positive_recovery": positive_recovery,
        "false_positive_rate": false_positive_rate,
        "overresolution_rate": overresolution_rate,
        "false_unique_attribution_rate": false_unique_rate,
        "sealed_transfer_rate": sealed_transfer_rate,
        "n_unavailable_cells": float(comparison["target_state"].eq("unavailable").sum()),
    }
    gates = {
        "KT-A": bool(oracle_valid.all()),
        "KT-B": positive_recovery >= thresholds["min_positive_recovery"],
        "KT-C": false_positive_rate <= thresholds["max_false_positive"],
        "KT-D": overresolution_rate <= thresholds["max_overresolution"],
        "KT-E": false_unique_rate <= thresholds["max_false_unique_attribution"],
        "KT-F": sealed_transfer_rate >= thresholds["min_sealed_transfer"],
    }
    reasons = tuple(gate for gate, passed in gates.items() if not passed)
    return KnownTruthGateDecision(
        passed=bool(all(gates.values())),
        gates=gates,
        metrics=metrics,
        reasons=reasons,
    )
