"""Spatial partitioning utilities for occurrence/background data."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupShuffleSplit


@dataclass(frozen=True)
class PresenceSpatialPartition:
    """Occurrence-only outer partition fixed before M/background construction."""

    presence_blocks: np.ndarray
    train_blocks: tuple[int, ...]
    test_blocks: tuple[int, ...]
    centers_xyz: np.ndarray


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


def make_presence_spatial_partition(
    presence_lon: np.ndarray,
    presence_lat: np.ndarray,
    *,
    n_blocks: int = 8,
    holdout_fraction: float = 0.5,
    random_state: int = 42,
) -> PresenceSpatialPartition:
    """Fix whole occurrence blocks as model-pool versus sealed answer-check blocks.

    This operation happens before any accessible-area or background construction.
    Occurrence coordinates are used only to declare the validation partition;
    sealed rows must not subsequently influence M, background sampling, fitting,
    predictor selection, regularization, or stopping.
    """

    p_xyz = lonlat_to_unit_xyz(presence_lon, presence_lat)
    if p_xyz.shape[0] < 4:
        raise ValueError("At least four occurrence points are required for spatial holdout.")
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between 0 and 1.")

    k = min(int(n_blocks), p_xyz.shape[0])
    if k < 4:
        raise ValueError("n_blocks must allow at least four spatial groups.")

    km = KMeans(n_clusters=k, n_init=20, random_state=random_state)
    p_blocks = km.fit_predict(p_xyz)
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

    return PresenceSpatialPartition(
        presence_blocks=p_blocks,
        train_blocks=train_blocks,
        test_blocks=test_blocks,
        centers_xyz=km.cluster_centers_,
    )


def assign_spatial_blocks(
    longitude: np.ndarray,
    latitude: np.ndarray,
    centers_xyz: np.ndarray,
) -> np.ndarray:
    """Assign coordinates to nearest predeclared occurrence-derived block center."""

    xyz = lonlat_to_unit_xyz(longitude, latitude)
    centers = np.asarray(centers_xyz, dtype=float)
    if centers.ndim != 2 or centers.shape[1] != 3 or not len(centers):
        raise ValueError("centers_xyz must be a non-empty n x 3 array")
    # Euclidean distance on the unit sphere is monotonic with great-circle
    # distance, so nearest-center labels are dateline safe and deterministic.
    distances = ((xyz[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return np.argmin(distances, axis=1).astype(int)


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
    """Create whole-region train/test blocks with occurrence-anchored centers.

    K-means is fitted only to occurrence coordinates so each spatial block is
    anchored by at least one known occurrence. Background points are assigned
    to the nearest occurrence-derived block. Whole blocks, never individual
    points, are then assigned to train or test.
    """

    b_xyz = lonlat_to_unit_xyz(background_lon, background_lat)
    if b_xyz.shape[0] < 2:
        raise ValueError("At least two background points are required.")

    presence = make_presence_spatial_partition(
        presence_lon,
        presence_lat,
        n_blocks=n_blocks,
        holdout_fraction=holdout_fraction,
        random_state=random_state,
    )
    b_blocks = assign_spatial_blocks(
        background_lon,
        background_lat,
        presence.centers_xyz,
    )
    return SpatialPartition(
        presence_blocks=presence.presence_blocks,
        background_blocks=b_blocks,
        train_blocks=presence.train_blocks,
        test_blocks=presence.test_blocks,
        centers_xyz=presence.centers_xyz,
    )
