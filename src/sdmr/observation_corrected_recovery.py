"""Observation-corrected ecological niche recovery for Product-A v2.

Marginalizing observation-process predictors from a model prediction is only half
of the separation problem: withheld occurrence environments can themselves be
biased by the observation process. This module transports the held-out occurrence
distribution toward a common target-group observation reference using a
candidate-independent nuisance model fitted only on training data.

The ecological candidate model and the observation audit model are deliberately
separate:

- conventional AUC/CBI/OR10 use the candidate's full record-prediction score;
- the candidate's ecological suitability marginalizes its declared observation
  predictors;
- the held-out occurrence target is weighted by an audit-wide observation model
  using the same frozen nuisance predictor set for every candidate.

No hidden ecological truth is used by these weights.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from .metrics import continuous_boyce_index, presence_rank_score
from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .model_criteria import or10
from .niche_recovery import NicheRecoveryProfile, _complete_matrix, _weighted_quantile
from .observation_process import inverse_observation_propensity_weights


def _weighted_schoener_d_pc12(
    reference_scores: np.ndarray,
    reference_weights: np.ndarray,
    observed_scores: np.ndarray,
    observed_weights: np.ndarray,
    *,
    bins: int,
) -> float:
    if bins < 4:
        raise ValueError("bins must be >= 4")
    dims = min(2, reference_scores.shape[1], observed_scores.shape[1])
    if dims == 0:
        return float("nan")
    ref = reference_scores[:, :dims]
    obs = observed_scores[:, :dims]
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
    predicted, _, _ = np.histogram2d(
        ref[:, 0], ref[:, 1], bins=edges, weights=reference_weights
    )
    observed, _, _ = np.histogram2d(
        obs[:, 0], obs[:, 1], bins=edges, weights=observed_weights
    )
    if float(predicted.sum()) <= 0 or float(observed.sum()) <= 0:
        return float("nan")
    predicted = predicted / predicted.sum()
    observed = observed / observed.sum()
    return float(1.0 - 0.5 * np.abs(predicted - observed).sum())


def observation_corrected_heldout_niche_recovery_profile(
    audit_fit_background: pd.DataFrame,
    evaluation_background: pd.DataFrame,
    heldout_occurrences: pd.DataFrame,
    evaluation_suitability: Sequence[float] | np.ndarray,
    heldout_occurrence_weights: Sequence[float] | np.ndarray,
    audit_predictors: Sequence[str],
    *,
    max_components: int = 4,
    quantiles: Sequence[float] = (0.05, 0.25, 0.50, 0.75, 0.95),
    overlap_bins: int = 20,
) -> NicheRecoveryProfile:
    """Compare ecological suitability with observation-corrected held-out records."""

    fit_env, _ = _complete_matrix(audit_fit_background, audit_predictors)
    reference, ref_valid = _complete_matrix(evaluation_background, audit_predictors)
    heldout, heldout_valid = _complete_matrix(heldout_occurrences, audit_predictors)

    raw_reference_weights = np.asarray(evaluation_suitability, dtype=float)
    if raw_reference_weights.ndim != 1 or len(raw_reference_weights) != len(evaluation_background):
        raise ValueError("evaluation_suitability must align with evaluation_background")
    reference_weights = raw_reference_weights[ref_valid]
    keep_reference = np.isfinite(reference_weights) & (reference_weights >= 0)
    reference = reference[keep_reference]
    reference_weights = reference_weights[keep_reference]

    raw_observed_weights = np.asarray(heldout_occurrence_weights, dtype=float)
    if raw_observed_weights.ndim != 1 or len(raw_observed_weights) != len(heldout_occurrences):
        raise ValueError("heldout_occurrence_weights must align with heldout_occurrences")
    observed_weights = raw_observed_weights[heldout_valid]
    keep_observed = np.isfinite(observed_weights) & (observed_weights >= 0)
    heldout = heldout[keep_observed]
    observed_weights = observed_weights[keep_observed]

    if (
        len(fit_env) < 5
        or len(reference) < 5
        or len(heldout) < 2
        or float(reference_weights.sum()) <= 0
        or float(observed_weights.sum()) <= 0
    ):
        return NicheRecoveryProfile(
            n_audit_components=0,
            n_reference=len(reference),
            n_sealed_occurrences=len(heldout),
            niche_overlap_schoener_d_pc12=float("nan"),
            centroid_distance=float("nan"),
            breadth_log_sd_error=float("nan"),
            quantile_profile_error=float("nan"),
            sealed_pc12_envelope_coverage90=float("nan"),
        )

    scaler = StandardScaler().fit(fit_env)
    fit_z = scaler.transform(fit_env)
    ref_z = scaler.transform(reference)
    heldout_z = scaler.transform(heldout)
    n_components = min(int(max_components), fit_z.shape[1], len(fit_z) - 1)
    if n_components < 1:
        raise ValueError("audit environment does not support a PCA component")
    pca = PCA(n_components=n_components, whiten=True, svd_solver="full").fit(fit_z)
    reference_pc = pca.transform(ref_z)
    heldout_pc = pca.transform(heldout_z)

    reference_weights = reference_weights / reference_weights.sum()
    observed_weights = observed_weights / observed_weights.sum()
    predicted_centroid = np.average(reference_pc, axis=0, weights=reference_weights)
    observed_centroid = np.average(heldout_pc, axis=0, weights=observed_weights)
    centroid_distance = float(np.sqrt(np.mean((predicted_centroid - observed_centroid) ** 2)))

    predicted_var = np.average(
        (reference_pc - predicted_centroid) ** 2, axis=0, weights=reference_weights
    )
    observed_var = np.average(
        (heldout_pc - observed_centroid) ** 2, axis=0, weights=observed_weights
    )
    eps = 1e-8
    breadth_error = float(
        np.mean(
            np.abs(
                np.log(
                    (np.sqrt(np.maximum(predicted_var, 0.0)) + eps)
                    / (np.sqrt(np.maximum(observed_var, 0.0)) + eps)
                )
            )
        )
    )

    q = tuple(float(x) for x in quantiles)
    errors: list[float] = []
    for axis in range(n_components):
        predicted_q = _weighted_quantile(reference_pc[:, axis], reference_weights, q)
        observed_q = _weighted_quantile(heldout_pc[:, axis], observed_weights, q)
        errors.extend((predicted_q - observed_q).tolist())
    quantile_error = float(np.sqrt(np.mean(np.square(errors)))) if errors else float("nan")
    schoener_d = _weighted_schoener_d_pc12(
        reference_pc,
        reference_weights,
        heldout_pc,
        observed_weights,
        bins=overlap_bins,
    )

    inside = np.ones(len(heldout_pc), dtype=bool)
    for axis in range(min(2, n_components)):
        lower, upper = _weighted_quantile(reference_pc[:, axis], reference_weights, (0.05, 0.95))
        inside &= (heldout_pc[:, axis] >= lower) & (heldout_pc[:, axis] <= upper)
    coverage = float(observed_weights[inside].sum()) if len(inside) else float("nan")

    return NicheRecoveryProfile(
        n_audit_components=n_components,
        n_reference=len(reference_pc),
        n_sealed_occurrences=len(heldout_pc),
        niche_overlap_schoener_d_pc12=schoener_d,
        centroid_distance=centroid_distance,
        breadth_log_sd_error=breadth_error,
        quantile_profile_error=quantile_error,
        sealed_pc12_envelope_coverage90=coverage,
    )


def cross_validated_observation_corrected_niche_recovery(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    predictors: Sequence[str],
    audit_predictors: Sequence[str],
    *,
    candidate_observation_predictors: Sequence[str] = (),
    audit_observation_predictors: Sequence[str] = (),
    n_splits: int = 4,
    model_spec: ModelSpec | None = None,
    observation_weight_truncation_quantile: float = 0.99,
) -> pd.DataFrame:
    """Return prediction and corrected niche-recovery metrics by spatial fold.

    The audit observation weights are identical for every candidate given the same
    train/test fold because they depend only on the frozen audit nuisance
    predictors and training focal/background rows.
    """

    candidate_observation_predictors = tuple(
        dict.fromkeys(str(x) for x in candidate_observation_predictors)
    )
    audit_observation_predictors = tuple(
        dict.fromkeys(str(x) for x in audit_observation_predictors)
    )
    unknown = sorted(set(candidate_observation_predictors) - set(predictors))
    if unknown:
        raise ValueError(f"candidate observation predictors are not model predictors: {unknown}")

    groups = np.unique(presence_groups)
    folds = min(int(n_splits), len(groups))
    if folds < 2:
        raise ValueError("At least two spatial blocks are required for corrected niche-recovery CV")
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    rows: list[dict[str, float | int]] = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(dummy, groups=presence_groups)):
        train_blocks = np.unique(presence_groups[train_idx])
        test_blocks = np.unique(presence_groups[test_idx])
        bg_train_mask = np.isin(background_groups, train_blocks)
        bg_test_mask = np.isin(background_groups, test_blocks)
        if bg_train_mask.sum() < 5 or bg_test_mask.sum() < 5 or len(test_idx) < 2:
            continue
        p_train = presence.iloc[train_idx].reset_index(drop=True)
        p_test = presence.iloc[test_idx].reset_index(drop=True)
        b_train = background.loc[bg_train_mask].reset_index(drop=True)
        b_test = background.loc[bg_test_mask].reset_index(drop=True)
        try:
            model = fit_relative_suitability_model(
                p_train,
                b_train,
                predictors,
                model_spec=model_spec,
            )
            train_p_scores = score_relative_suitability(model, p_train, predictors)
            test_p_scores = score_relative_suitability(model, p_test, predictors)
            test_b_scores = score_relative_suitability(model, b_test, predictors)
            ecological_b_scores = score_ecological_suitability(
                model,
                b_test,
                predictors,
                observation_predictors=candidate_observation_predictors,
                observation_reference=b_train,
            )
            observation_weights = inverse_observation_propensity_weights(
                p_train,
                b_train,
                p_test,
                audit_observation_predictors,
                truncation_quantile=observation_weight_truncation_quantile,
            )
            profile = observation_corrected_heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                ecological_b_scores,
                observation_weights.weights,
                audit_predictors,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            continue
        rows.append(
            {
                "fold": fold,
                "presence_rank": presence_rank_score(test_p_scores, test_b_scores),
                "continuous_boyce": continuous_boyce_index(test_p_scores, test_b_scores),
                "or10": or10(train_p_scores, test_p_scores),
                "n_candidate_observation_predictors": len(candidate_observation_predictors),
                "n_audit_observation_predictors": len(audit_observation_predictors),
                "observation_weight_ess": observation_weights.effective_sample_size,
                "observation_weight_max": observation_weights.maximum_normalized_weight,
                "observation_weight_truncation_cap": observation_weights.truncation_cap,
                "n_model_presence": len(p_train),
                "n_heldout_presence": len(p_test),
                "n_model_background": len(b_train),
                "n_heldout_background": len(b_test),
                **profile.as_dict(),
            }
        )
    return pd.DataFrame(rows)
