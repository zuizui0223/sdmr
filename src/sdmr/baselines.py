"""Conventional predictor-screening baselines used for SDMR comparison."""

from __future__ import annotations
from collections.abc import Sequence
import numpy as np
import pandas as pd


def _complete_environment(background: pd.DataFrame, predictors: Sequence[str]) -> np.ndarray:
    X = background[list(predictors)].replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float)
    if X.shape[0] < 3:
        raise ValueError("Too few complete background rows for VIF baseline.")
    return X


def vif_values(background: pd.DataFrame, predictors: Sequence[str]) -> pd.DataFrame:
    """Compute VIF on the model-pool accessible-environment sample."""
    names = list(predictors)
    if not names:
        return pd.DataFrame(columns=["predictor", "vif"])
    if len(names) == 1:
        return pd.DataFrame({"predictor": names, "vif": [1.0]})
    X = _complete_environment(background, names)
    rows = []
    for j, name in enumerate(names):
        y = X[:, j]
        others = np.delete(X, j, axis=1)
        if np.nanstd(y) <= 1e-12:
            vif = float("inf")
        else:
            design = np.column_stack([np.ones(len(others)), others])
            beta, *_ = np.linalg.lstsq(design, y, rcond=None)
            fitted = design @ beta
            ss_res = float(np.sum((y - fitted) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
            vif = float("inf") if r2 >= 1.0 - 1e-12 else float(1.0 / max(1e-12, 1.0 - r2))
        rows.append({"predictor": name, "vif": vif})
    return pd.DataFrame(rows)


def vif_prune_predictors(
    background: pd.DataFrame,
    predictors: Sequence[str],
    *,
    threshold: float = 5.0,
) -> tuple[list[str], pd.DataFrame]:
    """Iteratively prune high-VIF predictors for the conventional baseline."""
    if threshold <= 1:
        raise ValueError("VIF threshold must be > 1.")
    kept = list(dict.fromkeys(predictors))
    if not kept:
        raise ValueError("No predictors supplied.")
    trace = []
    step = 0
    while len(kept) > 1:
        table = vif_values(background, kept)
        max_vif = float(table["vif"].max())
        if np.isfinite(max_vif) and max_vif <= threshold:
            break
        worst_names = set(table.loc[table["vif"] == table["vif"].max(), "predictor"].astype(str))
        worst = next(name for name in kept if name in worst_names)
        step += 1
        trace.append({"step": step, "dropped": worst, "vif": max_vif, "remaining_after": len(kept) - 1, "retained": ""})
        kept.remove(worst)
    for row in vif_values(background, kept).itertuples(index=False):
        trace.append({"step": step + 1, "dropped": "", "vif": float(row.vif), "remaining_after": len(kept), "retained": str(row.predictor)})
    return kept, pd.DataFrame(trace)
