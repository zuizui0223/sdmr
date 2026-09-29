from sdmr.process_id.fresh.soil_recovery import (
    EXPECTED_LOCATION_ROWS,
    SOIL_PREDICTORS,
    SOIL_SHARD_COUNT,
    spatial_shard_bounds,
)


def test_soil_recovery_freezes_four_layers_and_16_spatial_shards():
    assert len(SOIL_PREDICTORS) == 4
    assert len(set(SOIL_PREDICTORS)) == 4
    assert SOIL_SHARD_COUNT == 16


def test_spatial_shards_cover_exact_location_index_once():
    ranges = [
        spatial_shard_bounds(EXPECTED_LOCATION_ROWS, i, SOIL_SHARD_COUNT)
        for i in range(SOIL_SHARD_COUNT)
    ]
    assert ranges[0][0] == 0
    assert ranges[-1][1] == EXPECTED_LOCATION_ROWS
    assert all(a[1] == b[0] for a, b in zip(ranges, ranges[1:]))
    assert sum(stop - start for start, stop in ranges) == EXPECTED_LOCATION_ROWS
    assert max(stop - start for start, stop in ranges) - min(
        stop - start for start, stop in ranges
    ) <= 1


def test_spatial_shard_bounds_reject_invalid_indices():
    import pytest

    with pytest.raises(ValueError):
        spatial_shard_bounds(10, -1, 2)
    with pytest.raises(ValueError):
        spatial_shard_bounds(10, 2, 2)
    with pytest.raises(ValueError):
        spatial_shard_bounds(1, 0, 2)
