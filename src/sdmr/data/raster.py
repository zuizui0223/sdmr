"""Raster extraction and provenance for local/COG environmental layers."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RasterLayerSpec:
    predictor: str
    uri: str
    source: str = ""
    version: str = ""
    scale: float | None = None
    offset: float | None = None


def sha256_file(path: str | Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _raster_env(rasterio, uri: str):
    """Use range-read friendly GDAL settings only for HTTP(S) COGs."""
    if str(uri).lower().startswith(("http://", "https://")):
        return rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
            GDAL_HTTP_MULTIRANGE="YES",
            VSI_CACHE="TRUE",
            VSI_CACHE_SIZE="67108864",
        )
    return nullcontext()


def probe_raster_layers(layers: Sequence[RasterLayerSpec]) -> pd.DataFrame:
    """Open every raster far enough to validate URI/driver/CRS metadata.

    This is intentionally cheaper than sampling values. It is useful as a
    preflight before an expensive DOI-backed Product-A run: a broken CHELSA URI
    is discovered before occurrence/snapshot materialization or model fitting.
    Failures are returned in the ledger rather than hidden.
    """
    try:
        import rasterio
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Raster probing requires rasterio; install sdmr[geo].") from exc

    rows: list[dict[str, object]] = []
    for layer in layers:
        row: dict[str, object] = {
            "predictor": layer.predictor,
            "source": layer.source,
            "version": layer.version,
            "uri": layer.uri,
            "status": "failed",
            "error": "",
        }
        try:
            with _raster_env(rasterio, layer.uri):
                with rasterio.open(layer.uri) as src:
                    if src.crs is None:
                        raise ValueError("raster has no CRS")
                    row.update(
                        {
                            "status": "ok",
                            "driver": str(src.driver),
                            "crs": str(src.crs),
                            "width": int(src.width),
                            "height": int(src.height),
                            "resolution_x": float(src.res[0]),
                            "resolution_y": float(src.res[1]),
                            "nodata": src.nodata,
                        }
                    )
        except Exception as exc:  # pragma: no cover - exercised with invalid local paths in tests
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return pd.DataFrame(rows)


def _sample_band_blockwise(src, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Sample band 1 exactly by pixel while reading each internal block once.

    ``DatasetReader.sample`` issues tiny windows in point order. For remote COGs,
    many scattered points can therefore create a large number of HTTP range
    operations even though multiple points occupy the same compressed tile.
    This helper computes the exact raster row/column for every coordinate,
    groups points by the source's native internal block, reads each occupied
    block once, and returns the identical nearest-pixel values in original point
    order. Coordinates outside the raster extent remain NaN.
    """
    from rasterio.transform import rowcol
    from rasterio.windows import Window

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    result = np.full(x.size, np.nan, dtype=float)
    if x.size == 0:
        return result

    rows, cols = rowcol(src.transform, x, y)
    rows = np.asarray(rows, dtype=np.int64)
    cols = np.asarray(cols, dtype=np.int64)
    valid = (
        (rows >= 0)
        & (rows < int(src.height))
        & (cols >= 0)
        & (cols < int(src.width))
    )
    if not np.any(valid):
        return result

    valid_idx = np.flatnonzero(valid)
    vrows = rows[valid]
    vcols = cols[valid]
    if src.block_shapes:
        block_height, block_width = (int(v) for v in src.block_shapes[0])
    else:  # defensive fallback for unusual untiled drivers
        block_height = min(256, int(src.height))
        block_width = min(256, int(src.width))
    n_block_cols = (int(src.width) + block_width - 1) // block_width
    block_rows = vrows // block_height
    block_cols = vcols // block_width
    block_keys = block_rows * n_block_cols + block_cols

    order = np.argsort(block_keys, kind="mergesort")
    sorted_keys = block_keys[order]
    starts = np.r_[0, np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]) + 1]
    ends = np.r_[starts[1:], len(order)]

    for start, end in zip(starts, ends, strict=True):
        local_positions = order[start:end]
        first = local_positions[0]
        block_row = int(block_rows[first])
        block_col = int(block_cols[first])
        row0 = block_row * block_height
        col0 = block_col * block_width
        height = min(block_height, int(src.height) - row0)
        width = min(block_width, int(src.width) - col0)
        block = src.read(
            1,
            window=Window(col0, row0, width, height),
            masked=False,
        )
        source_rows = vrows[local_positions] - row0
        source_cols = vcols[local_positions] - col0
        result[valid_idx[local_positions]] = np.asarray(
            block[source_rows, source_cols], dtype=float
        )
    return result


