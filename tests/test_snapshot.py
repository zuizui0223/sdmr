import pytest

from sdmr.data.snapshot import SnapshotBounds, build_snapshot_filter_sql, gbif_snapshot_s3_uri


def test_snapshot_uri_is_versioned_monthly_public_s3_path():
    assert gbif_snapshot_s3_uri("2026-08-01") == (
        "s3://gbif-open-data-us-east-1/occurrence/2026-08-01/occurrence.parquet/*"
    )
    with pytest.raises(ValueError, match="first day"):
        gbif_snapshot_s3_uri("2026-08-14")


def test_snapshot_filter_supports_focal_taxa_and_dateline_bounds():
    sql = build_snapshot_filter_sql(
        species_names=["O'Brien plant", "Alpha beta"],
        kingdom="Plantae",
        bounds=[SnapshotBounds(west=170, east=-170, south=-10, north=10)],
    )
    assert "species IN ('Alpha beta','O''Brien plant')" in sql
    assert "kingdom = 'Plantae'" in sql
    assert "decimallongitude >= 170.0 OR decimallongitude <= -170.0" in sql
    assert "decimallatitude IS NOT NULL" in sql


def test_snapshot_filter_refuses_unbounded_global_extract():
    with pytest.raises(ValueError, match="at least one taxonomic/spatial filter"):
        build_snapshot_filter_sql(require_coordinates=True)
