"""Raster extraction and provenance for local/COG environmental layers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import os
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
    """Open every raster far enough to validate URI/driver/CRS metadata."""
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
        except Exception as exc:  # pragma: no cover
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return pd.DataFrame(rows)


def _sample_band_blockwise(src, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Sample band 1 exactly by pixel while reading each internal block once."""
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
    else:
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
        block = src.read(1, window=Window(col0, row0, width, height), masked=False)
        source_rows = vrows[local_positions] - row0
        source_cols = vcols[local_positions] - col0
        result[valid_idx[local_positions]] = np.asarray(
            block[source_rows, source_cols], dtype=float
        )
    return result


def _resolve_layer_jobs() -> int:
    raw = os.environ.get("SDMR_RASTER_LAYER_JOBS", "1").strip() or "1"
    try:
        jobs = int(raw)
    except ValueError as exc:
        raise ValueError("SDMR_RASTER_LAYER_JOBS must be an integer >= 1") from exc
    if jobs < 1:
        raise ValueError("SDMR_RASTER_LAYER_JOBS must be >= 1")
    return jobs


def _extract_layer_values(
    rasterio,
    CRS,
    transform,
    layer: RasterLayerSpec,
    lon: np.ndarray,
    lat: np.ndarray,
    finite: np.ndarray,
    *,
    checksum_local_files: bool,
) -> tuple[str, np.ndarray, dict[str, object]]:
    """Extract one layer using a private raster handle; safe for layer threads."""
    if not layer.predictor:
        raise ValueError("Raster predictor name must not be empty")
    values = np.full(len(lon), np.nan, dtype=float)
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
            provenance = {
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
    return layer.predictor, values, provenance


def extract_raster_values(
    points: pd.DataFrame,
    layers: Sequence[RasterLayerSpec],
    *,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    checksum_local_files: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract environmental values and return a raster-provenance ledger.

    Native raster blocks are grouped for exact pixel sampling. Independent
    raster layers may additionally be read in parallel by setting
    ``SDMR_RASTER_LAYER_JOBS``. The default is one worker; ``executor.map``
    preserves manifest order, so sequential and parallel outputs have identical
    column/provenance ordering.
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
    layer_list = list(layers)
    jobs = _resolve_layer_jobs()

    def work(layer: RasterLayerSpec):
        return _extract_layer_values(
            rasterio,
            CRS,
            transform,
            layer,
            lon,
            lat,
            finite,
            checksum_local_files=checksum_local_files,
        )

    if jobs == 1:
        extracted = [work(layer) for layer in layer_list]
    else:
        with ThreadPoolExecutor(max_workers=jobs, thread_name_prefix="sdmr-raster") as executor:
            extracted = list(executor.map(work, layer_list))

    provenance_rows: list[dict[str, object]] = []
    for predictor, values, provenance in extracted:
        out[predictor] = values
        provenance_rows.append(provenance)
    return out, pd.DataFrame(provenance_rows)