def extract_raster_values(
    points: pd.DataFrame,
    layers: Sequence[RasterLayerSpec],
    *,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    checksum_local_files: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract environmental values and return a raster-provenance ledger.

    Raster scale/offset metadata are applied unless explicitly overridden in the
    layer spec. Local files can be SHA-256 fingerprinted; remote COG URIs retain
    the URI and raster metadata but are not downloaded solely for checksumming.
    Point values are read by native raster block to reduce remote COG I/O while
    preserving exact nearest-pixel sampling semantics.
    """

    try:
        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import transform
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Raster extraction requires rasterio; install sdmr[geo].") from exc

    if lon_col not in points or lat_col not in points:
        raise KeyError(f"points must contain {lon_col!r} and {lat_col!r}")
    out = points.copy().reset_index(drop=True)
    lon = pd.to_numeric(out[lon_col], errors="coerce").to_numpy(float)
    lat = pd.to_numeric(out[lat_col], errors="coerce").to_numpy(float)
    finite = np.isfinite(lon) & np.isfinite(lat)
    provenance_rows: list[dict[str, object]] = []

    for layer in layers:
        if not layer.predictor:
            raise ValueError("Raster predictor name must not be empty")
        values = np.full(len(out), np.nan, dtype=float)
        with _raster_env(rasterio, layer.uri):
            with rasterio.open(layer.uri) as src:
                if src.crs is None:
                    raise ValueError(f"Raster {layer.uri!r} has no CRS")
                x = lon[finite]
                y = lat[finite]
                if src.crs != CRS.from_epsg(4326):
                    x_t, y_t = transform(CRS.from_epsg(4326), src.crs, x.tolist(), y.tolist())
                    x_sample = np.asarray(x_t, dtype=float)
                    y_sample = np.asarray(y_t, dtype=float)
                else:
                    x_sample = np.asarray(x, dtype=float)
                    y_sample = np.asarray(y, dtype=float)
                sampled = _sample_band_blockwise(src, x_sample, y_sample)
                nodata = src.nodata
                if nodata is not None:
                    sampled[np.isclose(sampled, float(nodata), equal_nan=True)] = np.nan
                metadata_scale = float(src.scales[0]) if src.scales else 1.0
                metadata_offset = float(src.offsets[0]) if src.offsets else 0.0
                scale = metadata_scale if layer.scale is None else float(layer.scale)
                offset = metadata_offset if layer.offset is None else float(layer.offset)
                sampled = sampled * scale + offset
                values[finite] = sampled

                local = Path(layer.uri)
                is_local = local.exists() and local.is_file()
                provenance_rows.append(
                    {
                        "predictor": layer.predictor,
                        "source": layer.source,
                        "version": layer.version,
                        "uri": layer.uri,
                        "sha256": sha256_file(local) if checksum_local_files and is_local else "",
                        "crs": str(src.crs),
                        "width": int(src.width),
                        "height": int(src.height),
                        "resolution_x": float(src.res[0]),
                        "resolution_y": float(src.res[1]),
                        "nodata": nodata,
                        "scale": scale,
                        "offset": offset,
                        "sampling_engine": "native_block_grouped_exact_pixel",
                    }
                )
        out[layer.predictor] = values
    return out, pd.DataFrame(provenance_rows)
