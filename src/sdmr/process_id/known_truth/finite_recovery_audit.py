"""Development-only finite-recovery capacity and power audit for SDMR v3."""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..evidence import evaluate_occurrence_processes
from .occurrence_oracle import evaluate_occurrence_oracle_states
from .resampling import resample_world_observations
from .worlds import KNOWN_TRUTH_WORLDS, simulate_process_world


_POSITIVE = {"contributory", "required"}
_SHARP = {"replaceable", "contributory", "required"}


@dataclass(frozen=True)
class FiniteRecoveryAuditResult:
    baseline_states: pd.DataFrame
    power_states: pd.DataFrame
    baseline_metrics: pd.DataFrame
    power_metrics: pd.DataFrame


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator > 0 else float("nan")


def summarize_baseline_against_odo(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize learner recovery and safety against frozen ODO states."""

    required = {"learner", "odo_state", "finite_state"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"baseline rows missing columns: {missing}")
    result = []
    for learner, group in rows.groupby("learner", sort=True):
        positive = group["odo_state"].isin(_POSITIVE)
        replaceable = group["odo_state"].eq("replaceable")
        unresolved = group["odo_state"].eq("unresolved")
        finite_positive = group["finite_state"].isin(_POSITIVE)
        finite_sharp = group["finite_state"].isin(_SHARP)
        finite_unavailable = group["finite_state"].eq("unavailable")
        result.append(
            {
                "learner": str(learner),
                "positive_recovery": _ratio(
                    int((positive & finite_positive).sum()), int(positive.sum())
                ),
                "false_positive_rate": _ratio(
                    int((replaceable & finite_positive).sum()), int(replaceable.sum())
                ),
                "overresolution_rate": _ratio(
                    int((unresolved & finite_sharp).sum()), int(unresolved.sum())
                ),
                "positive_unavailable_rate": _ratio(
                    int((positive & finite_unavailable).sum()), int(positive.sum())
                ),
                "n_positive": int(positive.sum()),
                "n_replaceable": int(replaceable.sum()),
                "n_unresolved": int(unresolved.sum()),
            }
        )
    return pd.DataFrame(result)


def summarize_hgb_power_curve(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize HGB recovery across sample-size multipliers."""

    required = {"multiplier", "finite_state", "delta_mean"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"power rows missing columns: {missing}")
    result = []
    for multiplier, group in rows.groupby("multiplier", sort=True):
        positive = group["finite_state"].isin(_POSITIVE)
        unresolved = group["finite_state"].eq("unresolved")
        replaceable = group["finite_state"].eq("replaceable")
        unavailable = group["finite_state"].eq("unavailable")
        result.append(
            {
                "multiplier": int(multiplier),
                "positive_recovery": float(positive.mean()),
                "unresolved_rate": float(unresolved.mean()),
                "replaceable_rate": float(replaceable.mean()),
                "unavailable_rate": float(unavailable.mean()),
                "mean_delta": float(pd.to_numeric(group["delta_mean"]).mean()),
                "mean_delta_sem": (
                    float(pd.to_numeric(group["delta_sem"]).mean())
                    if "delta_sem" in group.columns
                    else float("nan")
                ),
                "n_rows": int(len(group)),
            }
        )
    return pd.DataFrame(result)


def _sampling_seed(
    ecological_seed: int,
    world_index: int,
    multiplier: int,
    replicate: int,
) -> int:
    return (
        int(ecological_seed) * 100000
        + (int(world_index) + 1) * 1000
        + int(multiplier) * 100
        + int(replicate)
    )


def run_finite_recovery_audit(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = KNOWN_TRUTH_WORLDS,
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
    baseline_learners: Sequence[str] = ("linear", "quadratic", "hgb"),
    sample_multipliers: Sequence[int] = (1, 2, 4),
    sampling_replicates: Sequence[int] = (0, 1, 2),
    odo_margin: float = 0.01,
    odo_sem_multiplier: float = 1.0,
    odo_adequacy_floor: float = -0.75,
    odo_approximation_tolerance: float = 0.01,
    finite_margin: float = 0.01,
    finite_sem_multiplier: float = 1.0,
    finite_adequacy_floor: float = -0.75,
    logistic_C: float = 1.0,
) -> FiniteRecoveryAuditResult:
    """Run baseline learner comparison plus HGB sample-size power curve."""

    seed_tuple = tuple(int(x) for x in seeds)
    world_tuple = tuple(str(x) for x in worlds)
    learner_tuple = tuple(str(x) for x in baseline_learners)
    multiplier_tuple = tuple(int(x) for x in sample_multipliers)
    replicate_tuple = tuple(int(x) for x in sampling_replicates)

    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be non-empty and unique")
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be non-empty and unique")
    unknown_worlds = sorted(set(world_tuple) - set(KNOWN_TRUTH_WORLDS))
    if unknown_worlds:
        raise ValueError(f"unknown worlds: {unknown_worlds}")
    if not learner_tuple or len(set(learner_tuple)) != len(learner_tuple):
        raise ValueError("baseline_learners must be non-empty and unique")
    unknown_learners = sorted(set(learner_tuple) - {"linear", "quadratic", "hgb"})
    if unknown_learners:
        raise ValueError(f"unknown baseline learners: {unknown_learners}")
    if not multiplier_tuple or any(x <= 0 for x in multiplier_tuple):
        raise ValueError("sample_multipliers must be positive")
    if len(set(multiplier_tuple)) != len(multiplier_tuple):
        raise ValueError("sample_multipliers must be unique")
    if not replicate_tuple or len(set(replicate_tuple)) != len(replicate_tuple):
        raise ValueError("sampling_replicates must be non-empty and unique")

    baseline_frames: list[pd.DataFrame] = []
    power_frames: list[pd.DataFrame] = []

    for world_index, world_name in enumerate(world_tuple):
        for ecological_seed in seed_tuple:
            world = simulate_process_world(
                world_name,
                seed=ecological_seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            odo = evaluate_occurrence_oracle_states(
                world,
                n_splits=int(n_splits),
                margin=float(odo_margin),
                sem_multiplier=float(odo_sem_multiplier),
                adequacy_floor=float(odo_adequacy_floor),
                approximation_tolerance=float(odo_approximation_tolerance),
                split_mode="random",
            ).states
            odo_target = odo.loc[:, ["process", "state"]].rename(
                columns={"state": "odo_state"}
            )

            for learner in learner_tuple:
                finite = evaluate_occurrence_processes(
                    world,
                    n_splits=int(n_splits),
                    margin=float(finite_margin),
                    adequacy_floor=float(finite_adequacy_floor),
                    sem_multiplier=float(finite_sem_multiplier),
                    C=float(logistic_C),
                    learner=learner,
                ).states
                merged = odo_target.merge(
                    finite,
                    on="process",
                    how="left",
                    validate="one_to_one",
                )
                merged.insert(0, "learner", learner)
                merged.insert(0, "seed", int(ecological_seed))
                merged.insert(0, "world", world_name)
                merged = merged.rename(columns={"state": "finite_state"})
                baseline_frames.append(merged)

            positive_processes = tuple(
                odo.loc[odo["state"].isin(_POSITIVE), "process"].astype(str)
            )
            if not positive_processes:
                continue

            focused_world = replace(world, process_universe=positive_processes)
            positive_target = odo_target.loc[
                odo_target["process"].isin(positive_processes)
            ].copy()

            for multiplier in multiplier_tuple:
                for replicate in replicate_tuple:
                    sampling_seed = _sampling_seed(
                        ecological_seed, world_index, multiplier, replicate
                    )
                    sampled = resample_world_observations(
                        focused_world,
                        n_occurrences=int(n_occurrences) * int(multiplier),
                        n_background=int(n_background) * int(multiplier),
                        sampling_seed=sampling_seed,
                    )
                    finite = evaluate_occurrence_processes(
                        sampled,
                        n_splits=int(n_splits),
                        margin=float(finite_margin),
                        adequacy_floor=float(finite_adequacy_floor),
                        sem_multiplier=float(finite_sem_multiplier),
                        C=float(logistic_C),
                        learner="hgb",
                    ).states
                    merged = positive_target.merge(
                        finite,
                        on="process",
                        how="left",
                        validate="one_to_one",
                    )
                    merged = merged.rename(columns={"state": "finite_state"})
                    merged.insert(0, "learner", "hgb")
                    merged.insert(0, "replicate", int(replicate))
                    merged.insert(0, "multiplier", int(multiplier))
                    merged.insert(0, "seed", int(ecological_seed))
                    merged.insert(0, "world", world_name)
                    power_frames.append(merged)

    baseline_states = (
        pd.concat(baseline_frames, ignore_index=True)
        if baseline_frames
        else pd.DataFrame()
    )
    power_states = (
        pd.concat(power_frames, ignore_index=True)
        if power_frames
        else pd.DataFrame()
    )
    return FiniteRecoveryAuditResult(
        baseline_states=baseline_states,
        power_states=power_states,
        baseline_metrics=summarize_baseline_against_odo(baseline_states),
        power_metrics=summarize_hgb_power_curve(power_states),
    )
