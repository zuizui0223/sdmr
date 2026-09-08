"""Fail-closed pairwise decision for preselected separator-block evidence."""
from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_FAVORED = "target_favored"
COMPETITOR_FAVORED = "competitor_favored"
UNRESOLVED = "unresolved"
INCOMPLETE = "incomplete"


def _mean_sem(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return float("nan"), float("nan")
    mean = float(np.mean(values))
    sem = float(np.std(values, ddof=1) / np.sqrt(len(values))) if len(values) > 1 else 0.0
    return mean, sem


def classify_separator_pair(
    evidence: pd.DataFrame,
    *,
    rank_margin: float = 0.02,
    density_margin: float = 0.01,
    sem_multiplier: float = 1.0,
) -> dict[str, object]:
    complete = evidence.loc[evidence["complete"].astype(bool)].copy()
    if complete.empty:
        return {"state": INCOMPLETE, "n_blocks": 0}
    rank_diff = complete["target_rank_loss"].to_numpy(float) - complete["competitor_rank_loss"].to_numpy(float)
    density_diff = complete["target_density_loss"].to_numpy(float) - complete["competitor_density_loss"].to_numpy(float)
    rmean, rsem = _mean_sem(rank_diff)
    dmean, dsem = _mean_sem(density_diff)
    if not all(np.isfinite(x) for x in (rmean, rsem, dmean, dsem)):
        return {"state": INCOMPLETE, "n_blocks": int(len(complete))}
    target = (rmean - float(sem_multiplier) * rsem > float(rank_margin)) and (dmean - float(sem_multiplier) * dsem > float(density_margin))
    competitor = (rmean + float(sem_multiplier) * rsem < -float(rank_margin)) and (dmean + float(sem_multiplier) * dsem < -float(density_margin))
    state = TARGET_FAVORED if target else COMPETITOR_FAVORED if competitor else UNRESOLVED
    return {
        "state": state,
        "n_blocks": int(len(complete)),
        "mean_rank_loss_difference": rmean,
        "sem_rank_loss_difference": rsem,
        "mean_density_loss_difference": dmean,
        "sem_density_loss_difference": dsem,
        "rank_margin": float(rank_margin),
        "density_margin": float(density_margin),
        "sem_multiplier": float(sem_multiplier),
    }
