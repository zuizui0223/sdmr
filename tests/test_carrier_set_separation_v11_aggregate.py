from pathlib import Path

import pandas as pd

from sdmr.carrier_set_separation_v11_development import PAIR_COLUMNS, _read_csv


def test_v11_empty_pair_csv_keeps_schema(tmp_path: Path):
    path = tmp_path / "pair_audit.csv"
    pd.DataFrame(columns=PAIR_COLUMNS).to_csv(path, index=False)
    frame = _read_csv(path, PAIR_COLUMNS)
    assert list(frame.columns) == PAIR_COLUMNS
    assert frame.empty


def test_v11_truly_empty_csv_fails_closed_to_declared_schema(tmp_path: Path):
    path = tmp_path / "pair_audit.csv"
    path.write_text("")
    frame = _read_csv(path, PAIR_COLUMNS)
    assert list(frame.columns) == PAIR_COLUMNS
    assert frame.empty
