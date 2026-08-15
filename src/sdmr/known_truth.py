"""Known-truth virtual-niche benchmarks for Product-A v2.

Real occurrence holdouts can test transfer but cannot reveal the generating
niche.  This module creates explicit virtual niches on an observed environmental
background and scores how closely a fitted procedure recovers the hidden
suitability surface and its ecological geometry.

The benchmark is intentionally separate from AUC, Boyce/CBI, OR10, and AICc.
Those remain model diagnostics/comparators rather than definitions of ecological
niche recovery.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VirtualNicheTruth:
    """Known generating niche evaluated over one environmental reference table."""

    family: str
    processes: tuple[str, ...]
    suitability: np.ndarray


@dataclass(frozen=True)
class KnownTruthRecoveryProfile:
    """Multi-axis recovery of a known virtual niche.

    Higher is better for ``truth_surface_rank`` and process recovery. Lower is
    better for all ecological geometry errors. No weighted super-score is
    defined here; v2 selection should use explicit gates/Pareto logic.
    """

    truth_surface_rank: float
    truth_surface_error: float
    centroid_error: float
    breadth_log_sd_error: float
    limit_quantile_error: float
    driver_process_precision: float
    driver_process_recall: float
    driver_process_f1: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def _numeric_column(frame: pd.DataFrame, name: str) -> np.ndarray:
    if name not in frame.columns:
        raise KeyError(f"environment is missing process column {name!r}")
    return pd.to_numeric(frame[name], errors="coerce").to_numpy(float)


def _mapping_value(values: Mapping[str, float] | None, process: str, default: float) -> float:
    if values is None:
        return float(default)
    if process not in values:
        raise KeyError(f"missing parameter for process {process!r}")
    return float(values[process])


def _default_center(x: np.ndarray) -> float:
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        raise ValueError("process column has no finite environmental values")
    return float(np.median(finite))


def _default_width(x: np.ndarray) -> float:
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        raise ValueError("process column has no finite environmental values")
    q25, q75 = np.quantile(finite, [0.25, 0.75])
    width = float(q75 - q25)
    if not width > 0:
        width = float(np.std(finite))
    if not width > 0:
        raise ValueError("process column has no usable environmental spread")
    return width


def _normalize_positive(values: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    finite = np.isfinite(out)
    if not np.any(finite):
        return np.full_like(out, np.nan, dtype=float)
    out = np.where(finite, np.clip(out, 0.0, None), np.nan)
    maximum = float(np.nanmax(out))
    if not maximum > 0:
        return np.where(finite, 0.0, np.nan)
    return out / maximum


def generate_known_truth_niche(
    environment: pd.DataFrame,
    processes: Sequence[str],
    *,
    family: str = "gaussian",
    centers: Mapping[str, float] | None = None,
    widths: Mapping[str, float] | None = None,
    left_widths: Mapping[str, float] | None = None,
    right_widths: Mapping[str, float] | None = None,
    thresholds: Mapping[str, float] | None = None,
    slopes: Mapping[str, float] | None = None,
    directions: Mapping[str, str] | None = None,
    interaction_strength: float = 0.0,
) -> VirtualNicheTruth:
    """Generate a hidden ecological response surface on observed environments.

    Supported families
    ------------------
    ``gaussian``
        Unimodal response on one or more processes.
    ``asymmetric``
        Unimodal response with independent lower/upper tolerance widths.
    ``threshold``
        Soft lower/upper environmental thresholds using logistic responses.
    ``interaction``
        Gaussian marginal responses plus a two-process interaction. The absolute
        interaction strength must be below one so the response remains bounded.

    Defaults are inferred from the environmental reference table only. In an
    empirical benchmark that table can be a CHELSA feature table, preserving
    realistic covariance and spatial environmental combinations.
    """

    processes = tuple(str(x) for x in processes)
    if not processes:
        raise ValueError("at least one generating process is required")
    family = str(family).lower()
    if family not in {"gaussian", "asymmetric", "threshold", "interaction"}:
        raise ValueError(f"unknown virtual-niche family: {family}")
    if family == "interaction" and len(processes) < 2:
        raise ValueError("interaction family requires at least two processes")
    if family == "interaction" and abs(float(interaction_strength)) >= 1:
        raise ValueError("absolute interaction_strength must be < 1")

    columns = {name: _numeric_column(environment, name) for name in processes}
    valid = np.ones(len(environment), dtype=bool)
    for values in columns.values():
        valid &= np.isfinite(values)

    log_suitability = np.full(len(environment), np.nan, dtype=float)
    if not np.any(valid):
        return VirtualNicheTruth(family=family, processes=processes, suitability=log_suitability)
    log_values = np.zeros(int(valid.sum()), dtype=float)

    standardized: dict[str, np.ndarray] = {}
    for process in processes:
        x_all = columns[process]
        x = x_all[valid]
        center = _mapping_value(centers, process, _default_center(x_all))
        width = _mapping_value(widths, process, _default_width(x_all))
        if not width > 0:
            raise ValueError(f"width must be > 0 for process {process!r}")
        z = (x - center) / width
        standardized[process] = z

        if family in {"gaussian", "interaction"}:
            log_values += -0.5 * z**2
        elif family == "asymmetric":
            left = _mapping_value(left_widths, process, width)
            right = _mapping_value(right_widths, process, width)
            if not left > 0 or not right > 0:
                raise ValueError(f"asymmetric widths must be > 0 for process {process!r}")
            local_width = np.where(x < center, left, right)
            log_values += -0.5 * ((x - center) / local_width) ** 2
        else:  # threshold
            threshold = _mapping_value(thresholds, process, center)
            slope = _mapping_value(slopes, process, 4.0 / width)
            direction = "above" if directions is None else str(directions.get(process, "above")).lower()
            if direction not in {"above", "below"}:
                raise ValueError("threshold direction must be 'above' or 'below'")
            signed = slope * (x - threshold)
            if direction == "below":
                signed = -signed
            # log(sigmoid(signed)) in a numerically stable form.
            log_values += -np.logaddexp(0.0, -signed)

    if family == "interaction":
        first, second = processes[:2]
        log_values += float(interaction_strength) * standardized[first] * standardized[second]

    # Convert relative log intensity to [0, 1] while preserving impossible/missing
    # environments as NaN.
    log_values -= float(np.max(log_values))
    suitability = np.full(len(environment), np.nan, dtype=float)
    suitability[valid] = np.exp(np.clip(log_values, -745.0, 0.0))
    suitability = _normalize_positive(suitability)
    return VirtualNicheTruth(family=family, processes=processes, suitability=suitability)


def sample_virtual_occurrences(
    environment: pd.DataFrame,
    truth: VirtualNicheTruth,
    n: int,
    *,
    sampling_bias: Sequence[float] | np.ndarray | None = None,
    random_state: int | None = None,
) -> pd.DataFrame:
    """Sample pseudo-occurrence cells from a hidden niche with optional bias.

    ``sampling_bias`` multiplies the ecological intensity and can represent road,
    population, observer-access, or other collection bias. Sampling is without
    replacement so repeated records from the same reference cell are not
    manufactured by the benchmark itself.
    """

    if n < 1:
        raise ValueError("n must be >= 1")
    suitability = np.asarray(truth.suitability, dtype=float)
    if suitability.ndim != 1 or len(suitability) != len(environment):
        raise ValueError("truth suitability must align with environment rows")
    weights = np.where(np.isfinite(suitability), np.clip(suitability, 0.0, None), 0.0)
    if sampling_bias is not None:
        bias = np.asarray(sampling_bias, dtype=float)
        if bias.ndim != 1 or len(bias) != len(environment):
            raise ValueError("sampling_bias must align with environment rows")
        weights *= np.where(np.isfinite(bias), np.clip(bias, 0.0, None), 0.0)
    available = np.flatnonzero(weights > 0)
    if n > len(available):
        raise ValueError("n exceeds the number of cells with positive sampling intensity")
    probabilities = weights / weights.sum()
    rng = np.random.default_rng(random_state)
    chosen = rng.choice(len(environment), size=int(n), replace=False, p=probabilities)
    out = environment.iloc[chosen].copy()
    out["virtual_truth_suitability"] = suitability[chosen]
    out["virtual_reference_index"] = chosen
    return out.reset_index(drop=True)


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(a) != len(b):
        return float("nan")
    ar = _average_ranks(a)
    br = _average_ranks(b)
    ar -= ar.mean()
    br -= br.mean()
    denominator = np.sqrt(np.sum(ar * ar) * np.sum(br * br))
    if denominator == 0:
        return float("nan")
    return float(np.sum(ar * br) / denominator)


def _unit_range(values: np.ndarray) -> np.ndarray:
    lo = float(np.min(values))
    hi = float(np.max(values))
    if not hi > lo:
        return np.zeros_like(values, dtype=float)
    return (values - lo) / (hi - lo)


def _weighted_quantiles(values: np.ndarray, weights: np.ndarray, q: Sequence[float]) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    x = values[order]
    w = weights[order]
    cumulative = np.cumsum(w)
    total = float(cumulative[-1])
    if not total > 0:
        return np.full(len(q), np.nan, dtype=float)
    cumulative = cumulative / total
    return np.interp(np.asarray(q, dtype=float), cumulative, x, left=x[0], right=x[-1])


def _process_metrics(true_processes: Sequence[str], estimated_processes: Sequence[str]) -> tuple[float, float, float]:
    truth = {str(x) for x in true_processes}
    estimate = {str(x) for x in estimated_processes}
    overlap = len(truth & estimate)
    precision = overlap / len(estimate) if estimate else (1.0 if not truth else 0.0)
    recall = overlap / len(truth) if truth else (1.0 if not estimate else 0.0)
    f1 = 0.0 if precision + recall == 0 else 2.0 * precision * recall / (precision + recall)
    return float(precision), float(recall), float(f1)


def evaluate_known_truth_recovery(
    environment: pd.DataFrame,
    truth: VirtualNicheTruth,
    estimated_suitability: Sequence[float] | np.ndarray,
    *,
    estimated_processes: Sequence[str] = (),
    limit_quantiles: tuple[float, float] = (0.05, 0.95),
) -> KnownTruthRecoveryProfile:
    """Score a fitted procedure against a hidden generating niche.

    Ecological geometry is evaluated only along the *true generating process
    axes*. Predictor names passed in ``estimated_processes`` should therefore be
    process/equivalence-group labels rather than arbitrary correlated raster
    aliases when such metadata are available.
    """

    estimate = np.asarray(estimated_suitability, dtype=float)
    truth_values = np.asarray(truth.suitability, dtype=float)
    if estimate.ndim != 1 or estimate.shape != truth_values.shape or len(estimate) != len(environment):
        raise ValueError("estimated suitability must align with the virtual reference environment")
    if not (0 <= limit_quantiles[0] < limit_quantiles[1] <= 1):
        raise ValueError("limit_quantiles must be ordered inside [0, 1]")

    process_arrays = [_numeric_column(environment, process) for process in truth.processes]
    valid = np.isfinite(truth_values) & np.isfinite(estimate)
    for values in process_arrays:
        valid &= np.isfinite(values)
    true = np.clip(truth_values[valid], 0.0, None)
    fitted = np.clip(estimate[valid], 0.0, None)
    if len(true) < 2 or float(true.sum()) <= 0 or float(fitted.sum()) <= 0:
        return KnownTruthRecoveryProfile(
            truth_surface_rank=float("nan"),
            truth_surface_error=float("nan"),
            centroid_error=float("nan"),
            breadth_log_sd_error=float("nan"),
            limit_quantile_error=float("nan"),
            driver_process_precision=_process_metrics(truth.processes, estimated_processes)[0],
            driver_process_recall=_process_metrics(truth.processes, estimated_processes)[1],
            driver_process_f1=_process_metrics(truth.processes, estimated_processes)[2],
        )

    surface_rank = _spearman(true, fitted)
    surface_error = float(np.sqrt(np.mean((_unit_range(true) - _unit_range(fitted)) ** 2)))

    true_weights = true / true.sum()
    fitted_weights = fitted / fitted.sum()
    centroid_errors: list[float] = []
    breadth_errors: list[float] = []
    limit_errors: list[float] = []
    eps = 1e-12
    for all_values in process_arrays:
        values = all_values[valid]
        span = float(np.max(values) - np.min(values))
        if not span > 0:
            continue
        true_center = float(np.sum(values * true_weights))
        fitted_center = float(np.sum(values * fitted_weights))
        centroid_errors.append(abs(fitted_center - true_center) / span)

        true_sd = float(np.sqrt(np.sum(true_weights * (values - true_center) ** 2)))
        fitted_sd = float(np.sqrt(np.sum(fitted_weights * (values - fitted_center) ** 2)))
        breadth_errors.append(abs(np.log((fitted_sd + eps) / (true_sd + eps))))

        true_limits = _weighted_quantiles(values, true_weights, limit_quantiles)
        fitted_limits = _weighted_quantiles(values, fitted_weights, limit_quantiles)
        limit_errors.extend((np.abs(fitted_limits - true_limits) / span).tolist())

    precision, recall, f1 = _process_metrics(truth.processes, estimated_processes)
    return KnownTruthRecoveryProfile(
        truth_surface_rank=surface_rank,
        truth_surface_error=surface_error,
        centroid_error=float(np.mean(centroid_errors)) if centroid_errors else float("nan"),
        breadth_log_sd_error=float(np.mean(breadth_errors)) if breadth_errors else float("nan"),
        limit_quantile_error=float(np.mean(limit_errors)) if limit_errors else float("nan"),
        driver_process_precision=precision,
        driver_process_recall=recall,
        driver_process_f1=f1,
    )
