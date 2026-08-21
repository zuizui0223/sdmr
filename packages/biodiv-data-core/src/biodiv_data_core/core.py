from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class OccurrenceRecord:
    taxon: str
    latitude: float
    longitude: float
    occurrence_id: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class AdmissionDecision:
    occurrence_id: str | None
    admitted: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RasterProvenance:
    name: str
    uri: str
    crs: str | None = None
    resolution: str | None = None
    nodata: str | None = None
    checksum_sha256: str | None = None


def stable_fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=repr)
    return sha256(payload.encode("utf-8")).hexdigest()


def validate_occurrence(record: OccurrenceRecord) -> AdmissionDecision:
    reasons: list[str] = []
    if not record.taxon.strip():
        reasons.append("missing_taxon")
    if not math.isfinite(record.latitude) or not -90 <= record.latitude <= 90:
        reasons.append("invalid_latitude")
    if not math.isfinite(record.longitude) or not -180 <= record.longitude <= 180:
        reasons.append("invalid_longitude")
    return AdmissionDecision(record.occurrence_id, not reasons, tuple(reasons))


def admission_ledger(records: Iterable[OccurrenceRecord]) -> tuple[AdmissionDecision, ...]:
    return tuple(validate_occurrence(record) for record in records)


def deduplicate_occurrences(
    records: Iterable[OccurrenceRecord],
    *,
    coordinate_digits: int = 5,
) -> tuple[OccurrenceRecord, ...]:
    """Deterministically keep one record per taxon/rounded coordinate key."""
    kept: dict[tuple[str, float, float], OccurrenceRecord] = {}
    ordered = sorted(
        records,
        key=lambda r: (r.taxon, r.occurrence_id or "", r.latitude, r.longitude),
    )
    for record in ordered:
        key = (
            record.taxon.strip(),
            round(record.latitude, coordinate_digits),
            round(record.longitude, coordinate_digits),
        )
        kept.setdefault(key, record)
    return tuple(kept[key] for key in sorted(kept))


def spatial_block_id(latitude: float, longitude: float, *, block_degrees: float) -> str:
    """Assign a deterministic geographic grid block without external GIS dependencies."""
    if block_degrees <= 0:
        raise ValueError("block_degrees must be positive")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("coordinates outside geographic bounds")
    lat_i = math.floor((latitude + 90.0) / block_degrees)
    lon_i = math.floor((longitude + 180.0) / block_degrees)
    return f"g{block_degrees:g}_lat{lat_i}_lon{lon_i}"


def assign_spatial_blocks(
    records: Iterable[OccurrenceRecord],
    *,
    block_degrees: float,
) -> tuple[tuple[OccurrenceRecord, str], ...]:
    return tuple(
        (record, spatial_block_id(record.latitude, record.longitude, block_degrees=block_degrees))
        for record in records
    )


def deterministic_block_split(
    block_ids: Sequence[str],
    *,
    holdout_fraction: float,
    salt: str = "",
) -> Mapping[str, str]:
    """Assign whole blocks to model/holdout roles with a stable hash contract."""
    if not 0 <= holdout_fraction <= 1:
        raise ValueError("holdout_fraction must be in [0, 1]")
    result: dict[str, str] = {}
    for block_id in sorted(set(block_ids)):
        digest = sha256(f"{salt}|{block_id}".encode("utf-8")).digest()
        u = int.from_bytes(digest[:8], "big") / 2**64
        result[block_id] = "holdout" if u < holdout_fraction else "model"
    return result


def occurrence_manifest(records: Iterable[OccurrenceRecord]) -> dict[str, object]:
    canonical = [asdict(r) for r in sorted(records, key=lambda x: (x.taxon, x.occurrence_id or "", x.latitude, x.longitude))]
    return {
        "record_count": len(canonical),
        "records_sha256": stable_fingerprint(canonical),
    }


def raster_manifest(rasters: Iterable[RasterProvenance]) -> dict[str, object]:
    canonical = [
        asdict(r)
        for r in sorted(rasters, key=lambda x: (x.name, x.uri))
    ]
    return {
        "raster_count": len(canonical),
        "rasters": canonical,
        "manifest_sha256": stable_fingerprint(canonical),
    }
