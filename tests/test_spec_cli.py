from pathlib import Path

import pandas as pd
import pytest

from sdmr.spec_cli import _read_specifications


def test_spec_cli_resolves_relative_paths_and_requires_unique_names(tmp_path: Path):
    occ = pd.DataFrame({"species": ["a"], "longitude": [0.0], "latitude": [0.0]})
    bg = pd.DataFrame({"species": ["a"], "longitude": [1.0], "latitude": [1.0]})
    occ.to_csv(tmp_path / "occ.csv", index=False)
    bg.to_csv(tmp_path / "bg.csv", index=False)
    config = pd.DataFrame({"name": ["buffer300"], "occurrences": ["occ.csv"], "background": ["bg.csv"]})
    config.to_csv(tmp_path / "specs.csv", index=False)

    loaded = _read_specifications(str(tmp_path / "specs.csv"))
    assert list(loaded) == ["buffer300"]
    assert loaded["buffer300"][0].equals(occ)
    assert loaded["buffer300"][1].equals(bg)

    duplicate = pd.concat([config, config], ignore_index=True)
    duplicate.to_csv(tmp_path / "duplicate.csv", index=False)
    with pytest.raises(ValueError, match="unique"):
        _read_specifications(str(tmp_path / "duplicate.csv"))
