"""Ecological-niche recovery diagnostics for Product-A v2.

These diagnostics are deliberately distinct from ordinary prediction/model-fit
scores such as AUC, Boyce/CBI, omission rate, or AICc.  They ask whether a fitted
relative-suitability model reconstructs the *environmental distribution* occupied
by genuinely withheld occurrences.

The audit environmental basis is fitted from model-pool background rows only.
Candidate models are therefore judged in one common environmental space rather
than in whichever predictors they happened to select.

This module does not claim to recover the fundamental niche from presence-only
data.  With empirical GBIF data the target is the sealed realized environmental
niche.  Known-truth simulations are required to establish whether a tuning rule
can recover a known generating niche.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class NicheRecoveryProfile:
    """Multi-axis ecological recovery profile; no weighted super-score."""

    n_audit_components: int
    n_reference: int
    n_sealed_occurrences: int
    niche_overlap_schoener_d_pc12: float
    centroid_distance: float
    breadth_log_sd_error: float
    quantile_profile_error: float
    sealed_pc12_envelope_coverage90: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _complete_matrix(frame: pd.DataFrame, columns: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    cols = list(columns)
    if not cols:
        raise ValueError("audit_predictors must not be empty")
    missing = set(cols) - set(frame.columns)
    if missing:
        raise KeyError(f"frame missing audit predictors: {sorted(missing)}")
    values = frame[cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    valid = np.isfinite(values).all(axis=1)
    return values[valid], valid


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, quantiles: Sequence[float]) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    q = np.asarray(list(quantiles), dtype=float)
    if values.ndim != 1 or weights.ndim != 1 or values.size != weights.size:
        raise ValueError("values and weights must be aligned one-dimensional arrays")
    if np.any((q < 0) | (q > 1)):
        raise ValueError("quantiles must lie in [0, 1]")
    valid = np.isfinite(values) & np.isfinite(weights) & (weights >= 0)
    values = values[valid]
    weights = weights[valid]
    if values.size == 0 or float(weights.sum()) <= 0:
        return np.full(q.shape, np.nan, dtype=float)
    order = np.argsort(values, kind="mergesort")
    values = values[order]
    weights = weights[order]
    cumulative = np.cumsum(weights)
    cumulative = (cumulative - 0.5 * weights) / float(weights.sum())
    return np.interp(q, cumulative, values, left=values[0], right=values[-1])


def _schoener_d_pc12(reference_scores: np.ndarray, weights: np.ndarray, sealed_scores: np.ndarray, bins: int) -> float:
    if bins < 4:
        raise ValueError("bins must be >= 4")
    dims = min(2, reference_scores.shape[1], sealed_scores.shape[1])
    if dims == 0:
        return float("nan")
    ref = reference_scores[:, :dims]
    obs = sealed_scores[:, :dims]
    if dims == 1:
        ref = np.column_stack((ref[:, 0], np.zeros(len(ref))))
        obs = np.column_stack((obs[:, 0], np.zeros(len(obs))))

    stacked = np.vstack((ref, obs))
    lo = np.nanmin(stacked, axis=0)
    hi = np.nanmax(stacked, axis=0)
    span = hi - lo
    span[~np.isfinite(span) | (span <= 0)] = 1.0
    lo = lo - 1e-9 * span
    hi = hi + 1e-9 * span
    edges = [np.linspace(lo[i], hi[i], bins + 1) for i in range(2)]

    pred, _, _ = np.histogram2d(ref[:, 0], ref[:, 1], bins=edges, weights=weights)
    seen, _, _ = np.histogram2d(obs[:, 0], obs[:, 1], bins=edges)
    if float(pred.sum()) <= 0 or float(seen.sum()) <= 0:
        return float("nan")
    pred = pred / pred.sum()
    seen = seen / seen.sum()
    return float(1.0 - 0.5 * np.abs(pred - seen).sum())


def empirical_niche_recovery_profile(
    model_background: pd.DataFrame,
    sealed_occurrences: pd.DataFrame,
    reference_suitability: Sequence[float] | np.ndarray,
    audit_predictors: Sequence[str],
    *,
    max_components: int = 4,
    quantiles: Sequence[float] = (0.05, 0.25, 0.50, 0.75, 0.95),
    overlap_bins: int = 20,
) -> NicheRecoveryProfile:
    """Compare a model-implied environmental niche with sealed occurrences.

    Parameters
    ----------
    model_background
        Reference environments inside the declared M, from the model pool.  This
        is also the only data used to fit the standardization/PCA audit basis.
    sealed_occurrences
        Genuinely withheld occurrences.  They are projected into the frozen audit
        space only after all modelling decisions have been made.
    reference_suitability
        Relative-suitability values predicted by the fitted model for each row of
        ``model_background``.  These weights define the model-implied niche
        distribution over available environments.
    audit_predictors
        A common environmental audit basis, ideally the frozen active candidate
        manifest rather than the subset selected by a candidate model.

    Notes
    -----
    Lower is better for ``centroid_distance``, ``breadth_log_sd_error`` and
    ``quantile_profile_error``.  Higher is better for Schoener D.  The 90%
    envelope coverage is descriptive rather than a standalone optimization
    target because arbitrarily broad niches can achieve high coverage.
    """

    if max_components < 1:
        raise ValueError("max_components must be >= 1")
    reference, ref_valid = _complete_matrix(model_background, audit_predictors)
    sealed, _ = _complete_matrix(sealed_occurrences, audit_predictors)
    raw_weights = np.asarray(reference_suitability, dtype=float)
    if raw_weights.ndim != 1 or len(raw_weights) != len(model_background):
        raise ValueError("reference_suitability must align with model_background rows")
    weights = raw_weights[ref_valid]
    valid_weight = np.isfinite(weights) & (weights >= 0)
    reference = reference[valid_weight]
    weights = weights[valid_weight]
    if len(reference) < 5 or len(sealed) < 2 or float(weights.sum()) <= 0:
        return NicheRecoveryProfile(
            n_audit_components=0,
            n_reference=len(reference),
            n_sealed_occurrences=len(sealed),
            niche_overlap_schoener_d_pc12=float("nan"),
            centroid_distance=float("nan"),
            breadth_log_sd_error=float("nan"),
            quantile_profile_error=float("nan"),
            sealed_pc12_envelope_coverage90=float("nan"),
        )

    scaler = StandardScaler()
    reference_z = scaler.fit_transform(reference)
    sealed_z = scaler.transform(sealed)
    n_components = min(int(max_components), reference_z.shape[1], len(reference_z) - 1)
    pca = PCA(n_components=n_components, whiten=True, svd_solver="full")
    reference_pc = pca.fit_transform(reference_z)
    sealed_pc = pca.transform(sealed_z)

    weights = weights / weights.sum()
    predicted_centroid = np.average(reference_pc, axis=0, weights=weights)
    observed_centroid = sealed_pc.mean(axis=0)
    centroid_distance = float(np.sqrt(np.mean((predicted_centroid - observed_centroid) ** 2)))

    predicted_var = np.average((reference_pc - predicted_centroid) ** 2, axis=0, weights=weights)
    observed_var = np.mean((sealed_pc - observed_centroid) ** 2, axis=0)
    predicted_sd = np.sqrt(np.maximum(predicted_var, 0.0))
    observed_sd = np.sqrt(np.maximum(observed_var, 0.0))
    eps = 1e-8
    breadth_log_sd_error = float(np.mean(np.abs(np.log((predicted_sd + eps) / (observed_sd + eps)))))

    q = tuple(float(x) for x in quantiles)
    q_errors: list[float] = []
    for axis in range(n_components):
        predicted_q = _weighted_quantile(reference_pc[:, axis], weights, q)
        observed_q = np.quantile(sealed_pc[:, axis], q)
        q_errors.extend((predicted_q - observed_q).tolist())
    quantile_profile_error = float(np.sqrt(np.mean(np.square(q_errors)))) if q_errors else float("nan")

    schoener_d = _schoener_d_pc12(reference_pc, weights, sealed_pc, bins=overlap_bins)

    coverage_dims = min(2, n_components)
    inside = np.ones(len(sealed_pc), dtype=bool)
    for axis in range(coverage_dims):
        lower, upper = _weighted_quantile(reference_pc[:, axis], weights, (0.05, 0.95))
        inside &= (sealed_pc[:, axis] >= lower) & (sealed_pc[:, axis] <= upper)
    coverage = float(np.mean(inside)) if len(inside) else float("nan")

    return NicheRecoveryProfile(
        n_audit_components=n_components,
        n_reference=len(reference_pc),
        n_sealed_occurrences=len(sealed_pc),
        niche_overlap_schoener_d_pc12=schoener_d,
        centroid_distance=centroid_distance,
        breadth_log_sd_error=breadth_log_sd_error,
        quantile_profile_error=quantile_profile_error,
        sealed_pc12_envelope_coverage90=coverage,
    )
