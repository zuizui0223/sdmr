"""Outcome-blind environmental decorrelation audit for v10.

The audit asks whether a target process closure P ceases to be predictable from
another process closure Q in a held-out environmental block.  Only background
environments and pre-existing block labels are accepted; occurrence labels,
suitability values, fitted SDM coefficients, and generating-process truth are
outside the API.

A block is a separating candidate only when its leave-one-block-out predictive
R2 is materially below the median R2 of the other blocks.  The material drop
and uncertainty rule are fixed before any process-outcome readout.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from .process_information_purge import _numeric_complete, _purge_regressor


@dataclass(frozen=True)
class DecorrelationAuditResult:
    target_process: str
    competitor_process: str
    block_table: pd.DataFrame
    separating_blocks: tuple[int, ...]
    material_r2_drop: float
    sem_multiplier: float


def _unique(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    out = tuple(str(x).strip() for x in values)
    if not out or any(not x for x in out) or len(set(out)) != len(out):
        raise ValueError(f"{name} must be non-empty and unique")
    return out


def _multioutput_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 3:
        return float("nan")
    try:
        return float(r2_score(y_true, y_pred, multioutput="variance_weighted"))
    except ValueError:
        return float("nan")


def audit_environmental_decorrelation(
    background: pd.DataFrame,
    block_labels: Sequence[int],
    *,
    target_process: str,
    competitor_process: str,
    target_predictors: Sequence[str],
    competitor_predictors: Sequence[str],
    degree: int = 2,
    ridge_alpha: float = 1.0,
    material_r2_drop: float = 0.10,
    sem_multiplier: float = 1.0,
    minimum_complete_rows_per_block: int = 10,
) -> DecorrelationAuditResult:
    pcols = _unique(target_predictors, name="target_predictors")
    qcols = _unique(competitor_predictors, name="competitor_predictors")
    if set(pcols) & set(qcols):
        raise ValueError("target and competitor closures must be structurally disjoint")
    labels = np.asarray(block_labels)
    if labels.shape != (len(background),):
        raise ValueError("block_labels must align with background rows")
    if float(material_r2_drop) <= 0:
        raise ValueError("material_r2_drop must be > 0")
    if float(sem_multiplier) < 0:
        raise ValueError("sem_multiplier must be >= 0")

    p, pv = _numeric_complete(background, pcols)
    q, qv = _numeric_complete(background, qcols)
    valid = pv & qv & pd.notna(labels)
    unique_blocks = tuple(sorted(int(x) for x in np.unique(labels[valid])))
    if len(unique_blocks) < 3:
        raise ValueError("decorrelation audit requires at least three complete environmental blocks")

    rows: list[dict[str, object]] = []
    for block in unique_blocks:
        test = valid & (labels == block)
        train = valid & (labels != block)
        n_test = int(test.sum())
        n_train = int(train.sum())
        score = float("nan")
        if n_test >= int(minimum_complete_rows_per_block) and n_train >= 2 * int(minimum_complete_rows_per_block):
            model = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
            model.fit(q[train], p[train])
            score = _multioutput_r2(p[test], np.asarray(model.predict(q[test]), dtype=float))
        rows.append({
            "block": int(block),
            "n_train": n_train,
            "n_test": n_test,
            "heldout_r2": score,
            "complete": bool(np.isfinite(score)),
        })

    table = pd.DataFrame(rows).sort_values("block", kind="mergesort").reset_index(drop=True)
    complete_scores = table.loc[table["complete"].astype(bool), "heldout_r2"].to_numpy(float)
    if len(complete_scores) < 3:
        table["reference_median_other_blocks"] = np.nan
        table["reference_sem_other_blocks"] = np.nan
        table["r2_drop"] = np.nan
        table["separating_candidate"] = False
        return DecorrelationAuditResult(str(target_process), str(competitor_process), table, (), float(material_r2_drop), float(sem_multiplier))

    medians: list[float] = []
    sems: list[float] = []
    drops: list[float] = []
    flags: list[bool] = []
    for _, row in table.iterrows():
        if not bool(row["complete"]):
            medians.append(float("nan")); sems.append(float("nan")); drops.append(float("nan")); flags.append(False); continue
        others = table.loc[table["complete"].astype(bool) & table["block"].ne(int(row["block"])), "heldout_r2"].to_numpy(float)
        ref = float(np.median(others))
        sem = float(np.std(others, ddof=1) / np.sqrt(len(others))) if len(others) > 1 else 0.0
        drop = ref - float(row["heldout_r2"])
        flag = bool(drop >= float(material_r2_drop) + float(sem_multiplier) * sem)
        medians.append(ref); sems.append(sem); drops.append(drop); flags.append(flag)
    table["reference_median_other_blocks"] = medians
    table["reference_sem_other_blocks"] = sems
    table["r2_drop"] = drops
    table["separating_candidate"] = flags
    separating = tuple(int(x) for x in table.loc[table["separating_candidate"].astype(bool), "block"])
    return DecorrelationAuditResult(str(target_process), str(competitor_process), table, separating, float(material_r2_drop), float(sem_multiplier))
