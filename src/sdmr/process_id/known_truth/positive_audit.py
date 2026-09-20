"""Diagnostic audit for SDMR v3 target-positive development cells.

This module never changes process states.  It only classifies the evidence
boundary that explains an already-computed occurrence-side state.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd


_POSITIVE_TARGETS = {"contributory", "required"}
_INTERVAL_REASON = "interval_process_challenge"


def _finite(value, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def classify_positive_boundary(
    row: pd.Series,
    *,
    margin: float,
    adequacy_floor: float,
    sem_multiplier: float = 1.0,
) -> str:
    """Explain why one target-positive process cell did or did not sharpen.

    Classification is diagnostic only.  Existing explicit refusal reasons are
    preserved.  Otherwise absolute full-model adequacy is checked before
    relative full-versus-knockout evidence.
    """

    margin = _finite(margin, name="margin")
    adequacy_floor = _finite(adequacy_floor, name="adequacy_floor")
    sem_multiplier = _finite(sem_multiplier, name="sem_multiplier")
    if margin < 0:
        raise ValueError("margin must be non-negative")
    if sem_multiplier < 0:
        raise ValueError("sem_multiplier must be non-negative")

    reason = str(row.get("reason", "")).strip()
    if reason and reason != _INTERVAL_REASON:
        return reason

    if not bool(row.get("complete", True)):
        return "incomplete_evidence"

    full = _finite(row["full_log_score"], name="full_log_score")
    knockout = _finite(row["knockout_log_score"], name="knockout_log_score")
    delta = _finite(row["delta_mean"], name="delta_mean")
    sem = _finite(row["delta_sem"], name="delta_sem")
    if sem < 0:
        raise ValueError("delta_sem must be non-negative")

    if full < adequacy_floor:
        return "full_inadequate"

    lower = delta - sem_multiplier * sem
    upper = delta + sem_multiplier * sem

    if upper <= margin:
        return "process_free_noninferior_witness"
    if lower <= margin:
        return "interval_indeterminate"
    if knockout < adequacy_floor:
        return "positive_required_evidence"
    return "positive_contribution_evidence"


def _validate_targets(targets: pd.DataFrame) -> pd.DataFrame:
    required = {"process", "expected_state"}
    missing = sorted(required - set(targets.columns))
    if missing:
        raise KeyError(f"target table missing columns: {missing}")
    data = targets.copy(deep=True)
    if data["process"].isna().any():
        raise ValueError("target process values must not be missing")
    data["process"] = data["process"].astype(str)
    if data["process"].duplicated().any():
        raise ValueError("target table must contain one row per process")
    return data


def build_positive_evidence_audit(
    targets: pd.DataFrame,
    states_by_learner: Mapping[str, pd.DataFrame],
    evidence_by_learner: Mapping[str, pd.DataFrame],
    *,
    margin: float,
    adequacy_floor: float,
    sem_multiplier: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build summary and fold-level diagnostics for target-positive processes."""

    target = _validate_targets(targets)
    target = target.loc[target["expected_state"].astype(str).isin(_POSITIVE_TARGETS)].copy()
    if target.empty:
        return pd.DataFrame(), pd.DataFrame()

    learners = tuple(str(name) for name in states_by_learner)
    if not learners:
        raise ValueError("states_by_learner must be non-empty")
    if set(learners) != {str(name) for name in evidence_by_learner}:
        raise ValueError("state and evidence learner keys must match exactly")

    summary_rows: list[dict[str, object]] = []
    fold_frames: list[pd.DataFrame] = []

    for learner in learners:
        states = states_by_learner[learner].copy(deep=True)
        evidence = evidence_by_learner[learner].copy(deep=True)
        state_required = {
            "process", "state", "reason", "complete", "full_log_score",
            "knockout_log_score", "delta_mean", "delta_sem",
        }
        missing_states = sorted(state_required - set(states.columns))
        if missing_states:
            raise KeyError(f"state table for {learner!r} missing columns: {missing_states}")
        if states["process"].astype(str).duplicated().any():
            raise ValueError(f"state table for {learner!r} must contain one row per process")

        fold_required = {
            "process", "fold", "route", "complete", "full_log_score",
            "knockout_log_score", "delta",
        }
        missing_folds = sorted(fold_required - set(evidence.columns))
        if missing_folds:
            raise KeyError(f"evidence table for {learner!r} missing columns: {missing_folds}")

        merged = target.loc[:, ["process", "expected_state"]].merge(
            states, on="process", how="left", validate="one_to_one"
        )
        if merged["state"].isna().any():
            missing_processes = merged.loc[merged["state"].isna(), "process"].astype(str).tolist()
            raise ValueError(f"state table for {learner!r} missing target processes: {missing_processes}")

        for _, row in merged.iterrows():
            lower = float(row["delta_mean"]) - float(sem_multiplier) * float(row["delta_sem"])
            upper = float(row["delta_mean"]) + float(sem_multiplier) * float(row["delta_sem"])
            summary_rows.append({
                "learner": learner,
                "process": str(row["process"]),
                "target_state": str(row["expected_state"]),
                "occurrence_state": str(row["state"]),
                "reason": str(row["reason"]),
                "complete": bool(row["complete"]),
                "full_log_score": float(row["full_log_score"]),
                "knockout_log_score": float(row["knockout_log_score"]),
                "delta_mean": float(row["delta_mean"]),
                "delta_sem": float(row["delta_sem"]),
                "lower_delta": lower,
                "upper_delta": upper,
                "full_adequate": bool(float(row["full_log_score"]) >= float(adequacy_floor)),
                "knockout_adequate": bool(float(row["knockout_log_score"]) >= float(adequacy_floor)),
                "diagnostic_boundary": classify_positive_boundary(
                    row,
                    margin=margin,
                    adequacy_floor=adequacy_floor,
                    sem_multiplier=sem_multiplier,
                ),
            })

        selected = evidence.loc[
            evidence["process"].astype(str).isin(set(target["process"].astype(str)))
        ].copy()
        selected.insert(0, "learner", learner)
        fold_frames.append(selected)

    summary = pd.DataFrame(summary_rows)
    folds = pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame()
    return summary, folds


