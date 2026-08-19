from pathlib import Path

import pandas as pd
import pytest

from sdmr.data import RasterLayerSpec
from sdmr.pilot_grid_cli import extract_protocol_grid_rasters, read_pilot_grid


def test_pilot_grid_fills_defaults_and_requires_unique_valid_specs(tmp_path: Path):
    path = tmp_path / "grid.csv"
    pd.DataFrame(
        {
            "name": ["bbox2", "buffer300"],
            "m_strategy": ["bbox", "buffer"],
            "bbox_buffer_degrees": [2.0, None],
            "occurrence_buffer_km": [None, 300.0],
            "background_points": [100, 200],
        }
    ).to_csv(path, index=False)
    grid = read_pilot_grid(str(path))
    assert grid["name"].tolist() == ["bbox2", "buffer300"]
    assert grid.loc[0, "bbox_buffer_degrees"] == 2.0
    assert grid.loc[1, "occurrence_buffer_km"] == 300.0
    assert grid["background_cell_size_degrees"].notna().all()

    duplicate = tmp_path / "duplicate.csv"
    pd.DataFrame({"name": ["x", "x"], "m_strategy": ["bbox", "buffer"]}).to_csv(duplicate, index=False)
    with pytest.raises(ValueError, match="unique"):
        read_pilot_grid(str(duplicate))

    invalid = tmp_path / "invalid.csv"
    pd.DataFrame({"name": ["x"], "m_strategy": ["convex_hull"]}).to_csv(invalid, index=False)
    with pytest.raises(ValueError, match="unsupported"):
        read_pilot_grid(str(invalid))


def test_protocol_grid_opens_raster_extraction_once_for_all_tables(monkeypatch):
    occurrence = pd.DataFrame(
        {"species": ["a", "a"], "longitude": [1.0, 2.0], "latitude": [3.0, 4.0], "occ_only": [1, 2]}
    )
    backgrounds = {
        "m150": pd.DataFrame({"species": ["a"], "longitude": [5.0], "latitude": [6.0], "bg_only": [10]}),
        "m500": pd.DataFrame({"species": ["a", "a"], "longitude": [7.0, 8.0], "latitude": [9.0, 10.0], "bg_only": [20, 30]}),
    }
    calls = []

    def fake_extract(points, layers):
        calls.append(points.copy())
        out = points.copy()
        out["bio1"] = range(len(out))
        return out, pd.DataFrame([{"predictor": "bio1", "uri": "synthetic"}])

    monkeypatch.setattr("sdmr.pilot_grid_cli.extract_raster_values", fake_extract)
    occ, bg, provenance = extract_protocol_grid_rasters(
        occurrence,
        backgrounds,
        [RasterLayerSpec("bio1", "synthetic")],
    )

    assert len(calls) == 1
    assert len(calls[0]) == len(occurrence) + sum(map(len, backgrounds.values()))
    assert occ["occ_only"].tolist() == [1, 2]
    assert "bg_only" not in occ.columns
    assert bg["m150"]["bg_only"].tolist() == [10]
    assert bg["m500"]["bg_only"].tolist() == [20, 30]
    assert all("bio1" in frame.columns for frame in [occ, *bg.values()])
    assert provenance.loc[0, "extraction_mode"] == "joint_protocol_grid"
