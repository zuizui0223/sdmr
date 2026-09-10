"""Matched-null route for the v8 conditional shared-information intervention.

The null starts from the exact v8 conditional-replacement values, then destroys
rowwise alignment with the conditioning processes while preserving the joint
marginal distribution of the replaced target-process closure separately within
each train/test presence/background frame.
"""
from __future__ import annotations

from collections.abc import Sequence
import hashlib

import numpy as np
import pandas as pd

from .conditional_shared_information_knockout import fit_conditional_shared_information_knockout
from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability, score_relative_suitability
from .observation_aware_identification import _weighted_presence_rank
from .proxy_closed_route_process_challenge import _presence_rank


def deterministic_joint_permutation(frame: pd.DataFrame, columns: Sequence[str], *, salt: str) -> pd.DataFrame:
    """Permute complete rows of ``columns`` jointly, preserving their exact multivariate distribution."""
    cols = tuple(str(x) for x in columns)
    if not cols:
        raise ValueError("columns must be non-empty")
    out = frame.copy()
    numeric = out[list(cols)].apply(pd.to_numeric, errors="coerce")
    valid = numeric.notna().all(axis=1).to_numpy()
    idx = np.flatnonzero(valid)
    if len(idx) < 2:
        return out
    keys = [hashlib.sha256(f"{salt}:{int(i)}".encode("utf-8")).digest() for i in range(len(idx))]
    order = np.argsort(np.asarray(keys, dtype="S32"), kind="mergesort")
    if np.array_equal(order, np.arange(len(idx))):
        order = np.roll(order, 1)
    values = numeric.iloc[idx].to_numpy(float)
    out.loc[out.index[idx], list(cols)] = values[order]
    return out


def matched_shrinkage_null_route_cv(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    conditioning_predictors: Sequence[str],
    ecological_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    model_spec: ModelSpec,
    folds,
    corrections,
    degree: int,
    ridge_alpha: float,
    density_probability_epsilon: float,
    null_salt: int,
) -> pd.DataFrame:
    """Evaluate one deterministic matched-null replicate using the v8 route geometry."""
    process_predictors = tuple(str(x) for x in process_predictors)
    conditioning_predictors = tuple(str(x) for x in conditioning_predictors)
    ecological_predictors = tuple(str(x) for x in ecological_predictors)
    observation_predictors = tuple(str(x) for x in observation_predictors)
    rows = []
    route = f"conditional_shrinkage_null::{int(null_salt)}::{model_spec.label}::{process}"
    for fold, ((p_train_idx, b_train_idx, p_test_idx, b_test_idx), correction) in enumerate(zip(folds, corrections, strict=True)):
        row = {
            "route": route,
            "route_type": "conditional_shrinkage_matched_null",
            "excluded_process": str(process),
            "model_label": model_spec.label,
            "fold": int(fold),
            "complete": False,
            "presence_rank": np.nan,
            "ecological_presence_rank": np.nan,
            "balanced_density_log_score": np.nan,
            "ecological_density_log_score": np.nan,
        }
        try:
            if not correction.complete:
                raise ValueError("candidate-independent observation correction unavailable")
            p_train = presence.iloc[p_train_idx].reset_index(drop=True)
            b_train = background.iloc[b_train_idx].reset_index(drop=True)
            p_test = presence.iloc[p_test_idx].reset_index(drop=True)
            b_test = background.iloc[b_test_idx].reset_index(drop=True)
            if min(len(p_train), len(b_train), len(p_test), len(b_test)) < 2:
                raise ValueError("fold lacks sufficient rows")
            knockout = fit_conditional_shared_information_knockout(
                b_train,
                process=str(process),
                process_predictors=process_predictors,
                conditioning_predictors=conditioning_predictors,
                degree=int(degree),
                ridge_alpha=float(ridge_alpha),
                minimum_complete_rows=5,
            )
            transformed = []
            for label, frame in (("pt", p_train), ("bt", b_train), ("pe", p_test), ("be", b_test)):
                conditional = knockout.transform(frame)
                null = deterministic_joint_permutation(
                    conditional,
                    process_predictors,
                    salt=f"{int(null_salt)}:{process}:{model_spec.label}:{fold}:{label}",
                )
                transformed.append(null)
            p_train_k, b_train_k, p_test_k, b_test_k = transformed
            model_predictors = ecological_predictors + observation_predictors
            model = fit_relative_suitability_model(p_train_k, b_train_k, model_predictors, model_spec=model_spec)
            p_full = score_relative_suitability(model, p_test_k, model_predictors)
            b_full = score_relative_suitability(model, b_test_k, model_predictors)
            p_eco = score_ecological_suitability(
                model, p_test_k, model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_k,
            )
            b_eco = score_ecological_suitability(
                model, b_test_k, model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_k,
            )
            values = (
                _presence_rank(p_full, b_full),
                _weighted_presence_rank(p_eco, b_eco, correction.weights),
                balanced_density_ratio_log_score(p_full, b_full, probability_epsilon=float(density_probability_epsilon)),
                balanced_density_ratio_log_score(
                    p_eco, b_eco, presence_weights=correction.weights,
                    probability_epsilon=float(density_probability_epsilon),
                ),
            )
            if not all(np.isfinite(float(x)) for x in values):
                raise ValueError("null route produced non-finite evidence")
            row.update({
                "complete": True,
                "presence_rank": float(values[0]),
                "ecological_presence_rank": float(values[1]),
                "balanced_density_log_score": float(values[2]),
                "ecological_density_log_score": float(values[3]),
            })
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
    return pd.DataFrame(rows)
