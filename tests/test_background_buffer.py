import numpy as np
import pandas as pd

from sdmr.data.background import occurrence_buffer_membership


EARTH_RADIUS_KM = 6371.0088


def _brute_membership(frame: pd.DataFrame, focal: pd.DataFrame, buffer_km: float) -> np.ndarray:
    lon = pd.to_numeric(frame["longitude"], errors="coerce").to_numpy(float)
    lat = pd.to_numeric(frame["latitude"], errors="coerce").to_numpy(float)
    flon = pd.to_numeric(focal["longitude"], errors="coerce").to_numpy(float)
    flat = pd.to_numeric(focal["latitude"], errors="coerce").to_numpy(float)
    out = np.zeros(len(frame), dtype=bool)
    fvalid = np.isfinite(flon) & np.isfinite(flat)
    for i, (xlon, xlat) in enumerate(zip(lon, lat, strict=True)):
        if not np.isfinite(xlon) or not np.isfinite(xlat):
            continue
        lon1 = np.deg2rad(xlon)
        lat1 = np.deg2rad(xlat)
        lon2 = np.deg2rad(flon[fvalid])
        lat2 = np.deg2rad(flat[fvalid])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        distance = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
        out[i] = bool(np.any(distance <= buffer_km))
    return out


def test_accelerated_buffer_matches_bruteforce_on_random_global_candidates():
    rng = np.random.default_rng(20260815)
    candidates = pd.DataFrame(
        {
            "longitude": rng.uniform(-180, 180, 5000),
            "latitude": rng.uniform(-89.5, 89.5, 5000),
        }
    )
    focal = pd.DataFrame(
        {
            "longitude": [-123.1, -71.2, 12.3, 139.7, 151.2],
            "latitude": [49.3, 42.4, 41.9, 35.7, -33.9],
        }
    )
    for buffer_km in (150.0, 300.0, 500.0, 1000.0):
        expected = _brute_membership(candidates, focal, buffer_km)
        observed = occurrence_buffer_membership(candidates, focal, buffer_km=buffer_km)
        np.testing.assert_array_equal(observed, expected)


def test_accelerated_buffer_matches_bruteforce_across_dateline():
    candidates = pd.DataFrame(
        {
            "longitude": [179.9, -179.9, 178.0, -178.0, 170.0, -170.0, 0.0, np.nan],
            "latitude": [0.0, 0.0, 0.5, -0.5, 0.0, 0.0, 0.0, 0.0],
        }
    )
    focal = pd.DataFrame(
        {
            "longitude": [179.5, -179.5],
            "latitude": [0.0, 0.0],
        }
    )
    for buffer_km in (100.0, 300.0, 1000.0):
        expected = _brute_membership(candidates, focal, buffer_km)
        observed = occurrence_buffer_membership(candidates, focal, buffer_km=buffer_km)
        np.testing.assert_array_equal(observed, expected)


def test_accelerated_buffer_matches_bruteforce_when_cap_reaches_pole():
    candidates = pd.DataFrame(
        {
            "longitude": [-180.0, -120.0, -60.0, 0.0, 60.0, 120.0, 179.0, 0.0],
            "latitude": [89.0, 89.0, 89.0, 89.0, 89.0, 89.0, 89.0, 80.0],
        }
    )
    focal = pd.DataFrame({"longitude": [30.0], "latitude": [88.5]})
    for buffer_km in (100.0, 300.0, 500.0):
        expected = _brute_membership(candidates, focal, buffer_km)
        observed = occurrence_buffer_membership(candidates, focal, buffer_km=buffer_km)
        np.testing.assert_array_equal(observed, expected)


def test_accelerated_buffer_preserves_invalid_candidate_handling():
    candidates = pd.DataFrame(
        {
            "longitude": [0.0, np.nan, 1.0, np.inf],
            "latitude": [0.0, 0.0, np.nan, 1.0],
        }
    )
    focal = pd.DataFrame({"longitude": [0.0], "latitude": [0.0]})
    expected = _brute_membership(candidates, focal, 100.0)
    observed = occurrence_buffer_membership(candidates, focal, buffer_km=100.0)
    np.testing.assert_array_equal(observed, expected)
