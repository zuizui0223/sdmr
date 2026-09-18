"""Burned-seed development panel for SDMR v3 process identification."""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .benchmark import compare_oracle_and_occurrence
from .oracle import evaluate_oracle_states
from .worlds import KNOWN_TRUTH_WORLDS, KnownTruthWorld, simulate_process_world
from ..evidence import evaluate_occurrence_processes


@dataclass(frozen=True)
class DevelopmentPanelResult:
    comparison: pd.DataFrame
    world_summary: pd.DataFrame
    metrics: dict[str, float | int]
    state_confusion: pd.DataFrame
    process_summary: pd.DataFrame
    world_metrics: pd.DataFrame


def expected_occurrence_targets(
    world: KnownTruthWorld, oracle_states: pd.DataFrame
) -> pd.DataFrame:
    """Derive the occurrence-level target without using generating membership.

    The truth-surface oracle supplies the default target. Observation-architecture
    constraints may only make that target less resolved, never sharper.
    """

    required = {"process", "state"}
    missing = sorted(required - set(oracle_states.columns))
    if missing:
        raise KeyError(f"oracle state table missing columns: {missing}")
    if oracle_states["process"].astype(str).duplicated().any():
        raise ValueError("oracle state table must contain one row per process")

    out = oracle_states.copy(deep=True)
    out["expected_state"] = out["state"].astype(str)
    out["unique_attribution_forbidden"] = False

    unresolved = set(world.observation_unresolved_processes)
    if unresolved:
        out.loc[out["process"].astype(str).isin(unresolved), "expected_state"] = "unresolved"

    if world.name == "shared_carrier":
        mask = out["process"].astype(str).isin({"thermal", "water"})
        out.loc[mask, "unique_attribution_forbidden"] = True
    elif world.name == "interaction":
        mask = out["process"].astype(str).isin({"thermal", "water"})
        out.loc[mask, "unique_attribution_forbidden"] = True

    return out


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return float("nan")
    return float(numerator / denominator)


