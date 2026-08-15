import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from sdmr.data.raster import _sample_band_blockwise


class _ReadCountingDataset:
    def __init__(self, src):
        self._src = src
        self.transform = src.transform
        self.height = src.height
        self.width = src.width
        self.block_shapes = src.block_shapes
        self.read_calls = 0

    def read(self, *args, **kwargs):
        self.read_calls += 1
        return self._src.read(*args, **kwargs)


def _dataset():
    data = np.arange(256 * 256, dtype=np.float32).reshape(256, 256)
    mem = MemoryFile()
    src = mem.open(
        driver="GTiff",
        width=256,
        height=256,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-10.0, 10.0, 0.1, 0.1),
        tiled=True,
        blockxsize=64,
        blockysize=64,
    )
    src.write(data, 1)
    return mem, src, data


def test_block_grouped_sampling_exactly_matches_rasterio_sample_for_in_bounds_points():
    mem, src, _ = _dataset()
    try:
        rng = np.random.default_rng(20260815)
        rows = rng.integers(0, 256, 500)
        cols = rng.integers(0, 256, 500)
        # Repeat some coordinates explicitly; order and duplicates must survive.
        rows = np.r_[rows, rows[:25]]
        cols = np.r_[cols, cols[:25]]
        x = -10.0 + (cols + 0.5) * 0.1
        y = 10.0 - (rows + 0.5) * 0.1
        direct = np.array(
            [float(value[0]) for value in src.sample(list(zip(x, y, strict=True)))],
            dtype=float,
        )
        grouped = _sample_band_blockwise(src, x, y)
        np.testing.assert_array_equal(grouped, direct)
    finally:
        src.close()
        mem.close()


def test_block_grouped_sampling_reads_each_occupied_native_block_once():
    mem, src, data = _dataset()
    try:
        # Four points in block (0,0), two in block (1,1), one in block (3,3).
        rows = np.array([1, 2, 40, 63, 65, 90, 250])
        cols = np.array([1, 20, 45, 63, 65, 100, 250])
        x = -10.0 + (cols + 0.5) * 0.1
        y = 10.0 - (rows + 0.5) * 0.1
        counted = _ReadCountingDataset(src)
        grouped = _sample_band_blockwise(counted, x, y)
        np.testing.assert_array_equal(grouped, data[rows, cols].astype(float))
        assert counted.read_calls == 3
        assert counted.read_calls < len(rows)
    finally:
        src.close()
        mem.close()


def test_block_grouped_sampling_leaves_out_of_bounds_coordinates_nan():
    mem, src, _ = _dataset()
    try:
        x = np.array([-9.95, 1000.0, -1000.0])
        y = np.array([9.95, 1000.0, -1000.0])
        values = _sample_band_blockwise(src, x, y)
        assert np.isfinite(values[0])
        assert np.isnan(values[1])
        assert np.isnan(values[2])
    finally:
        src.close()
        mem.close()
