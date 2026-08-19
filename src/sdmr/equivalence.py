"""Correlated-predictor equivalence groups for Product-B interpretation.

Correlation is used here only to identify potentially substitutable information
sets. It is never used as an automatic predictor-admission filter.
"""

from __future__ import annotations

from collections.abc import Sequence
import numpy as np
import pandas as pd

from .model import ModelSpec, evaluate_predictor_set


def correlation_equivalence_groups(
    environment: pd.DataFrame,
    predictors: Sequence[str],
    *,
    threshold: float = 0.90,
    method: str = "spearman",
    min_periods: int = 20,
) -> pd.DataFrame:
    """Build connected components of strongly correlated environmental rasters."""

    names = list(dict.fromkeys(predictors))
    if not names:
        return pd.DataFrame(columns=["predictor", "equivalence_group", "group_size", "max_abs_correlation"])
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    missing = [p for p in names if p not in environment]
    if missing:
        raise KeyError(f"Missing predictor columns: {missing}")
    corr = environment[names].corr(method=method, min_periods=min_periods).abs()

    parent = {name: name for name in names}
    order = {name: i for i, name in enumerate(names)}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if order[ra] <= order[rb]:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            value = corr.loc[a, b]
            if np.isfinite(value) and float(value) >= threshold:
                union(a, b)

    components: dict[str, list[str]] = {}
    for name in names:
        components.setdefault(find(name), []).append(name)
    ordered = sorted(components.values(), key=lambda g: min(order[x] for x in g))
    group_lookup = {}
    for idx, group in enumerate(ordered, start=1):
        group_id = f"eq{idx:03d}"
        for name in group:
            group_lookup[name] = (group_id, len(group))

    rows = []
    for name in names:
        peers = [p for p in names if p != name and group_lookup[p][0] == group_lookup[name][0]]
        max_corr = max((float(corr.loc[name, p]) for p in peers if np.isfinite(corr.loc[name, p])), default=0.0)
        rows.append(
            {
                "predictor": name,
                "equivalence_group": group_lookup[name][0],
                "group_size": group_lookup[name][1],
                "max_abs_correlation": max_corr,
            }
        )
    return pd.DataFrame(rows)


def drop_group_importance(
    train_presence: pd.DataFrame,
    train_background: pd.DataFrame,
    test_presence: pd.DataFrame,
    test_background: pd.DataFrame,
    predictors: Sequence[str],
    equivalence: pd.DataFrame,
    *,
    model_spec: ModelSpec | None = None,
) -> pd.DataFrame:
    """Measure sealed loss after removing all substitutable predictors together."""

    predictors = list(predictors)
    if not predictors:
        return pd.DataFrame(columns=["equivalence_group", "members", "full_presence_rank", "drop_presence_rank", "loss"])
    required = {"predictor", "equivalence_group"}
    missing = required - set(equivalence.columns)
    if missing:
        raise KeyError(f"equivalence missing columns: {sorted(missing)}")
    membership = equivalence.loc[equivalence["predictor"].isin(predictors), ["predictor", "equivalence_group"]]
    if set(membership["predictor"]) != set(predictors):
        absent = sorted(set(predictors) - set(membership["predictor"]))
        raise ValueError(f"Predictors missing from equivalence table: {absent}")

    full_score = float(
        evaluate_predictor_set(
            train_presence,
            train_background,
            test_presence,
            test_background,
            predictors,
            model_spec=model_spec,
        )["presence_rank"]
    )
    rows = []
    for group_id, group in membership.groupby("equivalence_group", sort=True):
        members = sorted(group["predictor"].astype(str).tolist())
        member_set = set(members)
        reduced = [p for p in predictors if p not in member_set]
        reduced_score = 0.5 if not reduced else float(
            evaluate_predictor_set(
                train_presence,
                train_background,
                test_presence,
                test_background,
                reduced,
                model_spec=model_spec,
            )["presence_rank"]
        )
        rows.append(
            {
                "equivalence_group": str(group_id),
                "members": ",".join(members),
                "n_members": len(members),
                "full_presence_rank": full_score,
                "drop_presence_rank": reduced_score,
                "loss": full_score - reduced_score,
            }
        )
    return pd.DataFrame(rows).sort_values("loss", ascending=False, kind="mergesort").reset_index(drop=True)
