"""Context-indexed process attribution for v16 development.

Consumes v15 source->target pair decisions and returns target-context statuses
without collapsing across evaluation environments. No generating truth or fresh
validation data are accepted by this module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


CONTEXT_REPLACEABLE = "context_replaceable"
CONTEXT_CONTRIBUTORY = "context_contributory"
CONTEXT_UNRESOLVED = "context_unresolved"
CONTEXT_INSUFFICIENT = "insufficient"


def classify_target_context(group: pd.DataFrame, *, minimum_evaluable_sources: int = 3) -> str:
    evaluable = group.loc[group["evaluable"].astype(bool)].copy()
    n = len(evaluable)
    if n < int(minimum_evaluable_sources):
        return CONTEXT_INSUFFICIENT
    reproduced = evaluable["reproduces_v8_noncontributory"].astype(bool)
    k = int(reproduced.sum())
    if k == n:
        return CONTEXT_REPLACEABLE
    if k == 0:
        return CONTEXT_CONTRIBUTORY
    return CONTEXT_UNRESOLVED


def summarize_context_indexed_attribution(
    pair_summary: pd.DataFrame,
    *,
    minimum_evaluable_sources: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {
        "family", "seed", "target_process", "source_block", "target_block",
        "evaluable", "reproduces_v8_noncontributory",
    }
    missing = sorted(required - set(pair_summary.columns))
    if missing:
        raise KeyError("pair summary missing columns: " + ", ".join(missing))

    frame = pair_summary.copy()
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["source_block"] = pd.to_numeric(frame["source_block"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    frame["evaluable"] = frame["evaluable"].astype(bool)
    frame["reproduces_v8_noncontributory"] = frame["reproduces_v8_noncontributory"].astype(bool)

    target_rows = []
    source_rows = []
    cell_rows = []
    keys = ["family", "seed", "target_process"]

    for cell_key, cell in frame.groupby(keys, sort=True):
        family, seed, process = cell_key
        for target, group in cell.groupby("target_block", sort=True):
            evaluable = group.loc[group["evaluable"]]
            n = int(len(evaluable))
            k = int(evaluable["reproduces_v8_noncontributory"].sum()) if n else 0
            target_rows.append({
                "family": family,
                "seed": int(seed),
                "target_process": process,
                "target_block": int(target),
                "n_evaluable_source_maps": n,
                "n_reproduced_source_maps": k,
                "reproduction_rate": float(k / n) if n else float("nan"),
                "context_status": classify_target_context(
                    group,
                    minimum_evaluable_sources=int(minimum_evaluable_sources),
                ),
            })
        for source, group in cell.groupby("source_block", sort=True):
            evaluable = group.loc[group["evaluable"]]
            n = int(len(evaluable))
            k = int(evaluable["reproduces_v8_noncontributory"].sum()) if n else 0
            source_rows.append({
                "family": family,
                "seed": int(seed),
                "target_process": process,
                "source_block": int(source),
                "n_evaluable_target_blocks": n,
                "n_reproduced_target_blocks": k,
                "reproduction_rate": float(k / n) if n else float("nan"),
            })

    targets = pd.DataFrame(target_rows)
    sources = pd.DataFrame(source_rows)
    for cell_key, t in targets.groupby(keys, sort=True):
        s = sources
        for col, val in zip(keys, cell_key, strict=True):
            s = s.loc[s[col].eq(val)]
        t_rates = pd.to_numeric(t["reproduction_rate"], errors="coerce").to_numpy(float)
        s_rates = pd.to_numeric(s["reproduction_rate"], errors="coerce").to_numpy(float)
        t_rates = t_rates[np.isfinite(t_rates)]
        s_rates = s_rates[np.isfinite(s_rates)]
        target_sd = float(np.std(t_rates, ddof=0)) if len(t_rates) else float("nan")
        source_sd = float(np.std(s_rates, ddof=0)) if len(s_rates) else float("nan")
        status_counts = t["context_status"].value_counts()
        cell_rows.append({
            "family": cell_key[0],
            "seed": int(cell_key[1]),
            "target_process": cell_key[2],
            "n_target_contexts": int(len(t)),
            "n_context_replaceable": int(status_counts.get(CONTEXT_REPLACEABLE, 0)),
            "n_context_contributory": int(status_counts.get(CONTEXT_CONTRIBUTORY, 0)),
            "n_context_unresolved": int(status_counts.get(CONTEXT_UNRESOLVED, 0)),
            "n_context_insufficient": int(status_counts.get(CONTEXT_INSUFFICIENT, 0)),
            "target_context_rate_sd": target_sd,
            "source_map_rate_sd": source_sd,
            "target_variation_exceeds_source_variation": bool(
                np.isfinite(target_sd) and np.isfinite(source_sd) and target_sd > source_sd
            ),
        })
    cells = pd.DataFrame(cell_rows)
    return targets, sources, cells
