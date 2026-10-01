"""Development-only finite split-geometry diagnostic for SDMR v3."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import pandas as pd

from ..evidence import evaluate_occurrence_processes
from .occurrence_oracle import evaluate_occurrence_oracle_states
from .worlds import simulate_process_world


_POSITIVE = {"contributory", "required"}
_ALLOWED_WORLDS = {"unique_process", "interaction", "geographic_shift"}


@dataclass(frozen=True)
class FiniteSplitGeometryAuditResult:
    states: pd.DataFrame
    metrics: pd.DataFrame


def summarize_split_geometry(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize HGB recovery among ODO-positive cells by inner split geometry."""

    required = {
        "split_mode",
        "finite_state",
        "full_log_score",
        "delta_mean",
        "delta_sem",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"split audit rows missing columns: {missing}")
    if rows.empty:
        raise ValueError("split audit rows must be non-empty")

    result = []
    for split_mode, group in rows.groupby("split_mode", sort=True):
        positive = group["finite_state"].isin(_POSITIVE)
        unavailable = group["finite_state"].eq("unavailable")
        unresolved = group["finite_state"].eq("unresolved")
        replaceable = group["finite_state"].eq("replaceable")
        result.append(
            {
                "split_mode": str(split_mode),
                "positive_recovery": float(positive.mean()),
                "unavailable_rate": float(unavailable.mean()),
                "unresolved_rate": float(unresolved.mean()),
                "replaceable_rate": float(replaceable.mean()),
                "mean_full_log_score": float(
                    pd.to_numeric(group["full_log_score"]).mean()
                ),
                "mean_delta": float(pd.to_numeric(group["delta_mean"]).mean()),
                "mean_delta_sem": float(pd.to_numeric(group["delta_sem"]).mean()),
                "n_rows": int(len(group)),
            }
        )
    return pd.DataFrame(result)


def run_finite_split_geometry_audit(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = ("unique_process", "interaction", "geographic_shift"),
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
    split_modes: Sequence[str] = ("spatial", "random_cell"),
    margin: float = 0.01,
    sem_multiplier: float = 1.0,
    adequacy_floor: float = -0.75,
    odo_approximation_tolerance: float = 0.01,
    logistic_C: float = 1.0,
) -> FiniteSplitGeometryAuditResult:
    """Compare HGB Stage-P evidence under spatial and random-cell cross-fitting."""

    seed_tuple = tuple(int(x) for x in seeds)
    world_tuple = tuple(str(x) for x in worlds)
    split_tuple = tuple(str(x) for x in split_modes)

    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be non-empty and unique")
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be non-empty and unique")
    unknown_worlds = sorted(set(world_tuple) - _ALLOWED_WORLDS)
    if unknown_worlds:
        raise ValueError(f"split audit supports only ODO-positive worlds: {unknown_worlds}")
    if split_tuple != ("spatial", "random_cell"):
        raise ValueError("split_modes must be exactly spatial, random_cell")

    frames: list[pd.DataFrame] = []
    for world_name in world_tuple:
        for seed in seed_tuple:
            world = simulate_process_world(
                world_name,
                seed=seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            odo = evaluate_occurrence_oracle_states(
                world,
                n_splits=int(n_splits),
                margin=float(margin),
                sem_multiplier=float(sem_multiplier),
                adequacy_floor=float(adequacy_floor),
                approximation_tolerance=float(odo_approximation_tolerance),
                split_mode="random",
            ).states
            positive = odo.loc[odo["state"].isin(_POSITIVE), ["process", "state"]].copy()
            if positive.empty:
                continue
            positive = positive.rename(columns={"state": "odo_state"})
            focused = replace(
                world,
                process_universe=tuple(positive["process"].astype(str)),
            )

            for split_mode in split_tuple:
                finite = evaluate_occurrence_processes(
                    focused,
                    n_splits=int(n_splits),
                    margin=float(margin),
                    adequacy_floor=float(adequacy_floor),
                    sem_multiplier=float(sem_multiplier),
                    C=float(logistic_C),
                    learner="hgb",
                    split_mode=split_mode,
                ).states
                merged = positive.merge(
                    finite,
                    on="process",
                    how="left",
                    validate="one_to_one",
                ).rename(columns={"state": "finite_state"})
                merged.insert(0, "learner", "hgb")
                merged.insert(0, "seed", int(seed))
                merged.insert(0, "world", world_name)
                frames.append(merged)

    if not frames:
        raise ValueError("split audit produced no ODO-positive cells")
    states = pd.concat(frames, ignore_index=True)
    return FiniteSplitGeometryAuditResult(
        states=states,
        metrics=summarize_split_geometry(states),
    )
