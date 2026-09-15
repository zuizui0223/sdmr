"""Set-valued process attribution preserving v21 support without forced winners."""
from __future__ import annotations

from collections.abc import Sequence
import pandas as pd


def build_context_sets(
    context_decisions: pd.DataFrame,
    *,
    process_order: Sequence[str] = ("temperature", "water", "seasonality", "noise"),
) -> pd.DataFrame:
    required = {
        "family", "seed", "target_block", "target_process",
        "supported", "high_confidence_supported",
    }
    missing = sorted(required - set(context_decisions.columns))
    if missing:
        raise KeyError("context decisions missing columns: " + ", ".join(missing))
    order = {str(p): i for i, p in enumerate(process_order)}
    rows = []
    frame = context_decisions.copy()
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    frame["supported"] = frame["supported"].astype(bool)
    frame["high_confidence_supported"] = frame["high_confidence_supported"].astype(bool)
    keys = ["family", "seed", "target_block"]
    for (family, seed, block), group in frame.groupby(keys, sort=True):
        if group["target_process"].astype(str).duplicated().any():
            raise ValueError("duplicate process row within context")
        unknown = sorted(set(group["target_process"].astype(str)) - set(order))
        if unknown:
            raise ValueError("process outside frozen universe: " + ", ".join(unknown))
        supported = sorted(group.loc[group["supported"], "target_process"].astype(str), key=order.__getitem__)
        high = sorted(group.loc[group["high_confidence_supported"], "target_process"].astype(str), key=order.__getitem__)
        if not set(high).issubset(set(supported)):
            raise ValueError("high-confidence subset must be contained in supported set")
        rows.append({
            "family": str(family), "seed": int(seed), "target_block": int(block),
            "supported_set": "+".join(supported),
            "high_confidence_subset": "+".join(high),
            "supported_set_size": int(len(supported)),
            "high_confidence_subset_size": int(len(high)),
            "attribution_state": (
                "empty" if len(supported) == 0 else
                "singleton" if len(supported) == 1 else
                "partial_identification_set"
            ),
        })
    return pd.DataFrame(rows)


def score_known_truth_sets(context_sets: pd.DataFrame, context_decisions: pd.DataFrame) -> dict[str, float | int]:
    """Development-only scoring; truth is not used to construct the sets."""
    required = {"family", "seed", "target_block", "target_process", "generating_process_true"}
    missing = sorted(required - set(context_decisions.columns))
    if missing:
        raise KeyError("truth scoring input missing columns: " + ", ".join(missing))
    truth = context_decisions.copy()
    truth["generating_process_true"] = truth["generating_process_true"].astype(bool)
    truth_map = {}
    for key, group in truth.groupby(["family", "seed", "target_block"], sort=True):
        truth_map[(str(key[0]), int(key[1]), int(key[2]))] = set(
            group.loc[group["generating_process_true"], "target_process"].astype(str)
        )
    n = len(context_sets); true_covered = 0; exact = 0; false_members = 0; total_members = 0
    singleton_n = 0; singleton_correct = 0; high_true_covered = 0
    for row in context_sets.itertuples(index=False):
        key = (str(row.family), int(row.seed), int(row.target_block))
        t = truth_map.get(key, set())
        s = set(filter(None, str(row.supported_set).split("+")))
        h = set(filter(None, str(row.high_confidence_subset).split("+")))
        true_covered += int(bool(t) and t.issubset(s))
        high_true_covered += int(bool(t) and t.issubset(h))
        exact += int(s == t)
        false_members += len(s - t); total_members += len(s)
        if len(s) == 1:
            singleton_n += 1
            singleton_correct += int(next(iter(s)) in t)
    return {
        "n_contexts": int(n),
        "all_true_processes_covered_rate": float(true_covered / n) if n else float("nan"),
        "high_confidence_all_true_covered_rate": float(high_true_covered / n) if n else float("nan"),
        "exact_set_rate": float(exact / n) if n else float("nan"),
        "false_member_fraction": float(false_members / total_members) if total_members else 0.0,
        "n_singleton_contexts": int(singleton_n),
        "singleton_precision": float(singleton_correct / singleton_n) if singleton_n else float("nan"),
    }
