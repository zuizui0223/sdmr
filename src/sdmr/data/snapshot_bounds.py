"""Build multiple spatial query boxes from focal occurrence subsets."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .snapshot import SnapshotBounds


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
        # Keep +180 rather than -180 for a west boundary when numerically exact.
        return 180.0 if np.isclose(out, -180.0) and value > 0 else float(out)

    return signed(west360), signed(east360)


def bounds_from_occurrences(
    frame: pd.DataFrame,
    *,
    buffer_degrees: float = 2.0,
    group_col: str = "species",
) -> list[SnapshotBounds]:
    """Return one dateline-aware query box per focal species/group."""
    if buffer_degrees < 0:
        raise ValueError("buffer_degrees must be >= 0")
    lon_col = "longitude" if "longitude" in frame else "decimallongitude"
    lat_col = "latitude" if "latitude" in frame else "decimallatitude"
    if lon_col not in frame or lat_col not in frame:
        raise KeyError("frame requires longitude/latitude or decimallongitude/decimallatitude")
    data = frame.copy()
    data[lon_col] = pd.to_numeric(data[lon_col], errors="coerce")
    data[lat_col] = pd.to_numeric(data[lat_col], errors="coerce")
    data = data.dropna(subset=[lon_col, lat_col])
    if not len(data):
        raise ValueError("No finite occurrence coordinates")

    groups = data.groupby(group_col, sort=True) if group_col in data else [("all", data)]
    boxes: list[SnapshotBounds] = []
    for _, group in groups:
        west, east = _minimal_longitude_interval(group[lon_col].to_numpy(float), buffer_degrees=buffer_degrees)
        south = max(-90.0, float(group[lat_col].min()) - buffer_degrees)
        north = min(90.0, float(group[lat_col].max()) + buffer_degrees)
        boxes.append(SnapshotBounds(west=west, east=east, south=south, north=north))
    return boxes
