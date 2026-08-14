"""Sampling-aware target-group background construction.

SDMR intentionally does not define a single universal accessible area (M). The
caller supplies an explicit M-membership mask; this module then draws reference
points from comparable plant sampling effort inside that declared area.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def bbox_membership(
    frame: pd.DataFrame,
    *,
    west: float,
    east: float,
    south: float,
    north: float,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
) -> np.ndarray:
    """Return a simple geographic bounding-box mask for diagnostics/sensitivity.

    This helper is a baseline M construction, not a claim that rectangular M is
    biologically optimal. Dateline-crossing boxes are supported with west > east.
    """

    lon = pd.to_numeric(frame[lon_col], errors="coerce").to_numpy(float)
    lat = pd.to_numeric(frame[lat_col], errors="coerce").to_numpy(float)
    if west <= east:
        lon_ok = (lon >= west) & (lon <= east)
    else:
        lon_ok = (lon >= west) | (lon <= east)
    return lon_ok & (lat >= south) & (lat <= north) & np.isfinite(lon) & np.isfinite(lat)


def _grid_ids(frame: pd.DataFrame, cell_size_degrees: float) -> np.ndarray:
    lon = pd.to_numeric(frame["longitude"], errors="coerce").to_numpy(float)
    lat = pd.to_numeric(frame["latitude"], errors="coerce").to_numpy(float)
    gx = np.floor((lon + 180.0) / cell_size_degrees).astype(np.int64)
    gy = np.floor((lat + 90.0) / cell_size_degrees).astype(np.int64)
    return np.char.add(np.char.add(gx.astype(str), ":"), gy.astype(str))


def sample_target_group_background(
    focal_occurrences: pd.DataFrame,
    target_group_pool: pd.DataFrame,
    *,
    m_mask: np.ndarray | pd.Series,
    n_points: int = 10_000,
    cell_size_degrees: float = 1 / 120,
    focal_species: str | None = None,
    species_col: str = "species",
    random_state: int = 42,
) -> pd.DataFrame:
    """Sample target-group reference points inside a predeclared accessible area.

    Candidate cells containing a focal presence are excluded. One target-group
    record per approximate climate cell is retained before sampling so collector
    hotspots do not become arbitrarily large weights merely through duplicates.
    """

    if n_points < 1:
        raise ValueError("n_points must be >= 1")
    if cell_size_degrees <= 0:
        raise ValueError("cell_size_degrees must be > 0")
    mask = np.asarray(m_mask, dtype=bool)
    if len(mask) != len(target_group_pool):
        raise ValueError("m_mask length must match target_group_pool")

    candidates = target_group_pool.loc[mask].copy().reset_index(drop=True)
    if not len(candidates):
        raise ValueError("No target-group records fall inside the supplied accessible area M")
    candidates = candidates.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    candidates["__cell"] = _grid_ids(candidates, cell_size_degrees)
    focal_cells = set(_grid_ids(focal_occurrences.dropna(subset=["longitude", "latitude"]), cell_size_degrees))
    candidates = candidates.loc[~candidates["__cell"].isin(focal_cells)].copy()
    candidates = candidates.drop_duplicates("__cell", keep="first")
    if not len(candidates):
        raise ValueError("No target-group cells remain after excluding focal-presence cells")

    if focal_species is None:
        if species_col in focal_occurrences and focal_occurrences[species_col].nunique() == 1:
            focal_species = str(focal_occurrences[species_col].iloc[0])
        else:
            focal_species = "focal_species"

    rng = np.random.default_rng(random_state)
    take = min(int(n_points), len(candidates))
    selected_idx = rng.choice(len(candidates), size=take, replace=False)
    selected = candidates.iloc[np.sort(selected_idx)].copy()
    if species_col in selected:
        selected["background_source_species"] = selected[species_col].astype(str)
    selected[species_col] = focal_species
    return selected.drop(columns=["__cell"]).reset_index(drop=True)
