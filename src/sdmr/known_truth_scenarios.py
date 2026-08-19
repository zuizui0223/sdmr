"""Predeclared known-truth scenario families for Product-A v2.

The ecological generating niche and the observation process are separate. The
role of every explicit observation-process predictor is declared before fitting;
hidden suitability is still opened only by the final known-truth audit.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from .known_truth import KnownTruthSimulation
from .model import ModelSpec
from .niche_recovery_cv import RecoveryCandidate


KNOWN_TRUTH_FAMILIES = (
    "gaussian",
    "asymmetric",
    "soft_threshold",
    "interaction",
    "omitted_driver",
    "observation_confounded",
)


def _base_landscape(seed: int, n_cells: int) -> tuple[np.random.Generator, pd.DataFrame]:
    if n_cells < 100:
        raise ValueError("n_cells must be >= 100")
    rng = np.random.default_rng(seed)
    longitude = rng.uniform(-2.5, 2.5, n_cells)
    latitude = rng.uniform(-2.0, 2.0, n_cells)
    temperature = 0.72 * latitude + 0.22 * longitude + rng.normal(0, 0.38, n_cells)
    water = -0.58 * longitude + 0.18 * latitude + rng.normal(0, 0.42, n_cells)
    temp_proxy = 0.90 * temperature + rng.normal(0, 0.30, n_cells)
    seasonality = np.sin(longitude * 1.15) + 0.35 * np.cos(latitude * 1.4) + rng.normal(0, 0.20, n_cells)
    soil = 0.30 * longitude - 0.15 * latitude + rng.normal(0, 0.75, n_cells)
    noise = rng.normal(0, 1.0, n_cells)

    # Independent focal-taxon observation/detectability process. Its role is
    # known by design, but its realized values never enter the ecological audit.
    recording_bias = rng.normal(0, 1.0, n_cells)
    domain = np.where(longitude < 0, "source", "shifted")
    return rng, pd.DataFrame(
        {
            "longitude": longitude,
            "latitude": latitude,
            "temperature": temperature,
            "water": water,
            "temp_proxy": temp_proxy,
            "seasonality": seasonality,
            "soil": soil,
            "noise": noise,
            "recording_bias": recording_bias,
            "domain": domain,
        }
    )


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(x, dtype=float), -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-x))


def _truth_surface(environment: pd.DataFrame, family: str) -> np.ndarray:
    t = environment["temperature"].to_numpy(float)
    w = environment["water"].to_numpy(float)
    s = environment["soil"].to_numpy(float)

    if family in {"gaussian", "observation_confounded"}:
        log_truth = -0.5 * (((t - 0.55) / 0.55) ** 2 + ((w + 0.35) / 0.65) ** 2)
    elif family == "asymmetric":
        t_width = np.where(t < 0.45, 0.95, 0.35)
        w_width = np.where(w < -0.25, 0.45, 0.85)
        log_truth = -0.5 * (((t - 0.45) / t_width) ** 2 + ((w + 0.25) / w_width) ** 2)
    elif family == "soft_threshold":
        lower_temp = _sigmoid((t + 0.25) / 0.18)
        upper_temp = _sigmoid((1.05 - t) / 0.20)
        lower_water = _sigmoid((w + 1.00) / 0.22)
        upper_water = _sigmoid((0.45 - w) / 0.28)
        truth = lower_temp * upper_temp * lower_water * upper_water
        return truth / float(np.nanmax(truth))
    elif family == "interaction":
        log_truth = (
            -0.5 * (((t - 0.45) / 0.70) ** 2 + ((w + 0.20) / 0.75) ** 2)
            + 0.80 * t * w
        )
    elif family == "omitted_driver":
        log_truth = -0.5 * (
            ((t - 0.50) / 0.70) ** 2
            + ((w + 0.30) / 0.75) ** 2
            + ((s - 0.20) / 0.45) ** 2
        )
    else:
        raise ValueError(f"unknown known-truth family: {family!r}")

    log_truth = log_truth - float(np.nanmax(log_truth))
    return np.exp(log_truth)


def simulate_known_truth_plant_niche(
    family: str,
    *,
    seed: int = 1,
    n_cells: int = 8_000,
    n_occurrences: int = 500,
    n_target_group: int = 2_500,
    sampling_bias_strength: float = 1.15,
    focal_recording_bias_strength: float = 3.0,
) -> KnownTruthSimulation:
    """Generate one known-truth plant niche and biased presence/background data."""

    family = str(family)
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError(f"family must be one of {KNOWN_TRUTH_FAMILIES}")
    if n_occurrences < 10 or n_target_group < 10:
        raise ValueError("occurrence and target-group sizes must be >= 10")
    if n_occurrences >= n_cells or n_target_group >= n_cells:
        raise ValueError("occurrence/target-group sizes must be smaller than n_cells")

    rng, environment = _base_landscape(seed, n_cells)
    true_suitability = _truth_surface(environment, family)

    access_axis = 0.65 * environment["longitude"].to_numpy(float) + 0.35 * environment["latitude"].to_numpy(float)
    access_z = (access_axis - access_axis.mean()) / access_axis.std()
    sampling_effort = np.exp(float(sampling_bias_strength) * access_z)
    sampling_effort /= sampling_effort.max()

    focal_multiplier = np.ones(n_cells, dtype=float)
    if family == "observation_confounded":
        rb = environment["recording_bias"].to_numpy(float)
        rb = (rb - rb.mean()) / rb.std()
        focal_multiplier = np.exp(float(focal_recording_bias_strength) * np.clip(rb, -3.0, 3.0))
        focal_multiplier /= focal_multiplier.max()

    occurrence_prob = true_suitability * sampling_effort * focal_multiplier
    if not np.isfinite(occurrence_prob).all() or float(occurrence_prob.sum()) <= 0:
        raise ValueError("invalid occurrence probability surface")
    occurrence_prob = occurrence_prob / occurrence_prob.sum()
    target_prob = sampling_effort / sampling_effort.sum()
    occurrence_idx = rng.choice(n_cells, size=n_occurrences, replace=False, p=occurrence_prob)
    target_idx = rng.choice(n_cells, size=n_target_group, replace=False, p=target_prob)

    environment = environment.copy()
    environment["true_suitability"] = true_suitability
    environment["sampling_effort"] = sampling_effort
    environment["focal_recording_multiplier"] = focal_multiplier
    environment["scenario"] = family

    occurrences = environment.iloc[np.sort(occurrence_idx)].copy().reset_index(drop=True)
    occurrences["species"] = f"simulated_{family}"
    target_group = environment.iloc[np.sort(target_idx)].copy().reset_index(drop=True)
    target_group["species"] = "nonfocal_target_group"

    audit_predictors = ("temperature", "water", "temp_proxy", "seasonality", "soil", "noise")
    return KnownTruthSimulation(
        environment=environment,
        occurrences=occurrences,
        target_group=target_group,
        audit_predictors=audit_predictors,
    )


def standard_known_truth_candidates() -> Mapping[str, RecoveryCandidate]:
    """Return one fixed, role-declared candidate library across all scenarios.

    ``recording_bias`` is predeclared as observation-process information, not an
    ecological predictor. Models may use it to explain records, but Product-A v2
    marginalizes it before computing the ecological niche surface.
    """

    return {
        "tw_linear": RecoveryCandidate(
            "tw_linear", ("temperature", "water"), ModelSpec(C=1.0, degree=1, penalty="l2")
        ),
        "tw_quadratic": RecoveryCandidate(
            "tw_quadratic", ("temperature", "water"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "proxy_water_quadratic": RecoveryCandidate(
            "proxy_water_quadratic", ("temp_proxy", "water"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "climate_soil_quadratic": RecoveryCandidate(
            "climate_soil_quadratic",
            ("temperature", "water", "soil"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
        ),
        "broad_linear": RecoveryCandidate(
            "broad_linear",
            ("temperature", "water", "temp_proxy", "seasonality", "soil", "noise"),
            ModelSpec(C=1.0, degree=1, penalty="l2"),
        ),
        "niche_plus_observer": RecoveryCandidate(
            "niche_plus_observer",
            ("temperature", "water", "recording_bias"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
            observation_predictors=("recording_bias",),
        ),
        "observer_only": RecoveryCandidate(
            "observer_only",
            ("recording_bias",),
            ModelSpec(C=1.0, degree=1, penalty="l2"),
            observation_predictors=("recording_bias",),
        ),
    }
