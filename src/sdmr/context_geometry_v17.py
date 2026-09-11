"""Background-only target-context geometry features for v17 development."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import PolynomialFeatures


@dataclass(frozen=True)
class ContextGeometry:
    conditional_residual_shift: float
    conditional_residual_scale_ratio: float
    conditional_target_r2: float
    process_support_shift: float
    conditioning_support_shift: float
    n_reference: int
    n_target: int


def _complete(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    if not columns:
        raise ValueError("feature set must be non-empty")
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise KeyError(f"missing columns: {missing}")
    # Always use list-like column selection. A singleton tuple can be treated as
    # a scalar-like key by pandas, yielding a Series and causing downstream
    # multi-output residual broadcasting to create an (n, n) matrix.
    vals = frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    return vals.loc[np.isfinite(vals.to_numpy(float)).all(axis=1)].copy()


def _standardized_mean_shift(reference: pd.DataFrame, target: pd.DataFrame, columns: tuple[str, ...]) -> float:
    ref = _complete(reference, columns)
    tgt = _complete(target, columns)
    if len(ref) < 3 or len(tgt) < 2:
        return float("nan")
    mu = ref.mean(axis=0).to_numpy(float)
    sd = ref.std(axis=0, ddof=1).to_numpy(float)
    sd = np.where(np.isfinite(sd) & (sd > 1e-12), sd, 1.0)
    z = (tgt.mean(axis=0).to_numpy(float) - mu) / sd
    return float(np.sqrt(np.mean(z**2)))


def context_geometry_features(
    reference_background: pd.DataFrame,
    target_background: pd.DataFrame,
    *,
    process_predictors: tuple[str, ...],
    conditioning_predictors: tuple[str, ...],
    degree: int = 2,
    ridge_alpha: float = 1e-3,
    minimum_reference_rows: int = 20,
    minimum_target_rows: int = 5,
) -> ContextGeometry:
    """Compute process-specific geometry using background rows only.

    A conditional map from non-process predictors to the target-process closure is
    fit on reference background rows. The held-out target block is never used to
    fit the map or the standardization constants.
    """
    if set(process_predictors) & set(conditioning_predictors):
        raise ValueError("process and conditioning predictors must be disjoint")
    all_cols = tuple(dict.fromkeys((*process_predictors, *conditioning_predictors)))
    ref = _complete(reference_background, all_cols)
    tgt = _complete(target_background, all_cols)
    if len(ref) < int(minimum_reference_rows) or len(tgt) < int(minimum_target_rows):
        return ContextGeometry(*(float("nan"),) * 5, n_reference=len(ref), n_target=len(tgt))

    x_ref = ref.loc[:, list(conditioning_predictors)].to_numpy(float)
    x_tgt = tgt.loc[:, list(conditioning_predictors)].to_numpy(float)
    y_ref = ref.loc[:, list(process_predictors)].to_numpy(float)
    y_tgt = tgt.loc[:, list(process_predictors)].to_numpy(float)
    poly = PolynomialFeatures(degree=int(degree), include_bias=True)
    z_ref = poly.fit_transform(x_ref)
    z_tgt = poly.transform(x_tgt)
    model = Ridge(alpha=float(ridge_alpha), fit_intercept=False)
    model.fit(z_ref, y_ref)
    pred_ref = np.asarray(model.predict(z_ref), float)
    pred_tgt = np.asarray(model.predict(z_tgt), float)
    if pred_ref.ndim == 1:
        pred_ref = pred_ref.reshape(-1, 1)
    if pred_tgt.ndim == 1:
        pred_tgt = pred_tgt.reshape(-1, 1)
    if y_ref.ndim == 1:
        y_ref = y_ref.reshape(-1, 1)
    if y_tgt.ndim == 1:
        y_tgt = y_tgt.reshape(-1, 1)
    ref_resid = y_ref - pred_ref
    tgt_resid = y_tgt - pred_tgt

    ref_sd = np.std(ref_resid, axis=0, ddof=1)
    ref_sd = np.where(np.isfinite(ref_sd) & (ref_sd > 1e-12), ref_sd, 1.0)
    residual_shift = float(np.sqrt(np.mean((np.mean(tgt_resid, axis=0) / ref_sd) ** 2)))
    tgt_sd = np.std(tgt_resid, axis=0, ddof=1)
    scale_ratio = float(np.sqrt(np.mean((tgt_sd / ref_sd) ** 2)))

    r2s = []
    for j in range(y_tgt.shape[1]):
        if np.std(y_tgt[:, j]) <= 1e-12:
            continue
        r2s.append(float(r2_score(y_tgt[:, j], pred_tgt[:, j])))
    target_r2 = float(np.mean(r2s)) if r2s else float("nan")
    p_shift = _standardized_mean_shift(ref, tgt, process_predictors)
    q_shift = _standardized_mean_shift(ref, tgt, conditioning_predictors)
    return ContextGeometry(
        conditional_residual_shift=residual_shift,
        conditional_residual_scale_ratio=scale_ratio,
        conditional_target_r2=target_r2,
        process_support_shift=p_shift,
        conditioning_support_shift=q_shift,
        n_reference=len(ref),
        n_target=len(tgt),
    )
