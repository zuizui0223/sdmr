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
