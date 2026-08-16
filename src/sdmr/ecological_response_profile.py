"""Ecologically interpretable response summaries from a fitted suitability surface.

This module is deliberately downstream of model selection.  It does not choose a
model and it does not define a new goodness-of-fit score.  Given a common audit
environment and an ecological (observation-marginalized) suitability surface, it
summarizes quantities that can be discussed biologically:

- niche centre and breadth on each environmental axis;
- lower/upper environmental limits containing a predeclared suitability mass;
- marginal response optimum;
- monotonic-direction diagnostic and number of response turning points.

The binned marginal curve is returned alongside the summary so interpretation is
not forced into one scalar or one categorical response-shape label.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EcologicalResponseProfile:
    summary: pd.DataFrame
    curves: pd.DataFrame


def _weighted_quantile(
    values: np.ndarray,
    weights: np.ndarray,
    probabilities: Sequence[float],
) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    x = np.asarray(values, dtype=float)[order]
    w = np.asarray(weights, dtype=float)[order]
    total = float(w.sum())
    if not total > 0:
        return np.full(len(tuple(probabilities)), np.nan, dtype=float)
    cdf = (np.cumsum(w) - 0.5 * w) / total
    cdf = np.clip(cdf, 0.0, 1.0)
    return np.interp(np.asarray(tuple(probabilities), dtype=float), cdf, x)


def _rank_correlation(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or len(x) != len(y):
        return float("nan")
    xr = pd.Series(x).rank(method="average").to_numpy(float)
    yr = pd.Series(y).rank(method="average").to_numpy(float)
    if np.allclose(xr, xr[0]) or np.allclose(yr, yr[0]):
        return 0.0
    return float(np.corrcoef(xr, yr)[0, 1])


def _direction_changes(values: np.ndarray) -> int:
    delta = np.diff(np.asarray(values, dtype=float))
    signs = np.sign(delta)
    signs = signs[signs != 0]
    if len(signs) < 2:
        return 0
    return int(np.sum(signs[1:] != signs[:-1]))


def ecological_response_profile(
    environment: pd.DataFrame,
    ecological_suitability: Sequence[float] | np.ndarray,
    predictors: Sequence[str],
    *,
    n_bins: int = 20,
    lower_mass: float = 0.05,
    upper_mass: float = 0.95,
) -> EcologicalResponseProfile:
    """Summarize ecological response structure without selecting a model.

    ``ecological_suitability`` should already have observation-process nuisance
    variables marginalized.  Suitability is used as a non-negative mass over the
    audit environment; it is not interpreted as a calibrated occurrence
    probability.
    """

    if n_bins < 4:
        raise ValueError("n_bins must be >= 4")
    if not 0 <= lower_mass < upper_mass <= 1:
        raise ValueError("lower_mass and upper_mass must satisfy 0 <= lower < upper <= 1")
    predictors = tuple(dict.fromkeys(str(x) for x in predictors))
    missing = sorted(set(predictors) - set(environment.columns))
    if missing:
        raise KeyError(f"environment missing response predictors: {missing}")

    suitability = np.asarray(ecological_suitability, dtype=float)
    if suitability.ndim != 1 or len(suitability) != len(environment):
        raise ValueError("ecological_suitability must be one-dimensional and align with environment")

    summary_rows: list[dict[str, object]] = []
    curve_rows: list[dict[str, object]] = []
    for predictor in predictors:
        x = pd.to_numeric(environment[predictor], errors="coerce").to_numpy(float)
        keep = np.isfinite(x) & np.isfinite(suitability) & (suitability >= 0)
        xv = x[keep]
        sv = suitability[keep]
        if len(xv) < 5 or float(sv.sum()) <= 0:
            summary_rows.append(
                {
                    "predictor": predictor,
                    "n_audit_rows": int(len(xv)),
                    "environment_min": float("nan"),
                    "environment_max": float("nan"),
                    "niche_center": float("nan"),
                    "niche_breadth_sd": float("nan"),
                    "lower_limit": float("nan"),
                    "upper_limit": float("nan"),
                    "marginal_optimum": float("nan"),
                    "marginal_rank_correlation": float("nan"),
                    "marginal_direction_changes": 0,
                    "n_curve_bins": 0,
                }
            )
            continue

        weights = sv / sv.sum()
        center = float(np.sum(weights * xv))
        breadth = float(np.sqrt(np.sum(weights * (xv - center) ** 2)))
        lower, upper = _weighted_quantile(xv, weights, (lower_mass, upper_mass))

        edges = np.unique(np.quantile(xv, np.linspace(0.0, 1.0, n_bins + 1)))
        centers: list[float] = []
        response: list[float] = []
        if len(edges) >= 3:
            edges = edges.copy()
            edges[0] -= 1e-12 * max(1.0, abs(float(edges[0])))
            edges[-1] += 1e-12 * max(1.0, abs(float(edges[-1])))
            for bin_index, (lo, hi) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
                mask = (xv >= lo) & (xv < hi)
                if not np.any(mask):
                    continue
                env_center = float(np.mean(xv[mask]))
                mean_response = float(np.mean(sv[mask]))
                centers.append(env_center)
                response.append(mean_response)
                curve_rows.append(
                    {
                        "predictor": predictor,
                        "bin": int(bin_index),
                        "environment_center": env_center,
                        "mean_ecological_suitability": mean_response,
                        "n_rows": int(mask.sum()),
                    }
                )

        c = np.asarray(centers, dtype=float)
        r = np.asarray(response, dtype=float)
        optimum = float(c[int(np.argmax(r))]) if len(r) else float("nan")
        rank = _rank_correlation(c, r) if len(r) else float("nan")
        changes = _direction_changes(r) if len(r) else 0
        summary_rows.append(
            {
                "predictor": predictor,
                "n_audit_rows": int(len(xv)),
                "environment_min": float(np.min(xv)),
                "environment_max": float(np.max(xv)),
                "niche_center": center,
                "niche_breadth_sd": breadth,
                "lower_limit": float(lower),
                "upper_limit": float(upper),
                "marginal_optimum": optimum,
                "marginal_rank_correlation": rank,
                "marginal_direction_changes": int(changes),
                "n_curve_bins": int(len(r)),
            }
        )

    return EcologicalResponseProfile(
        summary=pd.DataFrame(summary_rows),
        curves=pd.DataFrame(curve_rows),
    )
