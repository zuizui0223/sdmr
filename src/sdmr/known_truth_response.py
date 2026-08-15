"""Direct ecological truth-recovery diagnostics for Product-A v2.

These metrics are available only in simulations where the generating niche is
known. They are never inputs to real-data tuning or candidate selection. Their
purpose is to test whether a selector recovered biologically interpretable niche
structure rather than merely a similar geographic ranking.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .niche_recovery import _weighted_quantile


DEFAULT_PROCESS_ALIASES = {
    "temperature": "temperature",
    "temp_proxy": "temperature",
    "water": "water",
    "soil": "soil",
    "seasonality": "seasonality",
    "noise": "noise",
    "recording_bias": "observation_process",
}


@dataclass(frozen=True)
class KnownTruthResponseProfile:
    n_response_predictors: int
    truth_surface_rank: float
    truth_surface_nrmse: float
    response_curve_error: float
    optimum_error: float
    lower_limit_error: float
    upper_limit_error: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class KnownTruthProcessProfile:
    n_true_processes: int
    n_selected_processes: int
    driver_process_precision: float
    driver_process_recall: float
    driver_process_f1: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def infer_true_processes(environment: pd.DataFrame) -> tuple[str, ...]:
    """Return the predeclared generating processes for bundled simulations."""

    scenario = ""
    if "scenario" in environment.columns:
        values = tuple(sorted(str(x) for x in pd.unique(environment["scenario"].dropna())))
        if len(values) == 1:
            scenario = values[0]
    if scenario == "omitted_driver":
        return ("temperature", "water", "soil")
    return tuple(x for x in ("temperature", "water") if x in environment.columns)


def infer_response_predictors(environment: pd.DataFrame) -> tuple[str, ...]:
    """Return environmental axes whose true response should be audited directly."""

    return infer_true_processes(environment)


def _average_ranks(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    ranks = np.empty(len(x), dtype=float)
    start = 0
    while start < len(x):
        end = start + 1
        while end < len(x) and sorted_x[end] == sorted_x[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def _rank_correlation(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(a) != len(b):
        return float("nan")
    ar = _average_ranks(a)
    br = _average_ranks(b)
    ar -= ar.mean()
    br -= br.mean()
    denom = np.sqrt(np.sum(ar * ar) * np.sum(br * br))
    if denom <= 0:
        return float("nan")
    return float(np.sum(ar * br) / denom)


def _unit_scale(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    lo = float(np.min(x))
    hi = float(np.max(x))
    if not hi > lo:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _quantile_bin_curve(
    x: np.ndarray,
    suitability: np.ndarray,
    *,
    n_bins: int,
) -> tuple[np.ndarray, np.ndarray]:
    if n_bins < 4:
        raise ValueError("n_bins must be >= 4")
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.quantile(x, quantiles)
    edges = np.unique(edges)
    if len(edges) < 4:
        return np.array([], dtype=float), np.array([], dtype=float)
    # Ensure the global maximum is included in the final interval.
    edges[0] -= 1e-12 * max(1.0, abs(float(edges[0])))
    edges[-1] += 1e-12 * max(1.0, abs(float(edges[-1])))
    centers = []
    curve = []
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (x >= lower) & (x < upper)
        if not np.any(mask):
            continue
        centers.append(float(np.mean(x[mask])))
        curve.append(float(np.mean(suitability[mask])))
    return np.asarray(centers, dtype=float), np.asarray(curve, dtype=float)


def known_truth_response_profile(
    environment: pd.DataFrame,
    predicted_suitability: Sequence[float] | np.ndarray,
    true_suitability: Sequence[float] | np.ndarray,
    response_predictors: Sequence[str] | None = None,
    *,
    n_bins: int = 20,
    lower_mass: float = 0.05,
    upper_mass: float = 0.95,
) -> KnownTruthResponseProfile:
    """Score direct response shape, optimum and environmental limits.

    Errors for each environmental axis are divided by the available environmental
    range before averaging, making temperature- and water-axis errors comparable
    without assigning arbitrary scientific weights.
    """

    if not 0 <= lower_mass < upper_mass <= 1:
        raise ValueError("lower_mass and upper_mass must satisfy 0 <= lower < upper <= 1")
    predictors = tuple(response_predictors or infer_response_predictors(environment))
    missing = sorted(set(predictors) - set(environment.columns))
    if missing:
        raise KeyError(f"environment missing response predictors: {missing}")

    pred = np.asarray(predicted_suitability, dtype=float)
    truth = np.asarray(true_suitability, dtype=float)
    if pred.ndim != 1 or truth.ndim != 1 or len(pred) != len(environment) or len(truth) != len(environment):
        raise ValueError("predicted_suitability and true_suitability must align with environment")

    matrix = environment[list(predictors)].apply(pd.to_numeric, errors="coerce").to_numpy(float) if predictors else np.empty((len(environment), 0))
    keep = np.isfinite(pred) & np.isfinite(truth) & (pred >= 0) & (truth >= 0)
    if predictors:
        keep &= np.isfinite(matrix).all(axis=1)
    pred = pred[keep]
    truth = truth[keep]
    matrix = matrix[keep]
    if len(pred) < 5 or pred.sum() <= 0 or truth.sum() <= 0:
        return KnownTruthResponseProfile(
            len(predictors),
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
        )

    pred_unit = _unit_scale(pred)
    truth_unit = _unit_scale(truth)
    surface_rank = _rank_correlation(pred, truth)
    surface_nrmse = float(np.sqrt(np.mean((pred_unit - truth_unit) ** 2)))

    curve_errors = []
    optimum_errors = []
    lower_errors = []
    upper_errors = []
    pred_weights = pred / pred.sum()
    truth_weights = truth / truth.sum()
    for axis in range(matrix.shape[1]):
        x = matrix[:, axis]
        span = float(np.max(x) - np.min(x))
        if not span > 0:
            continue
        pred_centers, pred_curve = _quantile_bin_curve(x, pred_unit, n_bins=n_bins)
        truth_centers, truth_curve = _quantile_bin_curve(x, truth_unit, n_bins=n_bins)
        if len(pred_curve) and len(pred_curve) == len(truth_curve) and np.allclose(pred_centers, truth_centers):
            curve_errors.append(float(np.sqrt(np.mean((pred_curve - truth_curve) ** 2))))
            pred_optimum = float(pred_centers[int(np.argmax(pred_curve))])
            truth_optimum = float(truth_centers[int(np.argmax(truth_curve))])
            optimum_errors.append(abs(pred_optimum - truth_optimum) / span)

        pred_low, pred_high = _weighted_quantile(x, pred_weights, (lower_mass, upper_mass))
        truth_low, truth_high = _weighted_quantile(x, truth_weights, (lower_mass, upper_mass))
        lower_errors.append(abs(float(pred_low - truth_low)) / span)
        upper_errors.append(abs(float(pred_high - truth_high)) / span)

    def mean_or_nan(values: list[float]) -> float:
        return float(np.mean(values)) if values else float("nan")

    return KnownTruthResponseProfile(
        n_response_predictors=len(predictors),
        truth_surface_rank=surface_rank,
        truth_surface_nrmse=surface_nrmse,
        response_curve_error=mean_or_nan(curve_errors),
        optimum_error=mean_or_nan(optimum_errors),
        lower_limit_error=mean_or_nan(lower_errors),
        upper_limit_error=mean_or_nan(upper_errors),
    )


def known_truth_process_profile(
    selected_predictors: Sequence[str],
    true_processes: Sequence[str],
    *,
    process_aliases: Mapping[str, str] = DEFAULT_PROCESS_ALIASES,
) -> KnownTruthProcessProfile:
    """Score process-level recovery while treating declared proxies as aliases."""

    true = {str(x) for x in true_processes}
    selected = {
        str(process_aliases.get(str(predictor), str(predictor)))
        for predictor in selected_predictors
    }
    if not true:
        return KnownTruthProcessProfile(0, len(selected), float("nan"), float("nan"), float("nan"))
    tp = len(true & selected)
    precision = float(tp / len(selected)) if selected else 0.0
    recall = float(tp / len(true))
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return KnownTruthProcessProfile(
        n_true_processes=len(true),
        n_selected_processes=len(selected),
        driver_process_precision=precision,
        driver_process_recall=recall,
        driver_process_f1=f1,
    )
