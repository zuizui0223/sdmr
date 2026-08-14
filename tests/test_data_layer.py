import numpy as np
import pandas as pd
import pytest

from sdmr.data import (
    GBIFBulkDownloadRequired,
    OccurrenceAdmissionConfig,
    RasterLayerSpec,
    admit_occurrences,
    bbox_membership,
    extract_raster_values,
    fetch_occurrence_search,
    match_taxon,
    sample_target_group_background,
)


def test_gbif_match_and_pilot_pagination_are_auditable():
    def match_json(url, params):
        assert url.endswith("/v2/species/match")
        assert params["scientificName"] == "Plantus example"
        return {
            "usage": {"key": "123", "canonicalName": "Plantus example", "rank": "SPECIES", "status": "ACCEPTED"}
        }

    matched = match_taxon("Plantus example", get_json=match_json)
    assert matched.taxon_key == "123"

    calls = []

    def occurrence_json(url, params):
        calls.append(dict(params))
        offset = int(params["offset"])
        all_rows = [
            {
                "key": i,
                "taxonKey": 123,
                "species": "Plantus example",
                "decimalLongitude": float(i),
                "decimalLatitude": 10.0,
                "occurrenceStatus": "PRESENT",
            }
            for i in range(5)
        ]
        page = all_rows[offset : offset + int(params["limit"])]
        return {"count": 5, "results": page, "endOfRecords": offset + len(page) >= 5}

    result = fetch_occurrence_search(123, max_records=None, page_size=2, get_json=occurrence_json)
    assert result.retrieved_count == 5
    assert result.truncated is False
    assert len(result.query_sha256) == 64
    assert [c["limit"] for c in calls] == [2, 2, 2]
    assert set(result.records.columns) >= {"gbifID", "longitude", "latitude", "species"}


def test_gbif_full_search_refuses_queries_above_search_hard_limit():
    def occurrence_json(url, params):
        return {"count": 100_001, "results": [], "endOfRecords": False}

    with pytest.raises(GBIFBulkDownloadRequired):
        fetch_occurrence_search(123, max_records=None, get_json=occurrence_json)


def test_occurrence_admission_records_reasons_and_deduplicates():
    data = pd.DataFrame(
        {
            "species": ["a", "a", "a", "a", "a"],
            "longitude": [10, 10, 200, 20, 30],
            "latitude": [5, 5, 0, 6, 7],
            "coordinateUncertaintyInMeters": [100, 100, 100, 5000, 100],
            "year": [2020, 2020, 2020, 2020, 1990],
            "basisOfRecord": ["HUMAN_OBSERVATION"] * 5,
            "occurrenceStatus": ["PRESENT"] * 5,
        }
    )
    result = admit_occurrences(
        data,
        config=OccurrenceAdmissionConfig(max_coordinate_uncertainty_m=1000, min_year=2000),
    )
    assert len(result.accepted) == 1
    reasons = ";".join(result.rejected["rejection_reason"].tolist())
    assert "duplicate_coordinate" in reasons
    assert "invalid_coordinate" in reasons
    assert "coordinate_uncertainty_too_high" in reasons
    assert "year_before_min" in reasons
    assert result.ledger.set_index("metric").loc["accepted", "count"] == 1


def test_target_group_background_respects_declared_m_and_excludes_presence_cells():
    focal = pd.DataFrame({"species": ["focal"], "longitude": [0.0], "latitude": [0.0]})
    pool = pd.DataFrame(
        {
            "species": ["x", "y", "z", "q"],
            "longitude": [0.0, 1.0, 2.0, 50.0],
            "latitude": [0.0, 1.0, 2.0, 50.0],
        }
    )
    mask = bbox_membership(pool, west=-5, east=5, south=-5, north=5)
    bg = sample_target_group_background(
        focal, pool, m_mask=mask, n_points=10, cell_size_degrees=0.5, focal_species="focal", random_state=1
    )
    assert set(bg["background_source_species"]) == {"y", "z"}
    assert set(bg["species"]) == {"focal"}
    assert bg["longitude"].max() <= 5


def test_raster_extraction_applies_metadata_scale_offset_and_provenance(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    path = tmp_path / "tiny.tif"
    arr = np.array([[10, 20], [30, 40]], dtype=np.int16)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=arr.dtype,
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
        nodata=-9999,
    ) as dst:
        dst.write(arr, 1)
        dst.scales = (0.1,)
        dst.offsets = (-1.0,)

    points = pd.DataFrame({"longitude": [0.5, 1.5], "latitude": [1.5, 0.5]})
    values, provenance = extract_raster_values(
        points,
        [RasterLayerSpec("climate", str(path), source="synthetic", version="1")],
    )
    assert np.allclose(values["climate"], [0.0, 3.0])
    assert provenance.loc[0, "sha256"]
    assert provenance.loc[0, "scale"] == pytest.approx(0.1)
    assert provenance.loc[0, "offset"] == pytest.approx(-1.0)
