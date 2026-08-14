import numpy as np
import pytest

from sdmr.data import RasterLayerSpec, probe_raster_layers


def test_raster_probe_reports_valid_and_invalid_layers(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    path = tmp_path / "valid.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=3,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
    ) as dst:
        dst.write(np.ones((2, 3), dtype="float32"), 1)

    probe = probe_raster_layers(
        [
            RasterLayerSpec("ok", str(path), source="synthetic", version="1"),
            RasterLayerSpec("missing", str(tmp_path / "missing.tif"), source="synthetic", version="1"),
        ]
    ).set_index("predictor")

    assert probe.loc["ok", "status"] == "ok"
    assert probe.loc["ok", "width"] == 3
    assert probe.loc["ok", "height"] == 2
    assert probe.loc["ok", "crs"] == "EPSG:4326"
    assert probe.loc["missing", "status"] == "failed"
    assert "RasterioIOError" in probe.loc["missing", "error"]
