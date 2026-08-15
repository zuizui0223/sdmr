"""Inner spatial-CV evaluation for ecological niche-recovery tuning.

The audit transform is fitted on training-background environments only. Candidate
models then predict suitability over held-out-background environments, and the
resulting weighted environmental distribution is compared with held-out
occurrences in the frozen audit space.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from .metrics import continuous_boyce_index, presence_rank_score
from .model import ModelSpec, fit_relative_suitability_model, score_relative_suitability
from .model_criteria import or10
from .niche_recovery import (
    NicheRecoveryProfile,
    _complete_matrix,
    _schoener_d_pc12,
    _weighted_quantile,
)
from .niche_recovery_selection import NicheRecoverySelection, select_niche_recovery_protocol


@dataclass(frozen=True)
class RecoveryCandidate:
    name: str
    predictors: tuple[str, ...]
    model_spec: ModelSpec


def heldout_niche_recovery_profile(
    audit_fit_background: pd.DataFrame,
    evaluation_background: pd.DataFrame,
    heldout_occurrences: pd.DataFrame,
    evaluation_suitability: Sequence[float] | np.ndarray,
    audit_predictors: Sequence[str],
    *,
    max_components: int = 4,
    quantiles: Sequence[float] = (0.05, 0.25, 0.50, 0.75, 0.95),
    overlap_bins: int = 20,
) -> NicheRecoveryProfile:
    """Evaluate niche recovery in a held-out environment using a train-fitted audit basis."""

    fit_env, _ = _complete_matrix(audit_fit_background, audit_predictors)
    reference, ref_valid = _complete_matrix(evaluation_background, audit_predictors)
    heldout, _ = _complete_matrix(heldout_occurrences, audit_predictors)
    raw_weights = np.asarray(evaluation_suitability, dtype=float)
    if raw_weights.ndim != 1 or len(raw_weights) != len(evaluation_background):
        raise ValueError("evaluation_suitability must align with evaluation_background")
    weights = raw_weights[ref_valid]
    valid_weight = np.isfinite(weights) & (weights >= 0)
    reference = reference[valid_weight]
    weights = weights[valid_weight]

    if len(fit_env) < 5 or len(reference) < 5 or len(heldout) < 2 or float(weights.sum()) <= 0:
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

    weights = weights / weights.sum()
    predicted_centroid = np.average(reference_pc, axis=0, weights=weights)
    observed_centroid = heldout_pc.mean(axis=0)
    centroid_distance = float(np.sqrt(np.mean((predicted_centroid - observed_centroid) ** 2)))

    predicted_var = np.average((reference_pc - predicted_centroid) ** 2, axis=0, weights=weights)
    observed_var = np.mean((heldout_pc - observed_centroid) ** 2, axis=0)
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
        predicted_q = _weighted_quantile(reference_pc[:, axis], weights, q)
        observed_q = np.quantile(heldout_pc[:, axis], q)
        errors.extend((predicted_q - observed_q).tolist())
    quantile_error = float(np.sqrt(np.mean(np.square(errors)))) if errors else float("nan")
    schoener_d = _schoener_d_pc12(reference_pc, weights, heldout_pc, bins=overlap_bins)

    inside = np.ones(len(heldout_pc), dtype=bool)
    for axis in range(min(2, n_components)):
        lower, upper = _weighted_quantile(reference_pc[:, axis], weights, (0.05, 0.95))
        inside &= (heldout_pc[:, axis] >= lower) & (heldout_pc[:, axis] <= upper)

    return NicheRecoveryProfile(
        n_audit_components=n_components,
        n_reference=len(reference_pc),
        n_sealed_occurrences=len(heldout_pc),
        niche_overlap_schoener_d_pc12=schoener_d,
        centroid_distance=centroid_distance,
        breadth_log_sd_error=breadth_error,
        quantile_profile_error=quantile_error,
        sealed_pc12_envelope_coverage90=float(np.mean(inside)),
    )


def cross_validated_niche_recovery(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    predictors: Sequence[str],
    audit_predictors: Sequence[str],
    *,
    n_splits: int = 4,
    model_spec: ModelSpec | None = None,
) -> pd.DataFrame:
    """Return fold-level prediction and niche-recovery diagnostics from model-pool spatial CV."""

    groups = np.unique(presence_groups)
    folds = min(int(n_splits), len(groups))
    if folds < 2:
        raise ValueError("At least two spatial blocks are required for niche-recovery CV")
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
            profile = heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                test_b_scores,
                audit_predictors,
            )
        except (ValueError, np.linalg.LinAlgError):
            continue
        row = {
            "fold": fold,
            "presence_rank": presence_rank_score(test_p_scores, test_b_scores),
            "continuous_boyce": continuous_boyce_index(test_p_scores, test_b_scores),
            "or10": or10(train_p_scores, test_p_scores),
            "n_model_presence": len(p_train),
            "n_heldout_presence": len(p_test),
            "n_model_background": len(b_train),
            "n_heldout_background": len(b_test),
            **profile.as_dict(),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def benchmark_niche_recovery_candidates(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    candidates: Mapping[str, RecoveryCandidate],
    audit_predictors: Sequence[str],
    *,
    n_splits: int = 4,
) -> tuple[pd.DataFrame, NicheRecoverySelection]:
    """Evaluate candidate protocols and select one by ecological recovery only."""

    frames = []
    for name in sorted(candidates):
        candidate = candidates[name]
        frame = cross_validated_niche_recovery(
            presence,
            background,
            presence_groups,
            background_groups,
            candidate.predictors,
            audit_predictors,
            n_splits=n_splits,
            model_spec=candidate.model_spec,
        )
        if len(frame):
            frame["candidate"] = str(name)
            frame["n_predictors"] = len(candidate.predictors)
            frame["model"] = candidate.model_spec.label
            frames.append(frame)
    if not frames:
        raise ValueError("no niche-recovery candidate could be evaluated")
    metrics = pd.concat(frames, ignore_index=True)
    selection = select_niche_recovery_protocol(metrics)
    return metrics, selection
