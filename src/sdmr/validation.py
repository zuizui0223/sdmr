"""Spatial partitioning utilities for occurrence/background data."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupShuffleSplit


@dataclass(frozen=True)
class SpatialPartition:
    presence_blocks: np.ndarray
    background_blocks: np.ndarray
    train_blocks: tuple[int, ...]
    test_blocks: tuple[int, ...]
    centers_xyz: np.ndarray


def lonlat_to_unit_xyz(longitude: np.ndarray, latitude: np.ndarray) -> np.ndarray:
    """Project lon/lat to the 3-D unit sphere for dateline-safe clustering."""

    lon = np.deg2rad(np.asarray(longitude, dtype=float))
    lat = np.deg2rad(np.asarray(latitude, dtype=float))
    cos_lat = np.cos(lat)
    return np.column_stack((cos_lat * np.cos(lon), cos_lat * np.sin(lon), np.sin(lat)))


def make_spatial_partition(
    presence_lon: np.ndarray,
    presence_lat: np.ndarray,
    background_lon: np.ndarray,
    background_lat: np.ndarray,
    *,
    n_blocks: int = 8,
    holdout_fraction: float = 0.5,
    random_state: int = 42,
) -> SpatialPartition:
    """Create whole-region train/test blocks with about half the blocks held out.

    K-means is fitted only to occurrence coordinates so each spatial block is
    anchored by at least one known occurrence. Background points are assigned
    to the nearest occurrence-derived block. Whole blocks, never individual
    points, are then assigned to train or test.
    """

    p_xyz = lonlat_to_unit_xyz(presence_lon, presence_lat)
    b_xyz = lonlat_to_unit_xyz(background_lon, background_lat)
    if p_xyz.shape[0] < 4:
        raise ValueError("At least four occurrence points are required for spatial holdout.")
    if b_xyz.shape[0] < 2:
        raise ValueError("At least two background points are required.")
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between 0 and 1.")

    k = min(int(n_blocks), p_xyz.shape[0])
    if k < 4:
        raise ValueError("n_blocks must allow at least four spatial groups.")

    km = KMeans(n_clusters=k, n_init=20, random_state=random_state)
    p_blocks = km.fit_predict(p_xyz)
    b_blocks = km.predict(b_xyz)

    unique_blocks = np.unique(p_blocks)
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=holdout_fraction,
        random_state=random_state,
    )
    train_idx, test_idx = next(splitter.split(p_xyz, groups=p_blocks))
    train_blocks = tuple(sorted(int(x) for x in np.unique(p_blocks[train_idx])))
    test_blocks = tuple(sorted(int(x) for x in np.unique(p_blocks[test_idx])))

    if not train_blocks or not test_blocks or len(unique_blocks) < 4:
        raise ValueError("Spatial partition did not yield enough train/test blocks.")

    return SpatialPartition(
        presence_blocks=p_blocks,
        background_blocks=b_blocks,
        train_blocks=train_blocks,
        test_blocks=test_blocks,
        centers_xyz=km.cluster_centers_,
    )
