from pathlib import Path

import pandas as pd
import pytest

from sdmr.pilot_grid_cli import read_pilot_grid


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
