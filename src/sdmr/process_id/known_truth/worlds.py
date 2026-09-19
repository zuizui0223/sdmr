"""Known-truth process worlds for SDMR v3.

These worlds deliberately separate generating-process membership, declared
representation structure, observation architecture, and held-out transfer.
They are development fixtures until a separate prospective contract freezes
new seeds and thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..taxonomy import DEFAULT_PLANT_PROCESSES


KNOWN_TRUTH_WORLDS = (
    "unique_process",
    "redundant_representation",
    "shared_carrier",
    "null_correlated",
    "interaction",
    "observation_confounded",
    "omitted_driver",
    "geographic_shift",
)


@dataclass(frozen=True)
class KnownTruthWorld:
    name: str
    environment: pd.DataFrame
    true_suitability: np.ndarray
    occurrences: pd.DataFrame
    background: pd.DataFrame
    process_registry: pd.DataFrame
    predictor_universe: tuple[str, ...]
    process_universe: tuple[str, ...]
    spatial_groups: np.ndarray
    generating_processes: tuple[str, ...]
    observation_unresolved_processes: tuple[str, ...]
    model_pool_mask: np.ndarray


def _sigmoid(values):
    x = np.clip(np.asarray(values, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-x))


def _z(values):
    x = np.asarray(values, dtype=float)
    sd = float(np.std(x))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("cannot standardize constant world variable")
    return (x - float(np.mean(x))) / sd


def _standard_registry():
    return pd.DataFrame([
        {"predictor": "temperature", "process": "thermal", "role": "direct"},
        {"predictor": "elevation_proxy", "process": "thermal", "role": "proxy"},
        {"predictor": "pet_shared", "process": "thermal", "role": "composite"},
        {"predictor": "water", "process": "water", "role": "direct"},
        {"predictor": "pet_shared", "process": "water", "role": "composite"},
        {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
        {"predictor": "radiation", "process": "radiation_energy", "role": "direct"},
        {"predictor": "soil", "process": "soil_substrate", "role": "direct"},
        {"predictor": "productivity", "process": "productivity", "role": "direct"},
    ])


def _shared_carrier_registry():
    return pd.DataFrame([
        {"predictor": "pet_shared", "process": "thermal", "role": "composite"},
        {"predictor": "pet_shared", "process": "water", "role": "composite"},
        {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
        {"predictor": "radiation", "process": "radiation_energy", "role": "direct"},
        {"predictor": "soil", "process": "soil_substrate", "role": "direct"},
        {"predictor": "productivity", "process": "productivity", "role": "direct"},
    ])


def _base_environment(rng, n_cells):
    longitude = rng.uniform(-2.5, 2.5, n_cells)
    latitude = rng.uniform(-2.0, 2.0, n_cells)
    temperature = 0.72 * latitude + 0.22 * longitude + rng.normal(0, 0.36, n_cells)
    water = -0.58 * longitude + 0.18 * latitude + rng.normal(0, 0.42, n_cells)
    seasonality = np.sin(1.1 * longitude) + 0.30 * np.cos(1.3 * latitude) + rng.normal(0, 0.20, n_cells)
    radiation = 0.42 * longitude + 0.35 * latitude + rng.normal(0, 0.32, n_cells)
    soil = 0.28 * longitude - 0.16 * latitude + rng.normal(0, 0.65, n_cells)
    productivity = 0.42 * water + 0.32 * temperature + rng.normal(0, 0.34, n_cells)
    pet_shared = 0.58 * temperature - 0.48 * water + rng.normal(0, 0.16, n_cells)
    elevation_proxy = 0.90 * temperature + rng.normal(0, 0.18, n_cells)
    return pd.DataFrame({
        "cell_id": np.arange(n_cells, dtype=int),
        "longitude": longitude,
        "latitude": latitude,
        "temperature": temperature,
        "water": water,
        "seasonality": seasonality,
        "radiation": radiation,
        "soil": soil,
        "productivity": productivity,
        "pet_shared": pet_shared,
        "elevation_proxy": elevation_proxy,
    })


def _spatial_groups(environment):
    lon_rank = pd.qcut(environment["longitude"], q=4, labels=False, duplicates="drop")
    lat_rank = pd.qcut(environment["latitude"], q=3, labels=False, duplicates="drop")
    return (lon_rank.astype(int) * 10 + lat_rank.astype(int)).to_numpy()


def simulate_process_world(
    name: str,
    *,
    seed: int,
    n_cells: int = 4000,
    n_occurrences: int = 400,
    n_background: int = 1600,
) -> KnownTruthWorld:
    """Generate one SDMR v3 known-truth process world."""

    name = str(name)
    if name not in KNOWN_TRUTH_WORLDS:
        raise ValueError(f"unknown SDMR v3 known-truth world: {name!r}")
    if int(n_cells) < 500:
        raise ValueError("n_cells must be >= 500")
    if int(n_occurrences) < 20 or int(n_background) < 50:
        raise ValueError("occurrence/background sizes are too small")
    if int(n_occurrences) + int(n_background) >= int(n_cells):
        raise ValueError("occurrences plus background must be smaller than n_cells")

    rng = np.random.default_rng(int(seed))
    env = _base_environment(rng, int(n_cells))
    model_pool_mask = env["longitude"].to_numpy(float) < 0.0
    registry = _standard_registry()
    predictors = (
        "temperature",
        "water",
        "seasonality",
        "radiation",
        "soil",
        "productivity",
        "pet_shared",
        "elevation_proxy",
    )
    generating = ("thermal",)
    observation_unresolved = ()

    if name == "unique_process":
        logit = 1.9 * _z(env["temperature"])
    elif name == "redundant_representation":
        env["water"] = env["temperature"].to_numpy(float) + rng.normal(0, 0.045, int(n_cells))
        env["pet_shared"] = 0.60 * env["temperature"] - 0.45 * env["water"] + rng.normal(0, 0.12, int(n_cells))
        logit = 1.9 * _z(env["temperature"])
    elif name == "shared_carrier":
        registry = _shared_carrier_registry()
        predictors = ("pet_shared", "seasonality", "radiation", "soil", "productivity")
        generating = ("thermal", "water")
        logit = 2.0 * _z(env["pet_shared"])
    elif name == "null_correlated":
        env["seasonality"] = env["temperature"].to_numpy(float) + rng.normal(0, 0.06, int(n_cells))
        logit = 1.8 * _z(env["temperature"])
    elif name == "interaction":
        generating = ("thermal", "water")
        tz = _z(env["temperature"])
        wz = _z(env["water"])
        logit = 0.25 * tz + 0.25 * wz + 2.2 * tz * wz
    elif name == "observation_confounded":
        observation_unresolved = ("thermal",)
        logit = 1.5 * _z(env["temperature"])
    elif name == "omitted_driver":
        hidden = rng.normal(0, 1.0, int(n_cells))
        env["hidden_driver"] = hidden
        generating = ("thermal",)
        logit = 2.0 * hidden
    elif name == "geographic_shift":
        noise = rng.normal(0, 0.12, int(n_cells))
        temp = env["temperature"].to_numpy(float)
        env["elevation_proxy"] = np.where(model_pool_mask, 0.95 * temp + noise, -0.95 * temp + noise)
        logit = 1.7 * _z(temp)
    else:
        raise AssertionError("unreachable world")

    suitability = _sigmoid(logit)
    base_effort = np.exp(0.55 * _z(env["longitude"]) + 0.25 * _z(env["latitude"]))
    if name == "observation_confounded":
        base_effort = np.exp(1.35 * _z(env["temperature"]) + 0.10 * _z(env["longitude"]))
    effort = base_effort / float(np.max(base_effort))

    occurrence_weight = suitability * effort
    occurrence_weight = occurrence_weight / float(np.sum(occurrence_weight))
    occurrence_idx = rng.choice(int(n_cells), size=int(n_occurrences), replace=False, p=occurrence_weight)

    available = np.ones(int(n_cells), dtype=bool)
    available[occurrence_idx] = False
    available_idx = np.flatnonzero(available)
    background_weight = effort[available_idx].astype(float)
    background_weight = background_weight / float(np.sum(background_weight))
    background_idx = rng.choice(available_idx, size=int(n_background), replace=False, p=background_weight)

    env = env.copy()
    env["true_suitability"] = suitability
    env["sampling_effort"] = effort
    env["world"] = name
    occurrences = env.iloc[np.sort(occurrence_idx)].copy().reset_index(drop=True)
    occurrences["record_role"] = "occurrence"
    background = env.iloc[np.sort(background_idx)].copy().reset_index(drop=True)
    background["record_role"] = "background"

    return KnownTruthWorld(
        name=name,
        environment=env,
        true_suitability=np.asarray(suitability, dtype=float),
        occurrences=occurrences,
        background=background,
        process_registry=registry.reset_index(drop=True),
        predictor_universe=tuple(predictors),
        process_universe=DEFAULT_PLANT_PROCESSES,
        spatial_groups=_spatial_groups(env),
        generating_processes=tuple(generating),
        observation_unresolved_processes=tuple(observation_unresolved),
        model_pool_mask=np.asarray(model_pool_mask, dtype=bool),
    )
