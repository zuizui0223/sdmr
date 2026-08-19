"""Inner spatial-CV evaluation for ecological niche-recovery tuning.

Conventional prediction diagnostics use the full observation-aware model score.
Ecological recovery uses a separate score in which explicitly declared
observation-process predictors are marginalized over background values. Thus
sampling/detectability covariates can help fit records without being treated as
axes of the ecological niche.

A second, deliberately different robustness object is also reported: every
spatial refit is projected onto the same fixed background reference and its
observation nuisance variables are marginalized against the same reference
distribution. Pairwise agreement among those ecological surfaces asks whether the
*inferred niche itself* is stable to spatial refitting, rather than asking whether
a finite held-out occurrence sample happens to match one fold particularly well.
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
from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .model_criteria import or10
from .niche_recovery import (
    NicheRecoveryProfile,
    _complete_matrix,
    _schoener_d_pc12,
    _weighted_quantile,
)
from .niche_recovery_selection import NicheRecoverySelection, select_niche_recovery_protocol


SURFACE_STABILITY_DIRECTIONS = {
    "ecological_surface_stability_rank_mean": "max",
    "ecological_surface_stability_rank_min": "max",
    "ecological_surface_stability_nrmse_mean": "min",
    "ecological_surface_stability_nrmse_max": "min",
}


@dataclass(frozen=True)
class RecoveryCandidate:
    name: str
    predictors: tuple[str, ...]
    model_spec: ModelSpec
    observation_predictors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        unknown = sorted(set(self.observation_predictors) - set(self.predictors))
        if unknown:
            raise ValueError(f"observation predictors are not model predictors: {unknown}")


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


def _surface_rank_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman-style rank agreement, with explicit constant-surface semantics."""

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    keep = np.isfinite(a) & np.isfinite(b)
    a = a[keep]
    b = b[keep]
    if len(a) < 5:
        return float("nan")
    a_constant = bool(np.allclose(a, a[0], rtol=0.0, atol=1e-12))
    b_constant = bool(np.allclose(b, b[0], rtol=0.0, atol=1e-12))
    if a_constant and b_constant:
        # Stability is distinct from ecological information. Two identical flat
        # surfaces are perfectly stable; the preceding recovery gate is what
        # prevents a biologically uninformative flat model from winning.
        return 1.0 if np.allclose(a, b, rtol=1e-9, atol=1e-12) else 0.0
    if a_constant or b_constant:
        return 0.0
    ar = _average_ranks(a)
    br = _average_ranks(b)
    ar -= ar.mean()
    br -= br.mean()
    denom = float(np.sqrt(np.sum(ar * ar) * np.sum(br * br)))
    if not denom > 0:
        return float("nan")
    return float(np.sum(ar * br) / denom)


def _unit_scale(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    lo = float(np.min(x))
    hi = float(np.max(x))
    if not hi > lo:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _surface_nrmse(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    keep = np.isfinite(a) & np.isfinite(b)
    a = a[keep]
    b = b[keep]
    if len(a) < 5:
        return float("nan")
    return float(np.sqrt(np.mean((_unit_scale(a) - _unit_scale(b)) ** 2)))


def _deterministic_reference(frame: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if max_rows < 5:
        raise ValueError("max_stability_reference_rows must be >= 5")
    if len(frame) <= max_rows:
        return frame.reset_index(drop=True)
    index = np.unique(np.rint(np.linspace(0, len(frame) - 1, int(max_rows))).astype(int))
    return frame.iloc[index].reset_index(drop=True)


def ecological_surface_stability_profile(
    surfaces: Sequence[Sequence[float] | np.ndarray],
) -> dict[str, float | int]:
    """Summarize agreement among ecological surfaces from independent refits.

    Both average and worst pairwise agreement are retained. These are diagnostics
    of response-surface stability only; they are not combined with held-out niche
    recovery into a weighted score.
    """

    arrays = [np.asarray(x, dtype=float) for x in surfaces]
    rank_values: list[float] = []
    nrmse_values: list[float] = []
    for i in range(len(arrays)):
        for j in range(i + 1, len(arrays)):
            rank = _surface_rank_correlation(arrays[i], arrays[j])
            error = _surface_nrmse(arrays[i], arrays[j])
            if np.isfinite(rank):
                rank_values.append(float(rank))
            if np.isfinite(error):
                nrmse_values.append(float(error))
    return {
        "n_surface_stability_pairs": int(min(len(rank_values), len(nrmse_values))),
        "ecological_surface_stability_rank_mean": (
            float(np.mean(rank_values)) if rank_values else float("nan")
        ),
        "ecological_surface_stability_rank_min": (
            float(np.min(rank_values)) if rank_values else float("nan")
        ),
        "ecological_surface_stability_nrmse_mean": (
            float(np.mean(nrmse_values)) if nrmse_values else float("nan")
        ),
        "ecological_surface_stability_nrmse_max": (
            float(np.max(nrmse_values)) if nrmse_values else float("nan")
        ),
    }


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
    observation_predictors: Sequence[str] = (),
    n_splits: int = 4,
    model_spec: ModelSpec | None = None,
    max_stability_reference_rows: int = 256,
) -> pd.DataFrame:
    """Return prediction, recovery and refit-stability diagnostics.

    ``presence_rank``, continuous Boyce and OR10 use the full model score because
    they evaluate prediction of records. The ecological profile uses suitability
    after marginalizing ``observation_predictors`` over model-background values.

    Surface stability is evaluated on one deterministic common subset of the
    model-pool background. No occurrence response from a held-out fold enters that
    common reference. For observation-process models, the same model-pool
    background distribution is used for nuisance marginalization in every refit,
    so instability reflects the fitted ecological response rather than a changing
    nuisance integration measure.
    """

    observation_predictors = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    unknown = sorted(set(observation_predictors) - set(predictors))
    if unknown:
        raise ValueError(f"observation predictors are not model predictors: {unknown}")

    groups = np.unique(presence_groups)
    folds = min(int(n_splits), len(groups))
    if folds < 2:
        raise ValueError("At least two spatial blocks are required for niche-recovery CV")
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    stability_reference = _deterministic_reference(background, int(max_stability_reference_rows))
    rows: list[dict[str, float | int]] = []
    stability_surfaces: list[np.ndarray] = []
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
                observation_predictors=observation_predictors,
                observation_reference=b_train,
            )
            common_ecological_scores = score_ecological_suitability(
                model,
                stability_reference,
                predictors,
                observation_predictors=observation_predictors,
                observation_reference=background,
            )
            profile = heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                ecological_b_scores,
                audit_predictors,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            continue
        row = {
            "fold": fold,
            "presence_rank": presence_rank_score(test_p_scores, test_b_scores),
            "continuous_boyce": continuous_boyce_index(test_p_scores, test_b_scores),
            "or10": or10(train_p_scores, test_p_scores),
            "n_observation_predictors": len(observation_predictors),
            "n_model_presence": len(p_train),
            "n_heldout_presence": len(p_test),
            "n_model_background": len(b_train),
            "n_heldout_background": len(b_test),
            **profile.as_dict(),
        }
        rows.append(row)
        stability_surfaces.append(common_ecological_scores)

    stability = ecological_surface_stability_profile(stability_surfaces)
    for row in rows:
        row.update(stability)
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
            observation_predictors=candidate.observation_predictors,
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
