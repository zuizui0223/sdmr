"""Build a leakage-safe empirical niche audit space from model-pool availability.

The candidate predictor universe and the environmental audit space serve different
purposes.  A model may legitimately consider all predeclared CHELSA predictors,
while niche-recovery geometry should not require a 43-variable complete case if
several climate summaries are structurally unavailable in parts of a taxon's
range.

This module therefore chooses at most one representative predictor per
predeclared ecological process using *model-pool availability only*.  Outer
sealed rows are never inspected.  Selection is deterministic and does not use
occurrence-model scores, response magnitudes or niche-recovery outcomes.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EmpiricalAuditSpace:
    predictors: tuple[str, ...]
    processes: tuple[str, ...]
    minimum_predictor_coverage: float
    minimum_joint_coverage: float
    minimum_observed_joint_coverage: float
    ledger: pd.DataFrame


def _coverage(frame: pd.DataFrame, predictor: str) -> float:
    if len(frame) == 0 or predictor not in frame.columns:
        return 0.0
    return float(pd.to_numeric(frame[predictor], errors="coerce").notna().mean())


def _joint_coverage(frame: pd.DataFrame, predictors: Sequence[str]) -> float:
    predictors = tuple(str(x) for x in predictors)
    if len(frame) == 0 or not predictors:
        return 0.0
    missing = [p for p in predictors if p not in frame.columns]
    if missing:
        return 0.0
    matrix = frame.loc[:, predictors].apply(pd.to_numeric, errors="coerce")
    return float(matrix.notna().all(axis=1).mean())


def select_empirical_audit_space(
    manifest: pd.DataFrame,
    model_pool_frames: Sequence[pd.DataFrame],
    *,
    minimum_predictor_coverage: float = 0.95,
    minimum_joint_coverage: float = 0.80,
    minimum_processes: int = 4,
) -> EmpiricalAuditSpace:
    """Select process-representative audit axes without opening sealed evidence.

    Parameters are fixed availability guardrails, not ecological fit thresholds.
    For every manifest ``process`` the predictor with the highest *minimum*
    marginal coverage across all supplied model-pool frames is the only candidate
    representative.  Representatives below ``minimum_predictor_coverage`` are
    excluded.  Remaining representatives are added from highest coverage to
    lowest only while complete-case coverage remains at least
    ``minimum_joint_coverage`` in every model-pool frame.

    The supplied frames must already be restricted to authoritative model-pool
    rows.  Passing sealed rows would violate the caller's information barrier.
    """

    required = {"predictor", "process"}
    missing = required - set(manifest.columns)
    if missing:
        raise KeyError(f"audit-space manifest missing columns: {sorted(missing)}")
    frames = tuple(frame.reset_index(drop=True) for frame in model_pool_frames)
    if not frames or any(len(frame) == 0 for frame in frames):
        raise ValueError("audit-space selection requires non-empty model-pool frames")
    if not 0 < float(minimum_predictor_coverage) <= 1:
        raise ValueError("minimum_predictor_coverage must be in (0, 1]")
    if not 0 < float(minimum_joint_coverage) <= 1:
        raise ValueError("minimum_joint_coverage must be in (0, 1]")
    if int(minimum_processes) < 1:
        raise ValueError("minimum_processes must be >= 1")

    rows: list[dict[str, object]] = []
    work = manifest[["predictor", "process"]].dropna().copy()
    work["predictor"] = work["predictor"].astype(str)
    work["process"] = work["process"].astype(str)
    work = work.drop_duplicates(["predictor"], keep="first")
    for row in work.itertuples(index=False):
        coverages = tuple(_coverage(frame, row.predictor) for frame in frames)
        rows.append(
            {
                "predictor": row.predictor,
                "process": row.process,
                "minimum_marginal_coverage": float(min(coverages)),
                "mean_marginal_coverage": float(np.mean(coverages)),
                "frame_coverages": ";".join(f"{x:.6f}" for x in coverages),
            }
        )
    coverage = pd.DataFrame(rows)

    representatives = (
        coverage.sort_values(
            ["process", "minimum_marginal_coverage", "mean_marginal_coverage", "predictor"],
            ascending=[True, False, False, True],
            kind="mergesort",
        )
        .groupby("process", as_index=False, sort=True)
        .first()
    )
    representatives = representatives.sort_values(
        ["minimum_marginal_coverage", "mean_marginal_coverage", "process", "predictor"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    selected: list[str] = []
    selected_processes: list[str] = []
    ledger_rows: list[dict[str, object]] = []
    for row in representatives.itertuples(index=False):
        trial = [*selected, str(row.predictor)]
        joint = tuple(_joint_coverage(frame, trial) for frame in frames)
        marginal_ok = float(row.minimum_marginal_coverage) >= float(
            minimum_predictor_coverage
        )
        joint_ok = bool(joint) and float(min(joint)) >= float(minimum_joint_coverage)
        accepted = marginal_ok and joint_ok
        if accepted:
            selected.append(str(row.predictor))
            selected_processes.append(str(row.process))
        ledger_rows.append(
            {
                "process": str(row.process),
                "representative_predictor": str(row.predictor),
                "minimum_marginal_coverage": float(row.minimum_marginal_coverage),
                "mean_marginal_coverage": float(row.mean_marginal_coverage),
                "selected": bool(accepted),
                "decision": (
                    "selected"
                    if accepted
                    else "below_marginal_coverage"
                    if not marginal_ok
                    else "would_break_joint_coverage"
                ),
                "minimum_joint_coverage_if_added": float(min(joint)) if joint else 0.0,
            }
        )

    if len(selected) < int(minimum_processes):
        raise ValueError(
            "model-pool availability supports too few ecological audit processes: "
            f"selected={len(selected)} minimum={minimum_processes}"
        )
    final_joint = tuple(_joint_coverage(frame, selected) for frame in frames)
    return EmpiricalAuditSpace(
        predictors=tuple(selected),
        processes=tuple(selected_processes),
        minimum_predictor_coverage=float(minimum_predictor_coverage),
        minimum_joint_coverage=float(minimum_joint_coverage),
        minimum_observed_joint_coverage=float(min(final_joint)),
        ledger=pd.DataFrame(ledger_rows),
    )
