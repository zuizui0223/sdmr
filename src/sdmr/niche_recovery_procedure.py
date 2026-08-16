"""Nested procedure-level tuning for Product-A v2 ecological niche recovery.

The object being compared is a procedure, not one post-hoc frozen raster set.
Every outer spatial recovery fold reruns predictor selection using that fold's
training rows only. Held-out folds are used only to evaluate record diagnostics
and ecological niche recovery.

Strategies
----------
- ``all``: retain the full predeclared ecological predictor universe;
- ``vif``: VIF prune on the current outer-training background only;
- ``predictive_forward``: forward selection by inner spatial-CV record ranking;
- ``niche_forward``: forward selection by inner spatial-CV ecological recovery
  using prediction adequacy -> Pareto -> minimax.

Observation predictors are fixed nuisance terms and are never candidates for
ecological forward selection. No weighted prediction/ecology super-score is used.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .baselines import vif_prune_predictors
from .metrics import continuous_boyce_index, presence_rank_score
from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .model_criteria import or10
from .niche_recovery_selection import (
    GeneralizationGatedNicheRecoverySelection,
    select_generalization_gated_niche_recovery_protocol,
)
from .observation_corrected_recovery import (
    cross_validated_observation_corrected_niche_recovery,
    observation_corrected_heldout_niche_recovery_profile,
)
from .observation_process import inverse_observation_propensity_weights
from .selection import cross_validated_score


PROCEDURE_STRATEGIES = ("all", "vif", "predictive_forward", "niche_forward")


@dataclass(frozen=True)
class RecoveryProcedure:
    strategy: str
    model_spec: ModelSpec
    inner_folds: int = 3
    max_predictors: int | None = 8
    vif_threshold: float = 5.0
    predictive_min_gain: float = 0.005
    observation_predictors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.strategy not in PROCEDURE_STRATEGIES:
            raise ValueError(f"strategy must be one of {PROCEDURE_STRATEGIES}")
        if int(self.inner_folds) < 2:
            raise ValueError("inner_folds must be >= 2")
        if self.max_predictors is not None and int(self.max_predictors) < 1:
            raise ValueError("max_predictors must be >= 1 or None")
        if float(self.vif_threshold) <= 1:
            raise ValueError("vif_threshold must be > 1")
        if float(self.predictive_min_gain) < 0:
            raise ValueError("predictive_min_gain must be >= 0")

    @property
    def label(self) -> str:
        return f"{self.strategy}|{self.model_spec.label}"


@dataclass(frozen=True)
class RecoveryProcedureBenchmark:
    fold_metrics: pd.DataFrame
    selection_trace: pd.DataFrame


def _unique_predictors(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(x) for x in values))


def _with_observation_terms(
    ecological: Sequence[str], observation: Sequence[str]
) -> tuple[str, ...]:
    return _unique_predictors((*ecological, *observation))


def _predictive_forward_select(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    ecological_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    procedure: RecoveryProcedure,
) -> tuple[tuple[str, ...], pd.DataFrame]:
    """Predictive baseline: select ecological terms by inner record ranking."""

    remaining = list(_unique_predictors(ecological_predictors))
    selected: list[str] = []
    observation = _unique_predictors(observation_predictors)
    if observation:
        try:
            current_score = cross_validated_score(
                presence,
                background,
                presence_groups,
                background_groups,
                observation,
                n_splits=procedure.inner_folds,
                model_spec=procedure.model_spec,
            )
        except ValueError:
            current_score = 0.5
    else:
        current_score = 0.5
    trace: list[dict[str, object]] = []
    step = 0
    while remaining and (
        procedure.max_predictors is None or len(selected) < procedure.max_predictors
    ):
        scores: list[tuple[float, str]] = []
        for predictor in remaining:
            model_predictors = _with_observation_terms(
                (*selected, predictor), observation
            )
            try:
                score = cross_validated_score(
                    presence,
                    background,
                    presence_groups,
                    background_groups,
                    model_predictors,
                    n_splits=procedure.inner_folds,
                    model_spec=procedure.model_spec,
                )
            except ValueError:
                continue
            if np.isfinite(score):
                scores.append((float(score), predictor))
        if not scores:
            break
        scores.sort(key=lambda item: (-item[0], item[1]))
        best_score, best_predictor = scores[0]
        gain = best_score - current_score
        accepted = gain >= procedure.predictive_min_gain - 1e-12
        trace.append(
            {
                "step": step,
                "chosen_predictor": best_predictor,
                "inner_presence_rank": best_score,
                "gain": gain,
                "accepted": bool(accepted),
            }
        )
        if not accepted:
            break
        selected.append(best_predictor)
        remaining.remove(best_predictor)
        current_score = best_score
        step += 1

    # Keep the predictive baseline evaluable even if an optional positive-gain
    # guardrail rejects the first step. This is a deterministic baseline fallback,
    # not an ecological promotion rule.
    if not selected and remaining:
        scores = []
        for predictor in remaining:
            model_predictors = _with_observation_terms((predictor,), observation)
            try:
                score = cross_validated_score(
                    presence,
                    background,
                    presence_groups,
                    background_groups,
                    model_predictors,
                    n_splits=procedure.inner_folds,
                    model_spec=procedure.model_spec,
                )
            except ValueError:
                continue
            if np.isfinite(score):
                scores.append((float(score), predictor))
        if scores:
            scores.sort(key=lambda item: (-item[0], item[1]))
            selected.append(scores[0][1])
    return _with_observation_terms(selected, observation), pd.DataFrame(trace)


def _inner_recovery_candidates(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    subsets: dict[str, tuple[str, ...]],
    audit_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    procedure: RecoveryProcedure,
    *,
    observation_correction_active: bool,
    observation_weight_truncation_quantile: float,
    chance_auc: float,
    minimum_auc_margin: float,
    auc_sem_multiplier: float,
) -> tuple[GeneralizationGatedNicheRecoverySelection, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    observation = _unique_predictors(observation_predictors)
    for label, ecological_subset in subsets.items():
        model_predictors = _with_observation_terms(ecological_subset, observation)
        frame = cross_validated_observation_corrected_niche_recovery(
            presence,
            background,
            presence_groups,
            background_groups,
            model_predictors,
            audit_predictors,
            candidate_observation_predictors=observation,
            audit_observation_predictors=observation,
            observation_correction_active=observation_correction_active,
            n_splits=procedure.inner_folds,
            model_spec=procedure.model_spec,
            observation_weight_truncation_quantile=(
                observation_weight_truncation_quantile
            ),
        )
        if frame.empty:
            continue
        frame = frame.copy()
        frame["candidate"] = str(label)
        frame["n_predictors"] = len(model_predictors)
        frames.append(frame)
    if not frames:
        raise ValueError("inner niche-forward search produced no evaluable subset")
    metrics = pd.concat(frames, ignore_index=True)
    selection = select_generalization_gated_niche_recovery_protocol(
        metrics,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
    )
    return selection, metrics


def _niche_forward_select(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    ecological_predictors: Sequence[str],
    audit_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    procedure: RecoveryProcedure,
    *,
    observation_correction_active: bool,
    observation_weight_truncation_quantile: float,
    chance_auc: float,
    minimum_auc_margin: float,
    auc_sem_multiplier: float,
) -> tuple[tuple[str, ...], pd.DataFrame]:
    """Forward search driven by ecological recovery, not prediction gain."""

    remaining = list(_unique_predictors(ecological_predictors))
    selected: list[str] = []
    trace_rows: list[dict[str, object]] = []
    step = 0
    while remaining and (
        procedure.max_predictors is None or len(selected) < procedure.max_predictors
    ):
        subsets = {
            predictor: tuple((*selected, predictor)) for predictor in remaining
        }
        if selected:
            subsets["__current__"] = tuple(selected)
        selection, metrics = _inner_recovery_candidates(
            presence,
            background,
            presence_groups,
            background_groups,
            subsets,
            audit_predictors,
            observation_predictors,
            procedure,
            observation_correction_active=observation_correction_active,
            observation_weight_truncation_quantile=(
                observation_weight_truncation_quantile
            ),
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
        )
        winner = selection.candidate
        # GeneralizationGatedNicheRecoverySelection intentionally wraps the
        # ecological Pareto result. Trace the actual ecological frontier rather
        # than pretending the prediction gate itself has a Pareto front.
        pareto_front = selection.recovery_selection.pareto_front
        trace_rows.append(
            {
                "step": step,
                "winner": winner,
                "selected_before": ",".join(selected),
                "pareto_front": ",".join(pareto_front),
                "n_inner_candidates": int(metrics["candidate"].nunique()),
            }
        )
        if winner == "__current__":
            break
        selected.append(winner)
        remaining.remove(winner)
        step += 1
    if not selected:
        raise ValueError("niche-forward procedure selected no ecological predictor")
    return _with_observation_terms(selected, observation_predictors), pd.DataFrame(
        trace_rows
    )


def _select_fold_predictors(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    ecological_predictors: Sequence[str],
    audit_predictors: Sequence[str],
    procedure: RecoveryProcedure,
    *,
    observation_correction_active: bool,
    observation_weight_truncation_quantile: float,
    chance_auc: float,
    minimum_auc_margin: float,
    auc_sem_multiplier: float,
) -> tuple[tuple[str, ...], pd.DataFrame]:
    ecological = _unique_predictors(ecological_predictors)
    observation = _unique_predictors(procedure.observation_predictors)
    overlap = sorted(set(ecological) & set(observation))
    if overlap:
        raise ValueError(
            f"observation predictors must not be ecological selection candidates: {overlap}"
        )
    if procedure.strategy == "all":
        return _with_observation_terms(ecological, observation), pd.DataFrame()
    if procedure.strategy == "vif":
        selected, _ = vif_prune_predictors(
            background,
            ecological,
            threshold=procedure.vif_threshold,
        )
        if not selected:
            raise ValueError("VIF procedure removed every ecological predictor")
        return _with_observation_terms(selected, observation), pd.DataFrame()
    if procedure.strategy == "predictive_forward":
        return _predictive_forward_select(
            presence,
            background,
            presence_groups,
            background_groups,
            ecological,
            observation,
            procedure,
        )
    return _niche_forward_select(
        presence,
        background,
        presence_groups,
        background_groups,
        ecological,
        audit_predictors,
        observation,
        procedure,
        observation_correction_active=observation_correction_active,
        observation_weight_truncation_quantile=(
            observation_weight_truncation_quantile
        ),
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
    )


def cross_validated_recovery_procedure(
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
) -> RecoveryProcedureBenchmark:
    """Evaluate one procedure with nested spatial information barriers."""

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("spatial group arrays must align with model-pool rows")
    folds = min(int(outer_folds), len(np.unique(p_groups)))
    if folds < 2:
        raise ValueError("at least two outer spatial blocks are required")
    observation = _unique_predictors(procedure.observation_predictors)
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    rows: list[dict[str, object]] = []
    traces: list[pd.DataFrame] = []

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
        ecological_selected = [p for p in selected if p not in set(observation)]
        rows.append(
            {
                "fold": int(outer_fold),
                "candidate": procedure.label,
                "procedure": procedure.label,
                "strategy": procedure.strategy,
                "model": procedure.model_spec.label,
                "selected_predictors": ",".join(selected),
                "selected_ecological_predictors": ",".join(ecological_selected),
                "n_predictors": len(selected),
                "n_ecological_predictors": len(ecological_selected),
                "presence_rank": presence_rank_score(test_p_scores, test_b_scores),
                "continuous_boyce": continuous_boyce_index(
                    test_p_scores, test_b_scores
                ),
                "or10": or10(train_p_scores, test_p_scores),
                "observation_correction_active": bool(
                    observation_correction_active
                ),
                "observation_weight_ess": weights.effective_sample_size,
                "n_model_presence": len(p_train),
                "n_heldout_presence": len(p_test),
                "n_model_background": len(b_train),
                "n_heldout_background": len(b_test),
                **profile.as_dict(),
            }
        )
        if not trace.empty:
            trace = trace.copy()
            trace["outer_fold"] = int(outer_fold)
            trace["procedure"] = procedure.label
            traces.append(trace)

    return RecoveryProcedureBenchmark(
        fold_metrics=pd.DataFrame(rows),
        selection_trace=(
            pd.concat(traces, ignore_index=True) if traces else pd.DataFrame()
        ),
    )


def benchmark_recovery_procedures(
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
) -> RecoveryProcedureBenchmark:
    """Evaluate predeclared procedures on identical outer spatial folds."""

    procedures = tuple(procedures)
    if not procedures:
        raise ValueError("at least one recovery procedure is required")
    labels = [procedure.label for procedure in procedures]
    if len(set(labels)) != len(labels):
        raise ValueError("recovery procedure labels must be unique")
    metric_frames: list[pd.DataFrame] = []
    trace_frames: list[pd.DataFrame] = []
    for procedure in procedures:
        result = cross_validated_recovery_procedure(
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


def select_recovery_procedure(
    benchmark: RecoveryProcedureBenchmark,
    *,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
) -> GeneralizationGatedNicheRecoverySelection:
    """Select among procedures by ecological recovery after adequacy gating."""

    return select_generalization_gated_niche_recovery_protocol(
        benchmark.fold_metrics,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
        max_mean_or10=max_mean_or10,
    )
