import numpy as np

from sdmr.validation import make_spatial_partition


def test_spatial_partition_holds_out_whole_blocks():
    lon = np.linspace(-30, 30, 80)
    lat = 10 * np.sin(np.deg2rad(lon * 3))
    part = make_spatial_partition(lon, lat, lon + 0.2, lat + 0.2, n_blocks=8, random_state=3)
    assert set(part.train_blocks).isdisjoint(part.test_blocks)
    assert set(np.unique(part.presence_blocks)) == set(part.train_blocks) | set(part.test_blocks)
    assert 3 <= len(part.test_blocks) <= 5