from dataclasses import dataclass
from collections.abc import Sequence

from .development import expected_occurrence_targets
from .oracle import evaluate_oracle_states
from .worlds import simulate_process_world
from ..evidence import evaluate_occurrence_processes


@dataclass(frozen=True)
class PositiveEvidenceAuditResult:
    summary: pd.DataFrame
    folds: pd.DataFrame
    boundary_counts: pd.DataFrame


def run_positive_evidence_audit(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = ("unique_process", "interaction", "geographic_shift"),
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
) -> PositiveEvidenceAuditResult:
    """Run the burned-development positive-target audit for two learner routes."""

    seed_tuple = tuple(int(seed) for seed in seeds)
    world_tuple = tuple(str(world) for world in worlds)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be a non-empty unique sequence")
    allowed_worlds = {"unique_process", "interaction", "geographic_shift"}
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be a non-empty unique sequence")
    unknown = sorted(set(world_tuple) - allowed_worlds)
    if unknown:
        raise ValueError(f"positive audit only supports target-positive worlds: {unknown}")

    summary_frames: list[pd.DataFrame] = []
    fold_frames: list[pd.DataFrame] = []
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
            targets = expected_occurrence_targets(world, oracle)
            states_by_learner: dict[str, pd.DataFrame] = {}
            evidence_by_learner: dict[str, pd.DataFrame] = {}
            for learner in ("linear", "quadratic"):
                evaluation = evaluate_occurrence_processes(
                    world,
                    n_splits=int(n_splits),
                    margin=float(occurrence_margin),
                    adequacy_floor=float(occurrence_adequacy_floor),
                    sem_multiplier=float(occurrence_sem_multiplier),
                    C=float(logistic_C),
                    learner=learner,
                )
                states_by_learner[learner] = evaluation.states
                evidence_by_learner[learner] = evaluation.evidence

            summary, folds = build_positive_evidence_audit(
                targets,
                states_by_learner,
                evidence_by_learner,
                margin=float(occurrence_margin),
                adequacy_floor=float(occurrence_adequacy_floor),
                sem_multiplier=float(occurrence_sem_multiplier),
            )
            if not summary.empty:
                summary.insert(0, "seed", int(seed))
                summary.insert(0, "world", world_name)
                summary_frames.append(summary)
            if not folds.empty:
                folds.insert(0, "seed", int(seed))
                folds.insert(0, "world", world_name)
                fold_frames.append(folds)

    summary_all = (
        pd.concat(summary_frames, ignore_index=True)
        if summary_frames
        else pd.DataFrame()
    )
    folds_all = (
        pd.concat(fold_frames, ignore_index=True)
        if fold_frames
        else pd.DataFrame()
    )
    if summary_all.empty:
        boundary_counts = pd.DataFrame(
            columns=["learner", "diagnostic_boundary", "count"]
        )
    else:
        boundary_counts = (
            summary_all.groupby(["learner", "diagnostic_boundary"], dropna=False)
            .size()
            .rename("count")
            .reset_index()
            .sort_values(["learner", "diagnostic_boundary"], kind="mergesort")
            .reset_index(drop=True)
        )
    return PositiveEvidenceAuditResult(
        summary=summary_all,
        folds=folds_all,
        boundary_counts=boundary_counts,
    )
