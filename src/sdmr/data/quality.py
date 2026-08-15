"""Occurrence quality control and reproducible spatial thinning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OccurrenceAdmissionConfig:
    max_coordinate_uncertainty_m: float | None = None
    min_year: int | None = None
    max_year: int | None = None
    allowed_basis_of_record: tuple[str, ...] | None = None
    require_present_status: bool = True


@dataclass
class OccurrenceAdmissionResult:
    accepted: pd.DataFrame
    ledger: pd.DataFrame


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def admit_occurrences(
    records: pd.DataFrame,
    *,
    config: OccurrenceAdmissionConfig,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
) -> OccurrenceAdmissionResult:
    """Apply transparent row-level occurrence admission rules.

    Every input row is retained in the ledger with an accepted flag and a
    semicolon-separated rejection reason.  No implicit occurrence threshold is
    imposed here; species-level sufficiency is a separate declared gate.
    """

    if lon_col not in records or lat_col not in records:
        raise KeyError(f"records must contain {lon_col!r} and {lat_col!r}")
    data = records.copy().reset_index(drop=True)
    lon = _numeric(data[lon_col])
    lat = _numeric(data[lat_col])
    reasons = np.full(len(data), "", dtype=object)

    def reject(mask: pd.Series | np.ndarray, reason: str) -> None:
        nonlocal reasons
        mask = np.asarray(mask, dtype=bool)
        reasons[mask] = np.where(reasons[mask] == "", reason, reasons[mask] + ";" + reason)

    reject(lon.isna() | lat.isna(), "missing_coordinate")
    reject(lon.notna() & ~lon.between(-180, 180), "invalid_longitude")
    reject(lat.notna() & ~lat.between(-90, 90), "invalid_latitude")

    if config.max_coordinate_uncertainty_m is not None:
        if config.max_coordinate_uncertainty_m < 0:
            raise ValueError("max_coordinate_uncertainty_m must be >= 0")
        column = "coordinateUncertaintyInMeters"
        if column in data:
            uncertainty = _numeric(data[column])
            reject(uncertainty.notna() & (uncertainty > config.max_coordinate_uncertainty_m), "coordinate_uncertainty")

    if config.min_year is not None or config.max_year is not None:
        if "year" in data:
            year = _numeric(data["year"])
            if config.min_year is not None:
                reject(year.notna() & (year < config.min_year), "before_min_year")
            if config.max_year is not None:
                reject(year.notna() & (year > config.max_year), "after_max_year")

    if config.allowed_basis_of_record:
        if "basisOfRecord" in data:
            allowed = {str(x).upper() for x in config.allowed_basis_of_record}
            values = data["basisOfRecord"].fillna("").astype(str).str.upper()
            reject(~values.isin(allowed), "basis_of_record")

    if config.require_present_status and "occurrenceStatus" in data:
        status = data["occurrenceStatus"].fillna("").astype(str).str.upper()
        reject(~status.isin({"", "PRESENT"}), "occurrence_status")

    accepted = reasons == ""
    ledger = data.copy()
    ledger["accepted"] = accepted
    ledger["rejection_reason"] = reasons
    return OccurrenceAdmissionResult(
        accepted=data.loc[accepted].reset_index(drop=True),
        ledger=ledger,
    )


def _stable_id_key(data: pd.DataFrame) -> pd.Series:
    """Return a deterministic row tie-breaker without depending on scan order."""

    for column in ("gbifID", "occurrenceID", "scientificName", "eventDate"):
        if column in data:
            return data[column].fillna("").astype(str)
    # Coordinates are already part of the stable sort.  If no public record ID
    # is available, using a constant keeps selection deterministic for distinct
    # coordinates; exact coordinate duplicates are environmentally equivalent
    # for this generic pre-raster thinning baseline.
    return pd.Series("", index=data.index, dtype="object")


def thin_to_grid(
    occurrences: pd.DataFrame,
    *,
    cell_size_degrees: float = 1 / 120,
    species_col: str = "species",
) -> pd.DataFrame:
    """Deterministically retain at most one occurrence per species/grid cell.

    Input scan order is explicitly ignored.  Rows are sorted by species, cell,
    numeric coordinates, and a stable public-record identifier before the cell
    representative is selected.  This is a generic pre-raster baseline; once
    exact raster cell IDs are known, deduplicating on those IDs is preferable.
    """

    if cell_size_degrees <= 0:
        raise ValueError("cell_size_degrees must be > 0")
    data = occurrences.copy()
    lon = _numeric(data["longitude"])
    lat = _numeric(data["latitude"])
    if lon.isna().any() or lat.isna().any():
        raise ValueError("thin_to_grid requires finite longitude/latitude")
    data["__grid_x"] = np.floor((lon + 180.0) / cell_size_degrees).astype(np.int64)
    data["__grid_y"] = np.floor((lat + 90.0) / cell_size_degrees).astype(np.int64)
    data["__sdmr_lon_sort"] = lon.to_numpy(float)
    data["__sdmr_lat_sort"] = lat.to_numpy(float)
    data["__sdmr_id_sort"] = _stable_id_key(data)

    group_cols = ["__grid_x", "__grid_y"]
    sort_cols: list[str] = []
    if species_col in data:
        group_cols.insert(0, species_col)
        sort_cols.append(species_col)
    sort_cols.extend(["__grid_x", "__grid_y", "__sdmr_lon_sort", "__sdmr_lat_sort", "__sdmr_id_sort"])
    data = data.sort_values(sort_cols, kind="mergesort", na_position="last")
    out = data.drop_duplicates(subset=group_cols, keep="first").drop(
        columns=["__grid_x", "__grid_y", "__sdmr_lon_sort", "__sdmr_lat_sort", "__sdmr_id_sort"]
    )
    return out.reset_index(drop=True)
