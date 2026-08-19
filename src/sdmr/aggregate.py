"""Cross-taxon aggregation of predictor discovery results."""

from __future__ import annotations

import pandas as pd


def aggregate_predictor_selection(selection_rows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate inner-CV predictor selection with equal weight per species."""

    required = {"species", "predictor", "step", "gain"}
    missing = required - set(selection_rows.columns)
    if missing:
        raise KeyError(f"selection_rows missing columns: {sorted(missing)}")
    species_n = int(selection_rows["species"].nunique())
    if species_n == 0:
        return pd.DataFrame(
            columns=["predictor", "species_selected", "selection_fraction", "median_gain", "median_step"]
        )

    out = (
        selection_rows.groupby("predictor", as_index=False)
        .agg(
            species_selected=("species", "nunique"),
            median_gain=("gain", "median"),
            median_step=("step", "median"),
        )
        .assign(selection_fraction=lambda x: x["species_selected"] / species_n)
    )
    return out.sort_values(
        ["selection_fraction", "median_gain", "median_step"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def choose_common_predictors(
    aggregate: pd.DataFrame,
    *,
    min_fraction: float = 0.25,
    top_k: int | None = 8,
) -> list[str]:
    """Choose a discovery-taxa common set without consulting validation taxa."""

    if not 0 <= min_fraction <= 1:
        raise ValueError("min_fraction must be in [0, 1].")
    selected = aggregate.loc[aggregate["selection_fraction"] >= min_fraction, "predictor"].tolist()
    if not selected and len(aggregate):
        selected = aggregate["predictor"].tolist()
    if top_k is not None:
        selected = selected[: int(top_k)]
    return selected