def summarize_development_comparison(
    comparison: pd.DataFrame,
) -> tuple[dict[str, float | int], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Summarize development diagnostics without making a promotion decision."""

    required = {
        "world", "seed", "process", "target_state", "occurrence_state",
        "unique_attribution_forbidden",
    }
    missing = sorted(required - set(comparison.columns))
    if missing:
        raise KeyError(f"development comparison missing columns: {missing}")
    data = comparison.copy(deep=True)
    if data.duplicated(["world", "seed", "process"]).any():
        raise ValueError("development comparison contains duplicate world/seed/process cells")

    positive = data["target_state"].isin({"contributory", "required"})
    positive_called = data["occurrence_state"].isin({"contributory", "required"})
    replaceable = data["target_state"].eq("replaceable")
    unresolved = data["target_state"].eq("unresolved")
    unavailable = data["target_state"].eq("unavailable")
    sharp = data["occurrence_state"].isin({"replaceable", "contributory", "required"})
    available = ~unavailable

    forbidden_group_flags: list[bool] = []
    forbidden = data.loc[data["unique_attribution_forbidden"].astype(bool)]
    for _, group in forbidden.groupby(["world", "seed"], sort=False):
        if len(group) < 2:
            raise ValueError("unique-attribution-forbidden groups require at least two process cells")
        n_positive = int(group["occurrence_state"].isin({"contributory", "required"}).sum())
        forbidden_group_flags.append(n_positive == 1)

    metrics: dict[str, float | int] = {
        "positive_recovery": _ratio(int((positive & positive_called).sum()), int(positive.sum())),
        "false_positive_rate": _ratio(int((replaceable & positive_called).sum()), int(replaceable.sum())),
        "overresolution_rate": _ratio(int((unresolved & sharp).sum()), int(unresolved.sum())),
        "exact_state_agreement": _ratio(
            int((available & data["target_state"].eq(data["occurrence_state"])).sum()),
            int(available.sum()),
        ),
        "unavailable_cell_count": int(unavailable.sum()),
        "false_unique_attribution_rate": (
            float(np.mean(forbidden_group_flags)) if forbidden_group_flags else float("nan")
        ),
        "n_cells": int(len(data)),
    }

    confusion = (
        data.groupby(["target_state", "occurrence_state"], dropna=False)
        .size()
        .rename("count")
        .reset_index()
        .sort_values(["target_state", "occurrence_state"], kind="mergesort")
        .reset_index(drop=True)
    )

    process_rows = []
    for process, group in data.groupby("process", sort=True):
        target_positive = group["target_state"].isin({"contributory", "required"})
        called_positive = group["occurrence_state"].isin({"contributory", "required"})
        target_replaceable = group["target_state"].eq("replaceable")
        process_rows.append({
            "process": str(process),
            "positive_recovery": _ratio(
                int((target_positive & called_positive).sum()), int(target_positive.sum())
            ),
            "false_positive_rate": _ratio(
                int((target_replaceable & called_positive).sum()), int(target_replaceable.sum())
            ),
            "n_cells": int(len(group)),
        })
    process_summary = pd.DataFrame(process_rows)

    world_rows = []
    for world, group in data.groupby("world", sort=True):
        eligible = ~group["target_state"].eq("unavailable")
        world_rows.append({
            "world": str(world),
            "exact_state_agreement": _ratio(
                int((eligible & group["target_state"].eq(group["occurrence_state"])).sum()),
                int(eligible.sum()),
            ),
            "n_cells": int(len(group)),
        })
    world_metrics = pd.DataFrame(world_rows)
    return metrics, confusion, process_summary, world_metrics


def _oracle_world_valid(world: KnownTruthWorld, oracle_states: pd.DataFrame) -> bool:
    states = oracle_states.set_index("process")["state"].astype(str)
    if world.name == "omitted_driver":
        return bool(states.eq("unavailable").all())
    if states.eq("unavailable").any():
        return False
    if world.name == "unique_process":
        return states.get("thermal") in {"contributory", "required"}
    if world.name == "redundant_representation":
        return states.get("thermal") == "replaceable"
    if world.name == "shared_carrier":
        return states.get("thermal") == "unresolved" and states.get("water") == "unresolved"
    if world.name == "null_correlated":
        return states.get("seasonality") == "replaceable"
    if world.name == "interaction":
        return states.get("thermal") in {"contributory", "required"} and states.get("water") in {"contributory", "required"}
    if world.name == "observation_confounded":
        return states.get("thermal") in {"contributory", "required", "unresolved"}
    if world.name == "geographic_shift":
        return states.get("thermal") in {"contributory", "required"}
    return False


def run_development_panel(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = KNOWN_TRUTH_WORLDS,
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
    oracle_margin: float = 0.02,
    oracle_sem_multiplier: float = 1.0,
    oracle_baseline_r2_floor: float = 0.70,
    oracle_required_r2_ceiling: float = 0.0,
    occurrence_margin: float = 0.01,
    occurrence_sem_multiplier: float = 1.0,
    occurrence_adequacy_floor: float = -0.75,
    logistic_C: float = 1.0,
) -> DevelopmentPanelResult:
    """Run the full burned development denominator deterministically."""

    seed_tuple = tuple(int(seed) for seed in seeds)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be a non-empty unique sequence")
    world_tuple = tuple(str(world) for world in worlds)
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be a non-empty unique sequence")
    unknown = sorted(set(world_tuple) - set(KNOWN_TRUTH_WORLDS))
    if unknown:
        raise ValueError(f"unknown development worlds: {unknown}")

    comparisons = []
    world_rows = []
    for seed in seed_tuple:
        for world_name in world_tuple:
            world = simulate_process_world(
                world_name,
                seed=seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            oracle = evaluate_oracle_states(
                world,
                n_splits=int(n_splits),
                margin=float(oracle_margin),
                sem_multiplier=float(oracle_sem_multiplier),
                baseline_r2_floor=float(oracle_baseline_r2_floor),
                required_r2_ceiling=float(oracle_required_r2_ceiling),
            )
            target = expected_occurrence_targets(world, oracle)
            occurrence = evaluate_occurrence_processes(
                world,
                n_splits=int(n_splits),
                margin=float(occurrence_margin),
                adequacy_floor=float(occurrence_adequacy_floor),
                sem_multiplier=float(occurrence_sem_multiplier),
                C=float(logistic_C),
            ).states
            target = target.copy()
            occurrence = occurrence.copy()
            for frame in (target, occurrence):
                frame.insert(0, "seed", int(seed))
                frame.insert(0, "world", world_name)
            comparison = compare_oracle_and_occurrence(target, occurrence)
            comparisons.append(comparison)
            world_rows.append({
                "world": world_name,
                "seed": int(seed),
                "oracle_valid": _oracle_world_valid(world, oracle),
                "n_oracle_unavailable": int(oracle["state"].eq("unavailable").sum()),
                "n_occurrence_unavailable": int(occurrence["state"].eq("unavailable").sum()),
            })

    comparison = pd.concat(comparisons, ignore_index=True)
    world_summary = pd.DataFrame(world_rows)
    metrics, confusion, process_summary, world_metrics = summarize_development_comparison(comparison)
    return DevelopmentPanelResult(
        comparison=comparison,
        world_summary=world_summary,
        metrics=metrics,
        state_confusion=confusion,
        process_summary=process_summary,
        world_metrics=world_metrics,
    )
