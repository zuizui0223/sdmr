import pandas as pd

from sdmr.data.snapshot_bounds import bounds_from_occurrences


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
