"""Descriptive diagnostics for why local SDM scores may fail to transfer.

These summaries never select a Product-A method and never enter promotion. They
quantify whether model-pool spatial-CV AUC rankings survive the preassigned
outer-sealed test, and whether outer AUC-equivalent scores agree with Boyce/CBI.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _spearman(x: pd.Series, y: pd.Series) -> float:
    pair = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(pair) < 2 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return float("nan")
    return float(pair["x"].rank(method="average").corr(pair["y"].rank(method="average")))


def discovery_generalization_diagnostics(discovery_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return case-level AUC transfer diagnostics and one aggregate summary."""
    required = {
        "data_specification", "species", "universe", "strategy",
        "inner_presence_rank", "presence_rank", "n_predictors",
    }
    missing = required - set(discovery_metrics.columns)
    if missing:
        raise KeyError(f"discovery metrics missing columns: {sorted(missing)}")

    data = discovery_metrics.copy()
    for column in ("inner_presence_rank", "presence_rank", "boyce", "continuous_boyce"):
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    case_rows: list[dict[str, object]] = []
    case_cols = ["data_specification", "species"]
    for (specification, species), frame in data.groupby(case_cols, sort=True):
        usable = frame.loc[
            np.isfinite(frame["inner_presence_rank"]) & np.isfinite(frame["presence_rank"])
        ].copy()
        if not len(usable):
            continue
        inner_order = usable.sort_values(
            ["inner_presence_rank", "n_predictors", "universe", "strategy"],
            ascending=[False, True, True, True],
            kind="mergesort",
        ).reset_index(drop=True)
        outer_order = usable.sort_values(
            ["presence_rank", "n_predictors", "universe", "strategy"],
            ascending=[False, True, True, True],
            kind="mergesort",
        ).reset_index(drop=True)
        chosen = inner_order.iloc[0]
        oracle = outer_order.iloc[0]
        outer_ranks = usable["presence_rank"].rank(method="min", ascending=False)
        chosen_index = chosen.name
        # chosen.name is reset by inner_order, so recover by method identity.
        chosen_mask = (
            usable["universe"].astype(str).eq(str(chosen["universe"]))
            & usable["strategy"].astype(str).eq(str(chosen["strategy"]))
        )
        chosen_rank = float(outer_ranks.loc[chosen_mask].iloc[0])
        row = {
            "data_specification": str(specification),
            "species": str(species),
            "n_candidates": int(len(usable)),
            "within_case_inner_outer_spearman": _spearman(
                usable["inner_presence_rank"], usable["presence_rank"]
            ),
            "inner_selected_universe": str(chosen["universe"]),
            "inner_selected_strategy": str(chosen["strategy"]),
            "outer_oracle_universe": str(oracle["universe"]),
            "outer_oracle_strategy": str(oracle["strategy"]),
            "winner_match": bool(
                str(chosen["universe"]) == str(oracle["universe"])
                and str(chosen["strategy"]) == str(oracle["strategy"])
            ),
            "inner_selected_inner_auc": float(chosen["inner_presence_rank"]),
            "inner_selected_outer_auc": float(chosen["presence_rank"]),
            "outer_oracle_auc": float(oracle["presence_rank"]),
            "outer_regret": float(oracle["presence_rank"] - chosen["presence_rank"]),
            "inner_selected_generalization_gap": float(
                chosen["presence_rank"] - chosen["inner_presence_rank"]
            ),
            "inner_selected_outer_rank": chosen_rank,
        }
        if "boyce" in usable:
            row["within_case_outer_auc_boyce_spearman"] = _spearman(
                usable["presence_rank"], usable["boyce"]
            )
        if "continuous_boyce" in usable:
            row["within_case_outer_auc_cbi_spearman"] = _spearman(
                usable["presence_rank"], usable["continuous_boyce"]
            )
        case_rows.append(row)

    cases = pd.DataFrame(case_rows)
    finite_rows = data.loc[
        np.isfinite(data["inner_presence_rank"]) & np.isfinite(data["presence_rank"])
    ].copy()
    summary = {
        "n_rows": int(len(finite_rows)),
        "n_cases": int(len(cases)),
        "row_level_inner_outer_spearman": _spearman(
            finite_rows["inner_presence_rank"], finite_rows["presence_rank"]
        ) if len(finite_rows) else float("nan"),
        "mean_within_case_inner_outer_spearman": float(
            pd.to_numeric(cases.get("within_case_inner_outer_spearman"), errors="coerce").mean()
        ) if len(cases) else float("nan"),
        "inner_winner_matches_outer_winner_fraction": float(cases["winner_match"].mean()) if len(cases) else float("nan"),
        "mean_outer_regret": float(cases["outer_regret"].mean()) if len(cases) else float("nan"),
        "median_outer_regret": float(cases["outer_regret"].median()) if len(cases) else float("nan"),
        "mean_inner_selected_generalization_gap": float(
            cases["inner_selected_generalization_gap"].mean()
        ) if len(cases) else float("nan"),
        "mean_inner_selected_outer_rank": float(cases["inner_selected_outer_rank"].mean()) if len(cases) else float("nan"),
    }
    if "boyce" in finite_rows:
        summary["row_level_outer_auc_boyce_spearman"] = _spearman(
            finite_rows["presence_rank"], finite_rows["boyce"]
        )
    if "continuous_boyce" in finite_rows:
        summary["row_level_outer_auc_cbi_spearman"] = _spearman(
            finite_rows["presence_rank"], finite_rows["continuous_boyce"]
        )
    return cases, pd.DataFrame([summary])
