"""Exploratory geographic turnover of presence-record environment information.

A taxon shares one null occurrence/background density-ratio surface across
regions. The region-specific environmental availability and explicit effort
weights are retained. Spatial held-out process ablations are recomputed under
observed and null-simulated occurrences.

This is a new macroecological test, NOT Product A/B validation or evidence of
causal physiological limits. Requires a preconstructed available-cell table.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp

REQUIRED = (
    "taxon", "region", "cell_id", "spatial_block", "temperature",
    "moisture", "effort", "n_occ",
)
# Shared temperature x moisture information is excluded in BOTH knockouts.
FEATURES = ("temperature", "temperature_sq", "moisture", "moisture_sq", "temperature_x_moisture")
FEATURE_SETS = {"full": (0, 1, 2, 3, 4), "without_temperature": (2, 3), "without_moisture": (0, 1)}


def _check_frame(frame: pd.DataFrame) -> pd.DataFrame:
    absent = sorted(set(REQUIRED) - set(frame.columns))
    if absent:
        raise ValueError(f"missing required fields: {absent}")
    if frame.empty:
        raise ValueError("available-cell frame is empty")
    df = frame.copy()
    for k in ("taxon", "region", "cell_id", "spatial_block"):
        if df[k].isna().any() or (df[k].astype(str).str.strip() == "").any():
            raise ValueError(f"missing or blank {k}")
        df[k] = df[k].astype(str)
    if df.duplicated(["taxon", "region", "cell_id"]).any():
        raise ValueError("each taxon-region-cell_id must occur only once")
    for k in ("temperature", "moisture", "effort", "n_occ"):
        df[k] = pd.to_numeric(df[k], errors="coerce")
        if not np.isfinite(df[k].to_numpy(dtype=float)).all():
            raise ValueError(f"nonfinite {k}")
    if (df.effort <= 0).any():
        raise ValueError("effort must be >0 in every available cell; do not replace missing effort with zero")
    if (df.n_occ < 0).any() or not np.all(df.n_occ == np.floor(df.n_occ)):
        raise ValueError("n_occ must be nonnegative integer record counts")
    # Stable ordering prevents input-row permutation changing the statistics.
    return df.sort_values(["taxon", "region", "cell_id"], kind="mergesort").reset_index(drop=True)


def _features(df: pd.DataFrame) -> np.ndarray:
    raw = df[["temperature", "moisture"]].to_numpy(dtype=float)
    means = raw.mean(axis=0)
    scales = raw.std(axis=0)
    if np.any(scales <= 1e-12):
        raise ValueError("taxon's available environment has a constant temperature or moisture axis")
    t, w = ((raw - means) / scales).T
    return np.column_stack([t, t * t, w, w * w, t * w])


def _fit(x: np.ndarray, q: np.ndarray, y: np.ndarray, regions: np.ndarray,
         cols: tuple[int, ...], ridge: float) -> np.ndarray:
    """Conditional multinomial likelihood per region; region intercepts cancel."""
    a = x[:, cols]
    if len(a) < 2 or y.sum() < 2:
        raise ValueError("too few cells/records")
    groups = [(regions == r) for r in np.unique(regions)]
    groups = [m for m in groups if y[m].sum() > 0]
    if not groups:
        raise ValueError("no observed records")
    offset = np.log(q)
    n = float(y.sum())

    def loss_and_grad(beta: np.ndarray) -> tuple[float, np.ndarray]:
        eta = a @ beta + offset
        ll = float(y @ (a @ beta))
        grad = y @ a
        for mask in groups:
            vals = eta[mask]
            lse = logsumexp(vals)
            n_r = float(y[mask].sum())
            prob = np.exp(vals - lse)
            ll -= n_r * lse
            grad -= n_r * (prob @ a[mask])
        return -ll / n + ridge * float(beta @ beta) / 2, -grad / n + ridge * beta

    result = minimize(loss_and_grad, np.zeros(a.shape[1]), method="L-BFGS-B", jac=True,
                      options={"maxiter": 350, "ftol": 1e-10, "gtol": 1e-7})
    if not result.success and np.linalg.norm(result.jac) > 0.001:
        raise RuntimeError(f"conditional model did not converge: {result.message}")
    return result.x


def _test_logscore(x: np.ndarray, q: np.ndarray, y: np.ndarray,
                   beta: np.ndarray, cols: tuple[int, ...]) -> float:
    if y.sum() == 0:
        raise ValueError("empty test presence block")
    logits = x[:, cols] @ beta + np.log(q)
    return float(y @ (logits - logsumexp(logits)) / y.sum())


def _spatial_folds(df: pd.DataFrame, *, min_test_records: int) -> dict[str, np.ndarray]:
    """Exactly two fixed, whole-block folds in each geographic region."""
    folds = {}
    for region, part in df.groupby("region", sort=True):
        blocks = sorted(part.spatial_block.unique())
        if len(blocks) < 4:
            raise ValueError(f"{region}: at least four spatial blocks required")
        test = np.array([blocks.index(b) % 2 for b in part.spatial_block])
        for fold in (0, 1):
            test_records = float(part.n_occ.to_numpy()[test == fold].sum())
            train_records = float(part.n_occ.to_numpy()[test != fold].sum())
            if min(test_records, train_records) < min_test_records:
                raise ValueError(f"{region}: insufficient presence records in one spatial fold")
            if min(sum(test == fold), sum(test != fold)) < 2:
                raise ValueError(f"{region}: fewer than two available cells in a spatial fold")
        folds[str(region)] = test
    return folds


def _region_gains(df: pd.DataFrame, x: np.ndarray, y: np.ndarray,
                  folds: dict[str, np.ndarray], ridge: float) -> dict[str, dict[str, float]]:
    out = {}
    for r, part in df.groupby("region", sort=True):
        ids = part.index.to_numpy()
        q = part.effort.to_numpy(float)
        yt = y[ids]
        xx = x[ids]
        f = folds[str(r)]
        scores = {name: 0.0 for name in FEATURE_SETS}
        total = 0.0
        for holdout in (0, 1):
            train, test = f != holdout, f == holdout
            ntest = float(yt[test].sum())
            total += ntest
            for name, cols in FEATURE_SETS.items():
                beta = _fit(xx[train], q[train], yt[train], np.zeros(sum(train)), cols, ridge)
                scores[name] += ntest * _test_logscore(xx[test], q[test], yt[test], beta, cols)
        gain_t = (scores["full"] - scores["without_temperature"]) / total
        gain_w = (scores["full"] - scores["without_moisture"]) / total
        out[str(r)] = {
            "temperature_gain_nats_per_record": float(gain_t),
            "moisture_gain_nats_per_record": float(gain_w),
            "thermal_minus_moisture": float(gain_t - gain_w),
            "records": int(yt.sum()),
            "cells": len(ids),
            "blocks": len(np.unique(part.spatial_block)),
        }
    return out


def _turnover_stat(by_region: dict[str, dict[str, float]], minimum_contrast: float) -> dict[str, object]:
    contrasts = np.array([v["thermal_minus_moisture"] for v in by_region.values()])
    return {
        "spread_nats_per_record": float(np.ptp(contrasts)),
        "direction_reversal": bool(contrasts.min() < -minimum_contrast and contrasts.max() > minimum_contrast),
    }



def _availability_overlap(df: pd.DataFrame, bins: int = 6) -> dict[str, float]:
    """Pairwise shared environmental support (coarse, equal-area-cell proxy).

    Binning is defined from the pooled *available* environmental cells, without
    inspecting occurrence counts. Values are diagnostics, not inferential gates.
    """
    if bins < 2:
        raise ValueError("bins must be >=2")
    coords = []
    for name in ("temperature", "moisture"):
        values = df[name].to_numpy(float)
        edges = np.unique(np.quantile(values, np.linspace(0, 1, bins + 1)[1:-1]))
        coords.append(np.searchsorted(edges, values, side="right"))
    joint = coords[0] * bins + coords[1]
    histograms = {}
    for region, part in df.groupby("region", sort=True):
        h = np.bincount(joint[part.index], minlength=bins * bins).astype(float)
        histograms[str(region)] = h / h.sum()
    pairwise = {}
    names = sorted(histograms)
    for i, region_a in enumerate(names):
        for region_b in names[i + 1:]:
            # 1 - total variation distance for binned equal-area availability.
            value = np.minimum(histograms[region_a], histograms[region_b]).sum()
            pairwise[f"{region_a} :: {region_b}"] = float(value)
    return pairwise


def analyze_taxon(frame: pd.DataFrame, *, replicates: int = 199, seed: int = 1,
                  ridge: float = 0.02, minimum_contrast: float = 0.01,
                  min_test_records: int = 5) -> dict[str, object]:
    """Parametric-bootstrap test of turnover beyond a shared global niche surface.

    Regions are predeclared; their environment cells and sampling effort weights
    are held fixed in every simulation. This is conditional on a fitted null,
    not proof of niche evolution or a causal limiting factor.
    """
    if replicates < 1 or ridge < 0 or minimum_contrast < 0 or min_test_records < 1:
        raise ValueError("invalid replicates, ridge, minimum_contrast or min_test_records")
    df = _check_frame(frame)
    if df.taxon.nunique() != 1 or df.region.nunique() < 2:
        raise ValueError("exactly one taxon and at least two regions are required")
    x = _features(df)
    folds = _spatial_folds(df, min_test_records=min_test_records)
    y = df.n_occ.to_numpy(dtype=float)
    q = df.effort.to_numpy(float)
    observed = _region_gains(df, x, y, folds, ridge)
    stat = _turnover_stat(observed, minimum_contrast)
    availability_overlap = _availability_overlap(df)

    # Shared slope/response surface, with regional intercepts absorbed by
    # conditional normalization; preserve regional count totals and q/M.
    null_beta = _fit(x, q, y, df.region.to_numpy(), FEATURE_SETS["full"], ridge)
    rng = np.random.default_rng(seed)
    null_spreads, null_reversals = [], []
    for _ in range(replicates):
        simulated = np.zeros(len(df), dtype=float)
        for _, part in df.groupby("region", sort=True):
            idx = part.index.to_numpy()
            logits = x[idx] @ null_beta + np.log(q[idx])
            weights = np.exp(logits - logsumexp(logits))
            simulated[idx] = rng.multinomial(int(y[idx].sum()), weights)
        try:
            gains = _region_gains(df, x, simulated, folds, ridge)
        except ValueError:
            # Simulated spatial-fold support failure is part of null evidence;
            # never drop failed draws and selectively shrink its denominator.
            raise RuntimeError("null simulation lost required spatial-fold presence support; design is underpowered")
        entry = _turnover_stat(gains, minimum_contrast)
        null_spreads.append(entry["spread_nats_per_record"])
        null_reversals.append(entry["direction_reversal"])
    null_spreads = np.asarray(null_spreads, dtype=float)
    return {
        "taxon": df.taxon.iloc[0],
        "n_regions": int(df.region.nunique()),
        "n_available_cells": int(len(df)),
        "n_records": int(y.sum()),
        "regions": observed,
        "observed": stat,
        "pairwise_available_environment_overlap": availability_overlap,
        "minimum_pairwise_available_environment_overlap": min(availability_overlap.values()),
        "null_shared_response_beta": dict(zip(FEATURES, map(float, null_beta))),
        "null_spread_median": float(np.median(null_spreads)),
        "null_spread_q95": float(np.quantile(null_spreads, 0.95)),
        "null_direction_reversal_rate": float(np.mean(null_reversals)),
        "one_sided_bootstrap_p": float((1 + np.sum(null_spreads >= stat["spread_nats_per_record"])) / (replicates + 1)),
        "replicates": int(replicates),
        "seed": int(seed),
        "ridge": float(ridge),
        "minimum_contrast": float(minimum_contrast),
        "mode": "exploratory_presence_record_information_not_causal_limits",
    }


def analyze_table(frame: pd.DataFrame, **kwargs) -> dict[str, object]:
    df = _check_frame(frame)
    results, exclusions = [], []
    for taxon, part in df.groupby("taxon", sort=True):
        try:
            # Independent reproducible RNG substream for each species.
            seed = kwargs.get("seed", 1)
            derived_seed = int.from_bytes(hashlib.sha256((str(seed) + ":" + taxon).encode()).digest()[:4], "big")
            options = {**kwargs, "seed": derived_seed}
            results.append(analyze_taxon(part, **options))
        except (ValueError, RuntimeError) as e:
            exclusions.append({"taxon": taxon, "reason": str(e)})
    return {"analysis": "geographic_driver_turnover_v0", "results": results, "exclusions": exclusions,
            "n_eligible_taxa": len(results), "n_excluded_taxa": len(exclusions),
            "fixed_information_boundary": "NOT Product A/B promotion; no physiological or evolutionary inference"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replicates", type=int, default=199)
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--ridge", type=float, default=0.02)
    parser.add_argument("--min-test-records", type=int, default=5)
    parser.add_argument("--minimum-contrast", type=float, default=0.01)
    args = parser.parse_args()
    if args.input.suffix.lower() != ".csv":
        raise SystemExit("v0 accepts CSV available-cell inputs only")
    frame = pd.read_csv(args.input)
    options = {"replicates": args.replicates, "seed": args.seed, "ridge": args.ridge,
               "min_test_records": args.min_test_records, "minimum_contrast": args.minimum_contrast}
    receipt = analyze_table(frame, **options)
    receipt["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    receipt["options"] = options
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"eligible={receipt['n_eligible_taxa']} excluded={receipt['n_excluded_taxa']} output={args.output}")


if __name__ == "__main__":
    main()
