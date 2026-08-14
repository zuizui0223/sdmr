"""Reproducible occurrence admission and thinning for SDMR data layers."""

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
    """Apply declared filters and return row-level rejection reasons plus ledger.

    No coordinate-uncertainty or year threshold is invented by default. Those
    choices must be explicitly configured and can therefore be sensitivity-tested.
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

    # Explicit dtype matters with modern NumPy/Pandas when the source table has
    # extension/object dtypes (as real GBIF API tables often do).  The mask is a
    # pure row-state array and must remain boolean before bitwise inversion.
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


def thin_to_grid(
    occurrences: pd.DataFrame,
    *,
    cell_size_degrees: float = 1 / 120,
    species_col: str = "species",
) -> pd.DataFrame:
    """Deterministically retain at most one occurrence per approximate raster cell.

    This is a generic pre-raster baseline. Once exact raster cell IDs are known,
    deduplicating on those IDs is preferable to assuming a grid origin.
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
    subset = ["__grid_x", "__grid_y"]
    if species_col in data:
        subset.insert(0, species_col)
    out = data.drop_duplicates(subset=subset, keep="first").drop(columns=["__grid_x", "__grid_y"])
    return out.reset_index(drop=True)
