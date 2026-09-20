"""Burned-development audit across truth, observation-distribution, and finite states."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .identifiability_crosswalk import build_identifiability_crosswalk
from .occurrence_oracle import evaluate_occurrence_oracle_states
from .oracle import evaluate_oracle_states
from .worlds import KNOWN_TRUTH_WORLDS, simulate_process_world
from ..evidence import evaluate_occurrence_processes


_POSITIVE = {"contributory", "required"}


@dataclass(frozen=True)
class OccurrenceOracleAuditResult:
    truth_states: pd.DataFrame
    occurrence_oracle_states: pd.DataFrame
    occurrence_oracle_evidence: pd.DataFrame
    finite_states: pd.DataFrame
    crosswalk: pd.DataFrame
    metrics: dict[str, object]
    by_world: pd.DataFrame
    by_process: pd.DataFrame


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return float("nan")
    return float(numerator / denominator)


def summarize_occurrence_oracle_crosswalk(
    crosswalk: pd.DataFrame,
    occurrence_oracle_states: pd.DataFrame,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    """Summarize contraction and finite recovery using distribution-positive denominator."""

    required = {
        "world", "seed", "process", "learner", "truth_state", "distribution_state",
        "finite_state", "truth_positive", "distribution_positive", "finite_positive",
        "truth_positive_but_distribution_not_positive",
        "finite_false_negative_given_distribution_positive",
    }
    missing = sorted(required - set(crosswalk.columns))
    if missing:
        raise KeyError(f"crosswalk missing columns: {missing}")
    oracle_required = {"world", "seed", "process", "state", "full_numerically_adequate"}
    missing_oracle = sorted(oracle_required - set(occurrence_oracle_states.columns))
    if missing_oracle:
        raise KeyError(f"occurrence oracle states missing columns: {missing_oracle}")

    if crosswalk.duplicated(["world", "seed", "process", "learner"]).any():
        raise ValueError("crosswalk contains duplicate world/seed/process/learner cells")
    if occurrence_oracle_states.duplicated(["world", "seed", "process"]).any():
        raise ValueError("occurrence oracle states contain duplicate world/seed/process cells")

    unique = crosswalk.drop_duplicates(["world", "seed", "process"]).copy()
    truth_positive = unique["truth_positive"].astype(bool)
    distribution_positive = unique["distribution_positive"].astype(bool)
    truth_positive_count = int(truth_positive.sum())
    truth_and_distribution = int((truth_positive & distribution_positive).sum())

    recovery: dict[str, float] = {}
    false_positive: dict[str, float] = {}
    replaceable_false_positive: dict[str, float] = {}
    unresolved_overresolution: dict[str, float] = {}
    for learner, group in crosswalk.groupby("learner", sort=True):
        dist_positive = group["distribution_positive"].astype(bool)
        finite_positive = group["finite_positive"].astype(bool)
        recovery[str(learner)] = _rate(
            int((dist_positive & finite_positive).sum()), int(dist_positive.sum())
        )
        dist_nonpositive = ~dist_positive
        false_positive[str(learner)] = _rate(
            int((dist_nonpositive & finite_positive).sum()), int(dist_nonpositive.sum())
        )
        dist_replaceable = group["distribution_state"].astype(str).eq("replaceable")
        replaceable_false_positive[str(learner)] = _rate(
            int((dist_replaceable & finite_positive).sum()), int(dist_replaceable.sum())
        )
        dist_unresolved = group["distribution_state"].astype(str).eq("unresolved")
        finite_sharp = group["finite_state"].astype(str).isin(
            {"replaceable", "contributory", "required"}
        )
        unresolved_overresolution[str(learner)] = _rate(
            int((dist_unresolved & finite_sharp).sum()), int(dist_unresolved.sum())
        )

    metrics: dict[str, object] = {
        "truth_positive_cells": truth_positive_count,
        "distribution_positive_cells": int(distribution_positive.sum()),
        "truth_positive_distribution_positive_cells": truth_and_distribution,
        "truth_positive_distribution_positive_fraction": _rate(
            truth_and_distribution, truth_positive_count
        ),
        "truth_positive_but_distribution_not_positive_cells": int(
            unique["truth_positive_but_distribution_not_positive"].astype(bool).sum()
        ),
        "finite_positive_recovery": recovery,
        "finite_false_positive_rate": false_positive,
        "finite_false_positive_rate_on_replaceable": replaceable_false_positive,
        "finite_overresolution_rate_on_unresolved": unresolved_overresolution,
        "occurrence_oracle_unavailable_cells": int(
            occurrence_oracle_states["state"].astype(str).eq("unavailable").sum()
        ),
        "occurrence_oracle_numerically_inadequate_cells": int(
            (~occurrence_oracle_states["full_numerically_adequate"].astype(bool)).sum()
        ),
    }

    unique_oracle = unique.loc[:, [
        "world", "seed", "process", "truth_positive", "distribution_positive",
        "truth_positive_but_distribution_not_positive"
    ]].copy()
    unique_oracle = unique_oracle.merge(
        occurrence_oracle_states.loc[:, [
            "world", "seed", "process", "state", "full_numerically_adequate"
        ]],
        on=["world", "seed", "process"], how="left", validate="one_to_one"
    )

    def _group_summary(group: pd.DataFrame, key: str) -> dict[str, object]:
        tp = group["truth_positive"].astype(bool)
        dp = group["distribution_positive"].astype(bool)
        return {
            key: str(group.iloc[0][key]),
            "n_cells": int(len(group)),
            "truth_positive": int(tp.sum()),
            "distribution_positive": int(dp.sum()),
            "truth_positive_distribution_positive": int((tp & dp).sum()),
            "truth_positive_but_distribution_not_positive": int(
                group["truth_positive_but_distribution_not_positive"].astype(bool).sum()
            ),
            "occurrence_oracle_unavailable": int(group["state"].astype(str).eq("unavailable").sum()),
        }

    by_world = pd.DataFrame([
        _group_summary(group, "world")
        for _, group in unique_oracle.groupby("world", sort=True)
    ])
    by_process = pd.DataFrame([
        _group_summary(group, "process")
        for _, group in unique_oracle.groupby("process", sort=True)
    ])
    return metrics, by_world, by_process


def run_occurrence_oracle_audit(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = KNOWN_TRUTH_WORLDS,
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
    truth_margin: float = 0.02,
    truth_sem_multiplier: float = 1.0,
    truth_baseline_r2_floor: float = 0.70,
    truth_required_r2_ceiling: float = 0.0,
    occurrence_oracle_margin: float = 0.01,
    occurrence_oracle_sem_multiplier: float = 1.0,
    occurrence_oracle_adequacy_floor: float = -0.75,
    occurrence_oracle_approximation_tolerance: float = 0.01,
    finite_margin: float = 0.01,
    finite_sem_multiplier: float = 1.0,
    finite_adequacy_floor: float = -0.75,
    logistic_C: float = 1.0,
) -> OccurrenceOracleAuditResult:
    """Run all three identifiability levels on a frozen burned-development panel."""

    seed_tuple = tuple(int(seed) for seed in seeds)
    world_tuple = tuple(str(world) for world in worlds)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be a non-empty unique sequence")
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be a non-empty unique sequence")
    unknown = sorted(set(world_tuple) - set(KNOWN_TRUTH_WORLDS))
    if unknown:
        raise ValueError(f"unknown audit worlds: {unknown}")

    truth_frames: list[pd.DataFrame] = []
    distribution_frames: list[pd.DataFrame] = []
    distribution_evidence_frames: list[pd.DataFrame] = []
    finite_frames: list[pd.DataFrame] = []

    for seed in seed_tuple:
        for world_name in world_tuple:
            world = simulate_process_world(
                world_name, seed=seed, n_cells=int(n_cells),
                n_occurrences=int(n_occurrences), n_background=int(n_background)
            )
            truth = evaluate_oracle_states(
                world, n_splits=int(n_splits), margin=float(truth_margin),
                sem_multiplier=float(truth_sem_multiplier),
                baseline_r2_floor=float(truth_baseline_r2_floor),
                required_r2_ceiling=float(truth_required_r2_ceiling),
            ).copy()
            truth.insert(0, "seed", int(seed))
            truth.insert(0, "world", world_name)
            truth_frames.append(truth)

            distribution = evaluate_occurrence_oracle_states(
                world, n_splits=int(n_splits), margin=float(occurrence_oracle_margin),
                sem_multiplier=float(occurrence_oracle_sem_multiplier),
                adequacy_floor=float(occurrence_oracle_adequacy_floor),
                approximation_tolerance=float(occurrence_oracle_approximation_tolerance),
            )
            dist_states = distribution.states.copy()
            dist_states.insert(0, "seed", int(seed))
            dist_states.insert(0, "world", world_name)
            distribution_frames.append(dist_states)
            dist_evidence = distribution.evidence.copy()
            dist_evidence.insert(0, "seed", int(seed))
            dist_evidence.insert(0, "world", world_name)
            distribution_evidence_frames.append(dist_evidence)

            for learner in ("linear", "quadratic"):
                finite = evaluate_occurrence_processes(
                    world, n_splits=int(n_splits), margin=float(finite_margin),
                    adequacy_floor=float(finite_adequacy_floor),
                    sem_multiplier=float(finite_sem_multiplier), C=float(logistic_C),
                    learner=learner,
                ).states.copy()
                finite.insert(0, "learner", learner)
                finite.insert(0, "seed", int(seed))
                finite.insert(0, "world", world_name)
                finite_frames.append(finite)

    truth_states = pd.concat(truth_frames, ignore_index=True)
    occurrence_states = pd.concat(distribution_frames, ignore_index=True)
    occurrence_evidence = pd.concat(distribution_evidence_frames, ignore_index=True)
    finite_states = pd.concat(finite_frames, ignore_index=True)
    crosswalk = build_identifiability_crosswalk(
        truth_states.loc[:, ["world", "seed", "process", "state"]],
        occurrence_states.loc[:, ["world", "seed", "process", "state"]],
        finite_states.loc[:, ["world", "seed", "process", "learner", "state"]],
    )
    metrics, by_world, by_process = summarize_occurrence_oracle_crosswalk(
        crosswalk, occurrence_states
    )
    return OccurrenceOracleAuditResult(
        truth_states=truth_states, occurrence_oracle_states=occurrence_states,
        occurrence_oracle_evidence=occurrence_evidence, finite_states=finite_states,
        crosswalk=crosswalk, metrics=metrics, by_world=by_world, by_process=by_process,
    )
