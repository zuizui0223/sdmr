"""Build multiple spatial query boxes from focal occurrence subsets."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .snapshot import SnapshotBounds

_KM_PER_LAT_DEGREE = 111.195


def _coordinate_columns(frame: pd.DataFrame) -> tuple[str, str]:
    lon_col = "longitude" if "longitude" in frame else "decimallongitude"
    lat_col = "latitude" if "latitude" in frame else "decimallatitude"
    if lon_col not in frame or lat_col not in frame:
        raise KeyError("frame requires longitude/latitude or decimallongitude/decimallatitude")
    return lon_col, lat_col


def _finite_coordinates(frame: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    lon_col, lat_col = _coordinate_columns(frame)
    data = frame.copy()
    data[lon_col] = pd.to_numeric(data[lon_col], errors="coerce")
    data[lat_col] = pd.to_numeric(data[lat_col], errors="coerce")
    data = data.dropna(subset=[lon_col, lat_col])
    data = data.loc[
        data[lon_col].between(-180, 180, inclusive="both")
        & data[lat_col].between(-90, 90, inclusive="both")
    ].copy()
    if not len(data):
        raise ValueError("No finite occurrence coordinates")
    return data, lon_col, lat_col


def _minimal_longitude_interval(values: np.ndarray, *, buffer_degrees: float) -> tuple[float, float]:
    lon = np.asarray(values, dtype=float)
    lon = lon[np.isfinite(lon)]
    if lon.size == 0:
        raise ValueError("No finite longitudes")
    if buffer_degrees < 0:
        raise ValueError("buffer_degrees must be >= 0")
    if lon.size == 1:
        west360 = (lon[0] % 360.0) - buffer_degrees
        east360 = (lon[0] % 360.0) + buffer_degrees
        arc = 2 * buffer_degrees
    else:
        x = np.sort(np.mod(lon, 360.0))
        wrapped = np.concatenate([x, [x[0] + 360.0]])
        gaps = np.diff(wrapped)
        i = int(np.argmax(gaps))
        start = x[(i + 1) % len(x)]
        end = x[i]
        if end < start:
            end += 360.0
        west360 = start - buffer_degrees
        east360 = end + buffer_degrees
        arc = east360 - west360
    if arc >= 360.0:
        return -180.0, 180.0

    def signed(value: float) -> float:
        out = ((value + 180.0) % 360.0) - 180.0
        return 180.0 if np.isclose(out, -180.0) and value > 0 else float(out)

    return signed(west360), signed(east360)


def bounds_from_occurrences(
    frame: pd.DataFrame,
    *,
    buffer_degrees: float = 2.0,
    group_col: str = "species",
) -> list[SnapshotBounds]:
    """Return one dateline-aware query box per focal species/group.

    This is useful for compact-range taxa. For widespread taxa, prefer
    :func:`tiled_bounds_from_occurrences` so one species-wide bounding box does
    not accidentally expand a target-group extraction to continental/global
    scale.
    """
    if buffer_degrees < 0:
        raise ValueError("buffer_degrees must be >= 0")
    data, lon_col, lat_col = _finite_coordinates(frame)
    groups = data.groupby(group_col, sort=True) if group_col in data else [("all", data)]
    boxes: list[SnapshotBounds] = []
    for _, group in groups:
        west, east = _minimal_longitude_interval(group[lon_col].to_numpy(float), buffer_degrees=buffer_degrees)
        south = max(-90.0, float(group[lat_col].min()) - buffer_degrees)
        north = min(90.0, float(group[lat_col].max()) + buffer_degrees)
        boxes.append(SnapshotBounds(west=west, east=east, south=south, north=north))
    return boxes


def _expand_tile_longitude(west: float, east: float, buffer_degrees: float) -> tuple[float, float]:
    raw_west = west - buffer_degrees
    raw_east = east + buffer_degrees
    if raw_east - raw_west >= 360:
        return -180.0, 180.0
    if raw_west < -180:
        return float(raw_west + 360.0), float(raw_east)
    if raw_east > 180:
        return float(raw_west), float(raw_east - 360.0)
    return float(raw_west), float(raw_east)


def _distance_buffer_degrees(*, south: float, north: float, buffer_km: float) -> tuple[float, float]:
    """Return conservative latitude/longitude degree buffers for a distance buffer.

    Longitude degrees shrink toward the poles.  The conversion therefore uses
    the largest absolute latitude reached after adding the latitude buffer. This
    intentionally over-expands the rectangular cloud prefilter so it cannot trim
    candidates that a downstream haversine occurrence-buffer M would admit.
    """
    if buffer_km <= 0:
        raise ValueError("buffer_km must be > 0")
    lat_buffer = float(buffer_km) / _KM_PER_LAT_DEGREE
    max_abs_lat = min(89.999, max(abs(south - lat_buffer), abs(north + lat_buffer)))
    cosine = math.cos(math.radians(max_abs_lat))
    if cosine <= 1e-6:
        lon_buffer = 180.0
    else:
        lon_buffer = min(180.0, float(buffer_km) / (_KM_PER_LAT_DEGREE * cosine))
    return lat_buffer, lon_buffer


def tiled_bounds_from_occurrences(
    frame: pd.DataFrame,
    *,
    tile_degrees: float = 5.0,
    buffer_degrees: float = 3.0,
    buffer_km: float | None = None,
) -> list[SnapshotBounds]:
    """Return buffered query boxes for only geographic tiles containing focal records.

    This is a cloud-extraction prefilter, not the biological accessible area M.
    It avoids materializing a whole species-wide bounding box for widespread
    plants. If ``buffer_km`` is supplied, it overrides ``buffer_degrees`` and
    expands each occupied tile conservatively enough to contain a downstream
    spherical-distance M of that radius, including at high latitudes.
    """
    if not 0 < tile_degrees <= 180:
        raise ValueError("tile_degrees must be in (0, 180]")
    if buffer_degrees < 0:
        raise ValueError("buffer_degrees must be >= 0")
    if buffer_km is not None and buffer_km <= 0:
        raise ValueError("buffer_km must be > 0")
    data, lon_col, lat_col = _finite_coordinates(frame)

    nx = int(math.ceil(360.0 / tile_degrees))
    ny = int(math.ceil(180.0 / tile_degrees))
    lon = data[lon_col].to_numpy(float)
    lat = data[lat_col].to_numpy(float)
    ix = np.floor((lon + 180.0) / tile_degrees).astype(int)
    iy = np.floor((lat + 90.0) / tile_degrees).astype(int)
    ix = np.clip(ix, 0, nx - 1)
    iy = np.clip(iy, 0, ny - 1)

    boxes: list[SnapshotBounds] = []
    seen: set[tuple[float, float, float, float]] = set()
    for x, y in sorted(set(zip(ix.tolist(), iy.tolist(), strict=True))):
        west = -180.0 + x * tile_degrees
        east = min(180.0, west + tile_degrees)
        south = -90.0 + y * tile_degrees
        north = min(90.0, south + tile_degrees)
        if buffer_km is None:
            lat_buffer = lon_buffer = float(buffer_degrees)
        else:
            lat_buffer, lon_buffer = _distance_buffer_degrees(
                south=south,
                north=north,
                buffer_km=float(buffer_km),
            )
        west, east = _expand_tile_longitude(west, east, lon_buffer)
        south = max(-90.0, south - lat_buffer)
        north = min(90.0, north + lat_buffer)
        key = (round(west, 10), round(east, 10), round(south, 10), round(north, 10))
        if key in seen:
            continue
        seen.add(key)
        boxes.append(SnapshotBounds(west=west, east=east, south=south, north=north))
    return boxes
