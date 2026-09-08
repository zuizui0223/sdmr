"""Outcome-blind carrier qualification for shared-process separation v11."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .environmental_decorrelation_audit import (
    DecorrelationAuditResult,
    audit_environmental_decorrelation,
)

CARRIER_COLUMNS = (
    "target_process",
    "carrier_process",
    "structurally_disjoint",
    "n_complete_blocks",
    "median_heldout_r2",
    "eligible_carrier",
    "n_separating_blocks",
    "separating_blocks",
)


def qualify_carrier_pair(
    background: pd.DataFrame,
    block_labels: Sequence[int],
    *,
    target_process: str,
    carrier_process: str,
    target_predictors: Sequence[str],
    carrier_predictors: Sequence[str],
    minimum_complete_blocks: int = 3,
    median_heldout_r2_min_exclusive: float = 0.0,
    degree: int = 2,
    ridge_alpha: float = 1.0,
    material_r2_drop: float = 0.10,
    sem_multiplier: float = 1.0,
    minimum_complete_rows_per_block: int = 10,
) -> tuple[dict[str, object], DecorrelationAuditResult | None]:
    """Qualify Q as a carrier of P using background representation only.

    Carrier qualification deliberately ignores occurrence labels, process outcome
    status, suitability, and generating truth. The already-frozen v10
    decorrelation audit supplies leave-one-block-out P<-Q held-out R2 values.
    """
    if str(target_process) == str(carrier_process):
        raise ValueError("carrier_process must differ from target_process")
    if int(minimum_complete_blocks) < 3:
        raise ValueError("minimum_complete_blocks must be >= 3")

    base = {
        "target_process": str(target_process),
        "carrier_process": str(carrier_process),
        "structurally_disjoint": False,
        "n_complete_blocks": 0,
        "median_heldout_r2": float("nan"),
        "eligible_carrier": False,
        "n_separating_blocks": 0,
        "separating_blocks": "",
    }
    try:
        audit = audit_environmental_decorrelation(
            background,
            block_labels,
            target_process=str(target_process),
            competitor_process=str(carrier_process),
            target_predictors=target_predictors,
            competitor_predictors=carrier_predictors,
            degree=int(degree),
            ridge_alpha=float(ridge_alpha),
            material_r2_drop=float(material_r2_drop),
            sem_multiplier=float(sem_multiplier),
            minimum_complete_rows_per_block=int(minimum_complete_rows_per_block),
        )
    except ValueError as exc:
        if "structurally disjoint" in str(exc):
            return base, None
        raise

    complete = audit.block_table.loc[audit.block_table["complete"].astype(bool), "heldout_r2"].to_numpy(float)
    finite = complete[np.isfinite(complete)]
    median = float(np.median(finite)) if len(finite) else float("nan")
    eligible = bool(
        len(finite) >= int(minimum_complete_blocks)
        and np.isfinite(median)
        and median > float(median_heldout_r2_min_exclusive)
    )
    row = dict(base)
    row.update(
        {
            "structurally_disjoint": True,
            "n_complete_blocks": int(len(finite)),
            "median_heldout_r2": median,
            "eligible_carrier": eligible,
            "n_separating_blocks": int(len(audit.separating_blocks)) if eligible else 0,
            "separating_blocks": ",".join(str(x) for x in audit.separating_blocks) if eligible else "",
        }
    )
    return row, audit


def qualify_carrier_set(
    background: pd.DataFrame,
    block_labels: Sequence[int],
    *,
    target_process: str,
    process_universe: Sequence[str],
    closures: Mapping[str, Sequence[str]],
    minimum_complete_blocks: int = 3,
    median_heldout_r2_min_exclusive: float = 0.0,
    degree: int = 2,
    ridge_alpha: float = 1.0,
    material_r2_drop: float = 0.10,
    sem_multiplier: float = 1.0,
    minimum_complete_rows_per_block: int = 10,
) -> tuple[pd.DataFrame, dict[str, DecorrelationAuditResult]]:
    """Return every background-qualified carrier candidate Q for target P."""
    target = str(target_process)
    if target not in closures:
        raise KeyError(f"target process missing from closures: {target}")
    rows: list[dict[str, object]] = []
    audits: dict[str, DecorrelationAuditResult] = {}
    for q in (str(x) for x in process_universe):
        if q == target:
            continue
        if q not in closures:
            raise KeyError(f"carrier process missing from closures: {q}")
        row, audit = qualify_carrier_pair(
            background,
            block_labels,
            target_process=target,
            carrier_process=q,
            target_predictors=closures[target],
            carrier_predictors=closures[q],
            minimum_complete_blocks=minimum_complete_blocks,
            median_heldout_r2_min_exclusive=median_heldout_r2_min_exclusive,
            degree=degree,
            ridge_alpha=ridge_alpha,
            material_r2_drop=material_r2_drop,
            sem_multiplier=sem_multiplier,
            minimum_complete_rows_per_block=minimum_complete_rows_per_block,
        )
        rows.append(row)
        if audit is not None:
            audits[q] = audit
    frame = pd.DataFrame(rows, columns=CARRIER_COLUMNS)
    return frame, audits
