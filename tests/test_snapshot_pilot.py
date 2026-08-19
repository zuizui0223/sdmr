from pathlib import Path

import pandas as pd
import pytest

from sdmr.data.raster import sha256_file
from sdmr.snapshot_pilot_cli import _read_snapshot_provenance


def test_snapshot_pilot_provenance_verifies_materialized_subset_sha(tmp_path: Path):
    subset = tmp_path / "subset.bin"
    subset.write_bytes(b"stable snapshot subset")
    provenance = pd.DataFrame(
        [
            {
                "source_type": "gbif_monthly_cloud_snapshot",
                "snapshot_date": "2026-08-01",
                "snapshot_doi": "10.15468/example",
                "remote_uri": "s3://bucket/path/*",
                "query_sha256": "q" * 64,
                "sha256": sha256_file(subset),
            }
        ]
    )
    path = tmp_path / "provenance.csv"
    provenance.to_csv(path, index=False)
    row = _read_snapshot_provenance(str(path), str(subset))
    assert row["snapshot_date"] == "2026-08-01"

    subset.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA mismatch"):
        _read_snapshot_provenance(str(path), str(subset))
