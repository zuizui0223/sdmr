import pandas as pd
import pytest

from sdmr.data.snapshot_bounds import bounds_from_occurrences, tiled_bounds_from_occurrences


def test_bounds_from_occurrences_is_dateline_aware_and_grouped():
    frame = pd.DataFrame(
        {
            "species": ["cross", "cross", "normal", "normal"],
            "decimallongitude": [179.0, -179.0, 10.0, 12.0],
            "decimallatitude": [0.0, 1.0, 20.0, 22.0],
        }
    )
    boxes = bounds_from_occurrences(frame, buffer_degrees=1.0)
    assert len(boxes) == 2
    cross, normal = boxes
    assert cross.west > cross.east
    assert cross.west >= 177.9
    assert cross.east <= -177.9
    assert normal.west < normal.east
    assert normal.south == 19.0
    assert normal.north == 23.0


def test_tiled_bounds_avoid_species_wide_global_bbox_and_support_dateline():
    frame = pd.DataFrame(
        {
            "species": ["widespread"] * 4,
            "longitude": [-150.0, 10.0, 179.5, -179.5],
            "latitude": [40.0, 50.0, 0.0, 0.0],
        }
    )
    boxes = tiled_bounds_from_occurrences(frame, tile_degrees=5.0, buffer_degrees=3.0)
    assert 3 <= len(boxes) <= 4
    assert all((box.east - box.west) < 20 or box.west > box.east for box in boxes)
    assert any(box.west > box.east for box in boxes)


def test_tiled_bounds_deduplicate_multiple_records_in_same_tile():
    frame = pd.DataFrame({"longitude": [10.1, 10.2, 10.3], "latitude": [20.1, 20.2, 20.3]})
    boxes = tiled_bounds_from_occurrences(frame, tile_degrees=5.0, buffer_degrees=1.0)
    assert len(boxes) == 1
    box = boxes[0]
    assert box.west == 9.0
    assert box.east == 16.0
    assert box.south == 19.0
    assert box.north == 26.0


def test_distance_buffer_expands_longitude_more_at_high_latitude():
    equator = tiled_bounds_from_occurrences(
        pd.DataFrame({"longitude": [12.0], "latitude": [2.0]}),
        tile_degrees=5.0,
        buffer_km=300.0,
    )[0]
    high_lat = tiled_bounds_from_occurrences(
        pd.DataFrame({"longitude": [12.0], "latitude": [72.0]}),
        tile_degrees=5.0,
        buffer_km=300.0,
    )[0]
    equator_width = equator.east - equator.west
    high_width = high_lat.east - high_lat.west
    assert high_width > equator_width
    assert equator.south == pytest.approx(-300 / 111.195)
    assert high_lat.north > 77.0


def test_distance_buffer_rejects_nonpositive_km():
    frame = pd.DataFrame({"longitude": [0.0], "latitude": [0.0]})
    with pytest.raises(ValueError, match="buffer_km must be > 0"):
        tiled_bounds_from_occurrences(frame, buffer_km=0)
