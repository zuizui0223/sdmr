"""Procedure-level ecological surface stability for Product-A v2.2.

Every outer spatial refit reruns the complete predictor-selection procedure on its
training rows, fits a record model, and projects the resulting ecological model
onto one deterministic model-pool background reference. Declared observation
terms are marginalized against the same full model-pool background distribution
for every refit.

Held-out niche recovery and common-reference response-surface stability remain
separate evidence layers. They are never summed into a weighted score.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import continuous_boyce_index, presence_rank_score
from .model import (
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .model_criteria import or10
from .niche_recovery_cv import ecological_surface_stability_profile
from .niche_recovery_procedure import (
    RecoveryProcedure,
    RecoveryProcedureBenchmark,
    _select_fold_predictors,
)
from .niche_recovery_stability import (
    GeneralizationGatedStableNicheRecoverySelection,
    select_generalization_gated_stable_niche_recovery_protocol,
)
from .observation_corrected_recovery import (
    observation_corrected_heldout_niche_recovery_profile,
)
from .observation_process import inverse_observation_propensity_weights


def _unique_predictors(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values))


def _deterministic_model_pool_reference(
    background: pd.DataFrame,
    *,
    max_rows: int,
) -> pd.DataFrame:
    """Return one deterministic common reference without held-out responses."""

    if int(max_rows) < 5:
        raise ValueError("max_stability_reference_rows must be >= 5")
    if len(background) < 5:
        raise ValueError("model-pool background must contain at least five rows")
    frame = background.reset_index(drop=True)
    if len(frame) <= int(max_rows):
        return frame.copy()
    indices = np.unique(
        np.rint(np.linspace(0, len(frame) - 1, int(max_rows))).astype(int)
    )
    return frame.iloc[indices].reset_index(drop=True)


def _heldout_profile_payload(profile) -> dict[str, object]:
    """Use explicit outer-heldout names at the v2.2 procedure boundary."""

    payload = dict(profile.as_dict())
    if "n_sealed_occurrences" in payload:
        payload["n_outer_heldout_occurrences"] = payload.pop(
            "n_sealed_occurrences"
        )
    if "sealed_pc12_envelope_coverage90" in payload:
        payload["heldout_pc12_envelope_coverage90"] = payload.pop(
            "sealed_pc12_envelope_coverage90"
        )
    return payload


def cross_validated_recovery_procedure_with_surface_stability(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    ecological_predictors: Sequence[str],
    audit_predictors: Sequence[str],
    procedure: RecoveryProcedure,
    *,
    observation_correction_active: bool = False,
    outer_folds: int = 4,
    observation_weight_truncation_quantile: float = 0.99,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_stability_reference_rows: int = 256,
) -> RecoveryProcedureBenchmark:
    """Evaluate one procedure and its ecological surface stability by outer CV.

    The common stability reference and the nuisance marginalization distribution
    are both derived from the complete model-pool background. No held-out
    occurrence response or authoritative outer-sealed row is accepted by this
    function.
    """

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("spatial group arrays must align with model-pool rows")
    folds = min(int(outer_folds), len(np.unique(p_groups)))
    if folds < 2:
        raise ValueError("at least two outer spatial blocks are required")

    observation = _unique_predictors(procedure.observation_predictors)
    stability_reference = _deterministic_model_pool_reference(
        background,
        max_rows=int(max_stability_reference_rows),
    )
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    rows: list[dict[str, object]] = []
    traces: list[pd.DataFrame] = []
    stability_surfaces: list[np.ndarray] = []

    for outer_fold, (train_idx, test_idx) in enumerate(
        splitter.split(dummy, groups=p_groups)
    ):
        train_blocks = np.unique(p_groups[train_idx])
        test_blocks = np.unique(p_groups[test_idx])
        bg_train_mask = np.isin(b_groups, train_blocks)
        bg_test_mask = np.isin(b_groups, test_blocks)
        if bg_train_mask.sum() < 5 or bg_test_mask.sum() < 5 or len(test_idx) < 2:
            continue

        p_train = presence.iloc[train_idx].reset_index(drop=True)
        p_test = presence.iloc[test_idx].reset_index(drop=True)
        b_train = background.loc[bg_train_mask].reset_index(drop=True)
        b_test = background.loc[bg_test_mask].reset_index(drop=True)
        p_train_groups = p_groups[train_idx]
        b_train_groups = b_groups[bg_train_mask]

        try:
            selected, trace = _select_fold_predictors(
                p_train,
                b_train,
                p_train_groups,
                b_train_groups,
                ecological_predictors,
                audit_predictors,
                procedure,
                observation_correction_active=observation_correction_active,
                observation_weight_truncation_quantile=(
                    observation_weight_truncation_quantile
                ),
                chance_auc=chance_auc,
                minimum_auc_margin=minimum_auc_margin,
                auc_sem_multiplier=auc_sem_multiplier,
            )
            model = fit_relative_suitability_model(
                p_train,
                b_train,
                selected,
                model_spec=procedure.model_spec,
            )
            train_p_scores = score_relative_suitability(model, p_train, selected)
            test_p_scores = score_relative_suitability(model, p_test, selected)
            test_b_scores = score_relative_suitability(model, b_test, selected)
            ecological_b_scores = score_ecological_suitability(
                model,
                b_test,
                selected,
                observation_predictors=observation,
                observation_reference=b_train,
            )
            common_ecological_scores = score_ecological_suitability(
                model,
                stability_reference,
                selected,
                observation_predictors=observation,
                observation_reference=background,
            )
            weights = inverse_observation_propensity_weights(
                p_train,
                b_train,
                p_test,
                observation if observation_correction_active else (),
                truncation_quantile=observation_weight_truncation_quantile,
            )
            profile = observation_corrected_heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                ecological_b_scores,
                weights.weights,
                audit_predictors,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            continue

        ecological_selected = tuple(
            predictor
            for predictor in selected
            if predictor not in set(observation)
        )
        rows.append(
            {
                "fold": int(outer_fold),
                "candidate": procedure.label,
                "procedure": procedure.label,
                "strategy": procedure.strategy,
                "model": procedure.model_spec.label,
                "selected_predictors": ",".join(selected),
                "selected_ecological_predictors": ",".join(
                    ecological_selected
                ),
                "n_predictors": len(selected),
                "n_ecological_predictors": len(ecological_selected),
                "presence_rank": presence_rank_score(
                    test_p_scores,
                    test_b_scores,
                ),
                "continuous_boyce": continuous_boyce_index(
                    test_p_scores,
                    test_b_scores,
                ),
                "or10": or10(train_p_scores, test_p_scores),
                "observation_correction_active": bool(
                    observation_correction_active
                ),
                "observation_weight_ess": weights.effective_sample_size,
                "n_model_presence": len(p_train),
                "n_outer_heldout_presence": len(p_test),
                "n_model_background": len(b_train),
                "n_outer_heldout_background": len(b_test),
                "stability_reference_rows": len(stability_reference),
                **_heldout_profile_payload(profile),
            }
        )
        stability_surfaces.append(common_ecological_scores)
        if not trace.empty:
            trace = trace.copy()
            trace["outer_fold"] = int(outer_fold)
            trace["procedure"] = procedure.label
            traces.append(trace)

    stability = ecological_surface_stability_profile(stability_surfaces)
    for row in rows:
        row.update(stability)

    return RecoveryProcedureBenchmark(
        fold_metrics=pd.DataFrame(rows),
        selection_trace=(
            pd.concat(traces, ignore_index=True) if traces else pd.DataFrame()
        ),
    )


def benchmark_recovery_procedures_with_surface_stability(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    ecological_predictors: Sequence[str],
    audit_predictors: Sequence[str],
    procedures: Sequence[RecoveryProcedure],
    *,
    observation_correction_active: bool = False,
    outer_folds: int = 4,
    observation_weight_truncation_quantile: float = 0.99,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_stability_reference_rows: int = 256,
) -> RecoveryProcedureBenchmark:
    """Evaluate predeclared procedures on identical outer folds and reference."""

    procedures = tuple(procedures)
    if not procedures:
        raise ValueError("at least one recovery procedure is required")
    labels = [procedure.label for procedure in procedures]
    if len(set(labels)) != len(labels):
        raise ValueError("recovery procedure labels must be unique")

    metric_frames: list[pd.DataFrame] = []
    trace_frames: list[pd.DataFrame] = []
    for procedure in procedures:
        result = cross_validated_recovery_procedure_with_surface_stability(
            presence,
            background,
            presence_groups,
            background_groups,
            ecological_predictors,
            audit_predictors,
            procedure,
            observation_correction_active=observation_correction_active,
            outer_folds=outer_folds,
            observation_weight_truncation_quantile=(
                observation_weight_truncation_quantile
            ),
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
            max_stability_reference_rows=max_stability_reference_rows,
        )
        if not result.fold_metrics.empty:
            metric_frames.append(result.fold_metrics)
        if not result.selection_trace.empty:
            trace_frames.append(result.selection_trace)

    if not metric_frames:
        raise ValueError("no recovery procedure produced evaluable outer folds")
    return RecoveryProcedureBenchmark(
        fold_metrics=pd.concat(metric_frames, ignore_index=True),
        selection_trace=(
            pd.concat(trace_frames, ignore_index=True)
            if trace_frames
            else pd.DataFrame()
        ),
    )


def select_stable_recovery_procedure(
    benchmark: RecoveryProcedureBenchmark,
    *,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
) -> GeneralizationGatedStableNicheRecoverySelection:
    """Select by adequacy, recovery, surface stability, then parsimony."""

    return select_generalization_gated_stable_niche_recovery_protocol(
        benchmark.fold_metrics,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
        max_mean_or10=max_mean_or10,
    )
