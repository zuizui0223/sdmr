"""Known-truth simulations for Product-A v2 ecological niche recovery.

Real occurrence data cannot reveal the fundamental niche exactly. These helpers
create synthetic environmental landscapes with an explicit generating niche so
model-selection procedures can be judged against the known truth rather than
against their own preferred validation statistic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .niche_recovery import _complete_matrix, _weighted_quantile


@dataclass(frozen=True)
class KnownTruthSimulation:
    environment: pd.DataFrame
    occurrences: pd.DataFrame
    target_group: pd.DataFrame
    audit_predictors: tuple[str, ...]
    true_suitability_column: str = "true_suitability"
    sampling_effort_column: str = "sampling_effort"


@dataclass(frozen=True)
class KnownTruthNicheProfile:
    n_audit_components: int
    niche_overlap_schoener_d_pc12: float
    centroid_distance: float
    breadth_log_sd_error: float
    quantile_profile_error: float
    true_mass_inside_predicted_pc12_envelope90: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def simulate_gaussian_plant_niche(
    *,
    seed: int = 1,
    n_cells: int = 12_000,
    n_occurrences: int = 600,
    n_target_group: int = 4_000,
    niche_center: tuple[float, float] = (0.55, -0.35),
    niche_width: tuple[float, float] = (0.55, 0.65),
    interaction_strength: float = 0.25,
    sampling_bias_strength: float = 1.25,
) -> KnownTruthSimulation:
    """Simulate a spatial landscape, known environmental niche, and biased records.

    ``temp_proxy`` is deliberately correlated with the true temperature axis and
    ``noise`` is irrelevant. The sampling process is spatially biased so a tuning
    method can be tested under occurrence conditions more similar to opportunistic
    biodiversity data.
    """

    if n_cells < 100 or n_occurrences < 10 or n_target_group < 10:
        raise ValueError("simulation sizes are too small")
    if n_occurrences >= n_cells or n_target_group >= n_cells:
        raise ValueError("occurrence/target-group sample sizes must be smaller than n_cells")
    rng = np.random.default_rng(seed)
    longitude = rng.uniform(-2.5, 2.5, n_cells)
    latitude = rng.uniform(-2.0, 2.0, n_cells)

    temperature = 0.72 * latitude + 0.22 * longitude + rng.normal(0, 0.38, n_cells)
    water = -0.58 * longitude + 0.18 * latitude + rng.normal(0, 0.42, n_cells)
    temp_proxy = 0.90 * temperature + rng.normal(0, 0.30, n_cells)
    seasonality = np.sin(longitude * 1.15) + 0.35 * np.cos(latitude * 1.4) + rng.normal(0, 0.20, n_cells)
    noise = rng.normal(0, 1.0, n_cells)

    c1, c2 = niche_center
    w1, w2 = niche_width
    z1 = (temperature - c1) / w1
    z2 = (water - c2) / w2
    log_truth = -0.5 * (z1**2 + z2**2) + float(interaction_strength) * temperature * water
    log_truth -= np.nanmax(log_truth)
    true_suitability = np.exp(log_truth)

    # Sampling effort is spatial, not biological. Target-group sampling follows
    # effort alone; focal occurrence sampling follows effort × true suitability.
    access_axis = 0.65 * longitude + 0.35 * latitude
    sampling_effort = np.exp(float(sampling_bias_strength) * (access_axis - access_axis.mean()) / access_axis.std())
    sampling_effort /= sampling_effort.max()

    occurrence_prob = true_suitability * sampling_effort
    occurrence_prob = occurrence_prob / occurrence_prob.sum()
    target_prob = sampling_effort / sampling_effort.sum()
    occurrence_idx = rng.choice(n_cells, size=n_occurrences, replace=False, p=occurrence_prob)
    target_idx = rng.choice(n_cells, size=n_target_group, replace=False, p=target_prob)

    environment = pd.DataFrame(
        {
            "longitude": longitude,
            "latitude": latitude,
            "temperature": temperature,
            "water": water,
            "temp_proxy": temp_proxy,
            "seasonality": seasonality,
            "noise": noise,
            "true_suitability": true_suitability,
            "sampling_effort": sampling_effort,
        }
    )
    occurrences = environment.iloc[np.sort(occurrence_idx)].copy().reset_index(drop=True)
    occurrences["species"] = "simulated_plant"
    target_group = environment.iloc[np.sort(target_idx)].copy().reset_index(drop=True)
    target_group["species"] = "nonfocal_target_group"
    return KnownTruthSimulation(
        environment=environment,
        occurrences=occurrences,
        target_group=target_group,
        audit_predictors=("temperature", "water", "temp_proxy", "seasonality", "noise"),
    )


def _weighted_schoener_d(
    pc_scores: np.ndarray,
    predicted_weights: np.ndarray,
    truth_weights: np.ndarray,
    *,
    bins: int,
) -> float:
    dims = min(2, pc_scores.shape[1])
    if dims == 0:
        return float("nan")
    xy = pc_scores[:, :dims]
    if dims == 1:
        xy = np.column_stack((xy[:, 0], np.zeros(len(xy))))
    lo = np.nanmin(xy, axis=0)
    hi = np.nanmax(xy, axis=0)
    span = hi - lo
    span[~np.isfinite(span) | (span <= 0)] = 1.0
    edges = [np.linspace(lo[i] - 1e-9 * span[i], hi[i] + 1e-9 * span[i], bins + 1) for i in range(2)]
    pred, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=edges, weights=predicted_weights)
    truth, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=edges, weights=truth_weights)
    if pred.sum() <= 0 or truth.sum() <= 0:
        return float("nan")
    pred /= pred.sum()
    truth /= truth.sum()
    return float(1.0 - 0.5 * np.abs(pred - truth).sum())


def known_truth_niche_recovery_profile(
    environment: pd.DataFrame,
    predicted_suitability: Sequence[float] | np.ndarray,
    true_suitability: Sequence[float] | np.ndarray,
    audit_predictors: Sequence[str],
    *,
    max_components: int = 4,
    quantiles: Sequence[float] = (0.05, 0.25, 0.50, 0.75, 0.95),
    overlap_bins: int = 24,
) -> KnownTruthNicheProfile:
    """Compare a predicted environmental niche directly with the known truth."""

    env, valid = _complete_matrix(environment, audit_predictors)
    pred = np.asarray(predicted_suitability, dtype=float)
    truth = np.asarray(true_suitability, dtype=float)
    if pred.ndim != 1 or truth.ndim != 1 or len(pred) != len(environment) or len(truth) != len(environment):
        raise ValueError("predicted_suitability and true_suitability must align with environment")
    pred = pred[valid]
    truth = truth[valid]
    keep = np.isfinite(pred) & np.isfinite(truth) & (pred >= 0) & (truth >= 0)
    env = env[keep]
    pred = pred[keep]
    truth = truth[keep]
    if len(env) < 5 or pred.sum() <= 0 or truth.sum() <= 0:
        return KnownTruthNicheProfile(0, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))

    scaler = StandardScaler().fit(env)
    z = scaler.transform(env)
    n_components = min(int(max_components), z.shape[1], len(z) - 1)
    pca = PCA(n_components=n_components, whiten=True, svd_solver="full").fit(z)
    pc = pca.transform(z)
    pred = pred / pred.sum()
    truth = truth / truth.sum()

    pred_centroid = np.average(pc, axis=0, weights=pred)
    truth_centroid = np.average(pc, axis=0, weights=truth)
    centroid_distance = float(np.sqrt(np.mean((pred_centroid - truth_centroid) ** 2)))

    pred_var = np.average((pc - pred_centroid) ** 2, axis=0, weights=pred)
    truth_var = np.average((pc - truth_centroid) ** 2, axis=0, weights=truth)
    eps = 1e-8
    breadth_error = float(
        np.mean(
            np.abs(
                np.log(
                    (np.sqrt(np.maximum(pred_var, 0.0)) + eps)
                    / (np.sqrt(np.maximum(truth_var, 0.0)) + eps)
                )
            )
        )
    )

    q = tuple(float(x) for x in quantiles)
    errors: list[float] = []
    for axis in range(n_components):
        pred_q = _weighted_quantile(pc[:, axis], pred, q)
        truth_q = _weighted_quantile(pc[:, axis], truth, q)
        errors.extend((pred_q - truth_q).tolist())
    quantile_error = float(np.sqrt(np.mean(np.square(errors)))) if errors else float("nan")

    inside = np.ones(len(pc), dtype=bool)
    for axis in range(min(2, n_components)):
        lower, upper = _weighted_quantile(pc[:, axis], pred, (0.05, 0.95))
        inside &= (pc[:, axis] >= lower) & (pc[:, axis] <= upper)
    true_mass_coverage = float(truth[inside].sum())

    return KnownTruthNicheProfile(
        n_audit_components=n_components,
        niche_overlap_schoener_d_pc12=_weighted_schoener_d(pc, pred, truth, bins=overlap_bins),
        centroid_distance=centroid_distance,
        breadth_log_sd_error=breadth_error,
        quantile_profile_error=quantile_error,
        true_mass_inside_predicted_pc12_envelope90=true_mass_coverage,
    )
