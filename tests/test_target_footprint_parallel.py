import pandas as pd

from sdmr.target_footprint_parallel_cli import _chunk_files


def test_chunk_files_cover_sorted_catalog_exactly_once():
    files = [f"s3://bucket/{i:06d}" for i in range(9705)]
    chunks = [_chunk_files(files, i, 8) for i in range(8)]
    assert sum(chunks, []) == files
    assert sum(len(chunk) for chunk in chunks) == len(files)
    assert len({item for chunk in chunks for item in chunk}) == len(files)
    assert max(len(chunk) for chunk in chunks) - min(len(chunk) for chunk in chunks) <= 1


def _min_per_cell(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(["gx", "gy", "gbifid"], kind="mergesort")
    return ordered.drop_duplicates(["gx", "gy"], keep="first").reset_index(drop=True)


def test_chunk_min_then_global_min_equals_monolithic_min():
    frame = pd.DataFrame(
        [
            {"shard": 0, "gx": 1, "gy": 1, "gbifid": 70, "lon": 1.1, "lat": 1.2},
            {"shard": 0, "gx": 2, "gy": 2, "gbifid": 40, "lon": 2.1, "lat": 2.2},
            {"shard": 1, "gx": 1, "gy": 1, "gbifid": 30, "lon": 1.3, "lat": 1.4},
            {"shard": 2, "gx": 2, "gy": 2, "gbifid": 10, "lon": 2.3, "lat": 2.4},
            {"shard": 3, "gx": 1, "gy": 1, "gbifid": 50, "lon": 1.5, "lat": 1.6},
            {"shard": 3, "gx": 3, "gy": 3, "gbifid": 20, "lon": 3.1, "lat": 3.2},
        ]
    )
    monolithic = _min_per_cell(frame).sort_values(["gx", "gy"]).reset_index(drop=True)
    partials = []
    for shard_group in ([0, 1], [2, 3]):
        partials.append(_min_per_cell(frame.loc[frame["shard"].isin(shard_group)]))
    reduced = _min_per_cell(pd.concat(partials, ignore_index=True)).sort_values(["gx", "gy"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        reduced[["gx", "gy", "gbifid", "lon", "lat"]],
        monolithic[["gx", "gy", "gbifid", "lon", "lat"]],
    )
