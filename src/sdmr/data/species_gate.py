"""Explicit taxon-level data sufficiency gates for SDMR."""

from __future__ import annotations

import pandas as pd


def species_admission_table(
    occurrences: pd.DataFrame,
    *,
    min_occurrences: int,
    min_unique_cells: int,
    cell_size_degrees: float,
    species_col: str = "species",
) -> pd.DataFrame:
    """Report which taxa meet an explicitly declared modelling-data gate.

    Thresholds have no hidden defaults because they are part of the Product-A
    sensitivity design. ``n_unique_cells`` is a transparent pre-raster proxy;
    exact raster-cell counts should replace it after extraction where possible.
    """

    if min_occurrences < 1 or min_unique_cells < 1:
        raise ValueError("minimum counts must be >= 1")
    if cell_size_degrees <= 0:
        raise ValueError("cell_size_degrees must be > 0")
    if species_col not in occurrences:
        raise KeyError(species_col)
    data = occurrences.dropna(subset=["longitude", "latitude"]).copy()
    lon = pd.to_numeric(data["longitude"], errors="coerce")
    lat = pd.to_numeric(data["latitude"], errors="coerce")
    data = data.loc[lon.notna() & lat.notna()].copy()
    lon = pd.to_numeric(data["longitude"], errors="coerce")
    lat = pd.to_numeric(data["latitude"], errors="coerce")
    data["__cell"] = (
        ((lon + 180) / cell_size_degrees).floordiv(1).astype("int64").astype(str)
        + ":"
        + ((lat + 90) / cell_size_degrees).floordiv(1).astype("int64").astype(str)
    )
    summary = (
        data.groupby(species_col, as_index=False)
        .agg(n_occurrences=(species_col, "size"), n_unique_cells=("__cell", "nunique"))
        .sort_values(species_col, kind="mergesort")
        .reset_index(drop=True)
    )
    summary["eligible"] = (
        (summary["n_occurrences"] >= int(min_occurrences))
        & (summary["n_unique_cells"] >= int(min_unique_cells))
    )
    summary["min_occurrences"] = int(min_occurrences)
    summary["min_unique_cells"] = int(min_unique_cells)
    summary["cell_size_degrees"] = float(cell_size_degrees)
    return summary
