"""Reproducible occurrence admission and deterministic thinning for SDMR."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OccurrenceAdmissionConfig:
    max_coordinate_uncertainty_m: float | None = None
    min_year: int | None = None
    max_year: int | None = None
    allowed_basis_of_record: tuple[str, ...] | None = None
    require_present_status: bool = True
    deduplicate_coordinates: bool = True


@dataclass
class OccurrenceAdmissionResult:
    accepted: pd.DataFrame
    rejected: pd.DataFrame
    ledger: pd.DataFrame


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def admit_occurrences(
    occurrences: pd.DataFrame,
    *,
    config: OccurrenceAdmissionConfig | None = None,
    species_col: str = "species",
) -> OccurrenceAdmissionResult:
    """Apply declared filters and return accepted/rejected rows plus a count ledger.

    No coordinate-uncertainty or year threshold is invented by default. Exact
    duplicate coordinates within a species are removed by default, preserving
    the established admission contract. The later Product-A grid thinning is a
    separate operation and is stable to source scan order.
    """

    cfg = config or OccurrenceAdmissionConfig()
    data = occurrences.copy().reset_index(drop=True)
    if "longitude" not in data or "latitude" not in data:
        raise KeyError("occurrences must contain longitude and latitude")

    lon = _numeric(data["longitude"])
    lat = _numeric(data["latitude"])
    reasons: list[list[str]] = [[] for _ in range(len(data))]

    missing = lon.isna() | lat.isna()
    invalid = (~missing) & ((lon < -180) | (lon > 180) | (lat < -90) | (lat > 90))
    for idx in np.flatnonzero(missing.to_numpy()):
        reasons[idx].append("missing_coordinate")
    for idx in np.flatnonzero(invalid.to_numpy()):
        reasons[idx].append("invalid_coordinate")

    if cfg.require_present_status and "occurrenceStatus" in data:
        status = data["occurrenceStatus"].fillna("").astype(str).str.upper()
        bad = status.ne("") & status.ne("PRESENT")
        for idx in np.flatnonzero(bad.to_numpy()):
            reasons[idx].append("occurrence_not_present")

    if cfg.max_coordinate_uncertainty_m is not None and "coordinateUncertaintyInMeters" in data:
        if cfg.max_coordinate_uncertainty_m < 0:
            raise ValueError("max_coordinate_uncertainty_m must be >= 0")
        uncertainty = _numeric(data["coordinateUncertaintyInMeters"])
        bad = uncertainty.notna() & (uncertainty > float(cfg.max_coordinate_uncertainty_m))
        for idx in np.flatnonzero(bad.to_numpy()):
            reasons[idx].append("coordinate_uncertainty_too_high")

    if "year" in data:
        year = _numeric(data["year"])
        if cfg.min_year is not None:
            bad = year.notna() & (year < int(cfg.min_year))
            for idx in np.flatnonzero(bad.to_numpy()):
                reasons[idx].append("year_before_min")
        if cfg.max_year is not None:
            bad = year.notna() & (year > int(cfg.max_year))
            for idx in np.flatnonzero(bad.to_numpy()):
                reasons[idx].append("year_after_max")

    if cfg.allowed_basis_of_record is not None and "basisOfRecord" in data:
        allowed = {str(x).upper() for x in cfg.allowed_basis_of_record}
        basis = data["basisOfRecord"].fillna("").astype(str).str.upper()
        bad = ~basis.isin(allowed)
        for idx in np.flatnonzero(bad.to_numpy()):
            reasons[idx].append("basis_of_record_not_allowed")

    # Explicit dtype matters for real GBIF object/extension dtypes.  This mask
    # is pure row state and must remain boolean before bitwise inversion.
    initial_reject = np.asarray([bool(x) for x in reasons], dtype=np.bool_)
    if cfg.deduplicate_coordinates:
        candidate = data.loc[~initial_reject].copy()
        candidate["__lon"] = lon.loc[~initial_reject].to_numpy()
        candidate["__lat"] = lat.loc[~initial_reject].to_numpy()
        subset = ["__lon", "__lat"]
        if species_col in candidate:
            subset.insert(0, species_col)
        duplicated = candidate.duplicated(subset=subset, keep="first")
        for idx in candidate.index[duplicated]:
            reasons[int(idx)].append("duplicate_coordinate")

    data["rejection_reason"] = [";".join(x) for x in reasons]
    rejected_mask = data["rejection_reason"].ne("")
    accepted = data.loc[~rejected_mask].drop(columns=["rejection_reason"]).reset_index(drop=True)
    rejected = data.loc[rejected_mask].reset_index(drop=True)

    counts: dict[str, int] = {"input": len(data), "accepted": len(accepted), "rejected": len(rejected)}
    for entries in reasons:
        for reason in entries:
            counts[reason] = counts.get(reason, 0) + 1
    ledger = pd.DataFrame([{"metric": key, "count": int(value)} for key, value in counts.items()])
    return OccurrenceAdmissionResult(accepted=accepted, rejected=rejected, ledger=ledger)


def _stable_id_key(data: pd.DataFrame) -> pd.Series:
    """Return a deterministic row tie-breaker without depending on scan order."""

    for column in ("gbifID", "occurrenceID", "scientificName", "eventDate"):
        if column in data:
            return data[column].fillna("").astype(str)
    return pd.Series("", index=data.index, dtype="object")


def thin_to_grid(
    occurrences: pd.DataFrame,
    *,
    cell_size_degrees: float = 1 / 120,
    species_col: str = "species",
) -> pd.DataFrame:
    """Deterministically retain at most one occurrence per species/grid cell.

    Input scan order is ignored. Rows are sorted by species, grid cell, numeric
    coordinates, and a stable public-record identifier before a representative
    is selected. This is separate from exact-coordinate deduplication during
    admission and is the declared pre-sealing spatial-thinning step for Product A.
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
