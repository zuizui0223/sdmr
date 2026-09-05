"""Observation-aware prospective ecological-identification learner.

This module is the execution-time learner for the prospective validation contract.
It keeps ecological process predictors separate from declared observation-process
predictors. Observation predictors may absorb recording/detectability structure
in the fitted model, but they are marginalized from the ecological score and are
never members of an ecological process-information closure.

A process-knockout route counts as an adequate witness only when it preserves
both (1) ordinary held-out record prediction and (2) an observation-corrected
ecological ranking of held-out occurrences against background. The observation
correction gate and weights use training rows only and are computed once per
inner fold, independently of every ecological candidate/knockout route.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import presence_rank_score
from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .observation_process import (
    inverse_observation_propensity_weights,
    observation_process_signal_evidence,
)
from .process_information_closure import (
    freeze_process_information_knockout_registry,
    normalize_process_information_registry,
)
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


@dataclass(frozen=True)
class _ObservationCorrection:
    complete: bool
    active: bool
    signal_auc: float
    weights: np.ndarray
    effective_sample_size: float


@dataclass(frozen=True)
class ObservationAwareIdentificationFit:
    ecological_predictors: tuple[str, ...]
    observation_predictors: tuple[str, ...]
    process_universe: tuple[str, ...]
    fold_evidence: pd.DataFrame
    baseline_summary: pd.DataFrame
    knockout_summary: pd.DataFrame
    process_summary: pd.DataFrame
    admissible_model_labels: tuple[str, ...]
    fitted_models: tuple[tuple[str, object], ...]
    observation_reference: pd.DataFrame
    selection_receipt: str
    chance_score: float
    adequacy_floor: float
    sem_multiplier: float

    @property
    def model_predictors(self) -> tuple[str, ...]:
        return self.ecological_predictors + self.observation_predictors

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        if not self.fitted_models:
            raise RuntimeError("identification learner has no fitted admissible models")
        predictions = [
            score_relative_suitability(model, frame, self.model_predictors)
            for _, model in self.fitted_models
        ]
        with np.errstate(invalid="ignore"):
            return np.nanmean(np.vstack(predictions), axis=0)

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        if not self.fitted_models:
            raise RuntimeError("identification learner has no fitted admissible models")
        predictions = [
            score_ecological_suitability(
                model,
                frame,
                self.model_predictors,
                observation_predictors=self.observation_predictors,
                observation_reference=self.observation_reference,
            )
            for _, model in self.fitted_models
        ]
        with np.errstate(invalid="ignore"):
            return np.nanmean(np.vstack(predictions), axis=0)


def _unique(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(x).strip() for x in values)
    if not result or any(not x for x in result):
        raise ValueError(f"{name} must contain non-empty values")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _weighted_presence_rank(
    presence_scores: np.ndarray,
    background_scores: np.ndarray,
    weights: np.ndarray,
) -> float:
    p = np.asarray(presence_scores, dtype=float)
    b = np.asarray(background_scores, dtype=float)
    w = np.asarray(weights, dtype=float)
    if len(p) != len(w):
        raise ValueError("presence scores and observation weights must align")
    keep_p = np.isfinite(p) & np.isfinite(w) & (w > 0)
    keep_b = np.isfinite(b)
    p = p[keep_p]
    w = w[keep_p]
    b = b[keep_b]
    if not len(p) or not len(b) or not float(w.sum()) > 0:
        return float("nan")
    b_sorted = np.sort(b)
    lower = np.searchsorted(b_sorted, p, side="left")
    upper = np.searchsorted(b_sorted, p, side="right")
    ranks = (lower + 0.5 * (upper - lower)) / len(b_sorted)
    return float(np.average(ranks, weights=w))


def _summary(
    frame: pd.DataFrame,
    column: str,
    *,
    chance_score: float,
    minimum_margin: float,
    sem_multiplier: float,
) -> dict[str, object]:
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(float)
    complete_flags = frame["complete"].astype(bool).to_numpy()
    finite = values[np.isfinite(values)]
    complete = bool(len(frame) and complete_flags.all() and len(finite) == len(frame))
    mean = float(np.mean(finite)) if len(finite) else float("nan")
    sem = (
        float(np.std(finite, ddof=1) / np.sqrt(len(finite)))
        if len(finite) >= 2
        else (0.0 if len(finite) == 1 else float("nan"))
    )
    lower = mean - sem_multiplier * sem if np.isfinite(mean) and np.isfinite(sem) else float("nan")
    floor = chance_score + minimum_margin
    adequate = bool(
        complete
        and np.isfinite(mean)
        and np.isfinite(lower)
        and mean >= floor - 1e-12
        and lower >= chance_score - 1e-12
    )
    return {
        "complete": complete,
        "mean": mean,
        "sem": sem,
        "lower": lower,
        "adequate": adequate,
        "n_folds": int(len(frame)),
    }


def _fold_indices(
    n_presence: int,
    n_background: int,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    *,
    n_splits: int,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], ...]:
    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != n_presence or len(b_groups) != n_background:
        raise ValueError("group arrays must align with presence/background rows")
    groups = np.concatenate([p_groups, b_groups])
    if len(np.unique(groups)) < int(n_splits):
        raise ValueError("insufficient spatial groups for requested inner folds")
    all_idx = np.arange(n_presence + n_background)
    splitter = GroupKFold(n_splits=int(n_splits))
    folds = []
    for train_idx, test_idx in splitter.split(all_idx, groups=groups):
        folds.append(
            (
                train_idx[train_idx < n_presence],
                train_idx[train_idx >= n_presence] - n_presence,
                test_idx[test_idx < n_presence],
                test_idx[test_idx >= n_presence] - n_presence,
            )
        )
    return tuple(folds)


def _prepare_observation_corrections(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    observation_predictors: tuple[str, ...],
    folds: tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], ...],
    *,
    observation_signal_chance: float,
    observation_signal_margin: float,
    observation_signal_sem_multiplier: float,
    observation_weight_truncation_quantile: float,
    observation_weight_probability_epsilon: float,
) -> tuple[_ObservationCorrection, ...]:
    corrections: list[_ObservationCorrection] = []
    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    nuisance_spec = ModelSpec(C=1.0, degree=1, penalty="l2", random_state=0)
    for p_train_idx, b_train_idx, p_test_idx, _ in folds:
        if not observation_predictors:
            corrections.append(
                _ObservationCorrection(
                    complete=True,
                    active=False,
                    signal_auc=float(observation_signal_chance),
                    weights=np.ones(len(p_test_idx), dtype=float),
                    effective_sample_size=float(len(p_test_idx)),
                )
            )
            continue
        try:
            p_train = presence.iloc[p_train_idx].reset_index(drop=True)
            b_train = background.iloc[b_train_idx].reset_index(drop=True)
            p_test = presence.iloc[p_test_idx].reset_index(drop=True)
            train_group_count = len(np.unique(p_groups[p_train_idx]))
            if train_group_count < 2:
                raise ValueError("observation gate requires at least two training groups")
            signal = observation_process_signal_evidence(
                p_train,
                b_train,
                p_groups[p_train_idx],
                b_groups[b_train_idx],
                observation_predictors,
                n_splits=min(3, train_group_count),
                chance_auc=observation_signal_chance,
                minimum_auc_margin=observation_signal_margin,
                auc_sem_multiplier=observation_signal_sem_multiplier,
                model_spec=nuisance_spec,
            )
            if signal.correction_active:
                weight_result = inverse_observation_propensity_weights(
                    p_train,
                    b_train,
                    p_test,
                    observation_predictors,
                    model_spec=nuisance_spec,
                    truncation_quantile=observation_weight_truncation_quantile,
                    probability_epsilon=observation_weight_probability_epsilon,
                )
                weights = weight_result.weights
                ess = float(weight_result.effective_sample_size)
            else:
                weights = np.ones(len(p_test), dtype=float)
                ess = float(len(p_test))
            corrections.append(
                _ObservationCorrection(
                    complete=True,
                    active=bool(signal.correction_active),
                    signal_auc=float(signal.mean_auc),
                    weights=weights,
                    effective_sample_size=ess,
                )
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            corrections.append(
                _ObservationCorrection(
                    complete=False,
                    active=False,
                    signal_auc=float("nan"),
                    weights=np.full(len(p_test_idx), np.nan, dtype=float),
                    effective_sample_size=float("nan"),
                )
            )
    return tuple(corrections)


def _route_cv(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    ecological_predictors: tuple[str, ...],
    observation_predictors: tuple[str, ...],
    model_spec: ModelSpec,
    folds: tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], ...],
    corrections: tuple[_ObservationCorrection, ...],
    *,
    route: str,
    route_type: str,
    excluded_process: str = "",
) -> pd.DataFrame:
    model_predictors = ecological_predictors + observation_predictors
    rows: list[dict[str, object]] = []
    for fold, ((p_train_idx, b_train_idx, p_test_idx, b_test_idx), correction) in enumerate(
        zip(folds, corrections, strict=True)
    ):
        row: dict[str, object] = {
            "route": route,
            "route_type": route_type,
            "excluded_process": excluded_process,
            "model_label": model_spec.label,
            "fold": int(fold),
            "complete": False,
            "presence_rank": float("nan"),
            "ecological_presence_rank": float("nan"),
            "observation_correction_active": bool(correction.active),
            "observation_signal_auc": float(correction.signal_auc),
            "observation_weight_ess": float(correction.effective_sample_size),
        }
        try:
            if not correction.complete:
                raise ValueError("candidate-independent observation correction unavailable")
            if min(len(p_train_idx), len(b_train_idx), len(p_test_idx), len(b_test_idx)) < 2:
                raise ValueError("fold lacks sufficient presence/background rows")
            p_train = presence.iloc[p_train_idx].reset_index(drop=True)
            b_train = background.iloc[b_train_idx].reset_index(drop=True)
            p_test = presence.iloc[p_test_idx].reset_index(drop=True)
            b_test = background.iloc[b_test_idx].reset_index(drop=True)
            model = fit_relative_suitability_model(
                p_train,
                b_train,
                model_predictors,
                model_spec=model_spec,
            )
            p_full = score_relative_suitability(model, p_test, model_predictors)
            b_full = score_relative_suitability(model, b_test, model_predictors)
            prediction_rank = presence_rank_score(p_full, b_full)
            p_ecological = score_ecological_suitability(
                model,
                p_test,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train,
            )
            b_ecological = score_ecological_suitability(
                model,
                b_test,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train,
            )
            ecological_rank = _weighted_presence_rank(
                p_ecological,
                b_ecological,
                correction.weights,
            )
            if not np.isfinite(prediction_rank) or not np.isfinite(ecological_rank):
                raise ValueError("route produced non-finite adequacy score")
            row.update(
                {
                    "complete": True,
                    "presence_rank": float(prediction_rank),
                    "ecological_presence_rank": float(ecological_rank),
                }
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
    return pd.DataFrame(rows)


def fit_observation_aware_identification(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    *,
    ecological_predictors: Sequence[str],
    observation_predictors: Sequence[str] = (),
    process_registry: pd.DataFrame,
    process_universe: Sequence[str],
    model_specs: Sequence[ModelSpec],
    n_splits: int = 4,
    chance_score: float = 0.50,
    minimum_margin: float = 0.01,
    sem_multiplier: float = 1.0,
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> ObservationAwareIdentificationFit:
    ecological = _unique(ecological_predictors, name="ecological_predictors")
    observation = tuple(str(x).strip() for x in observation_predictors)
    if any(not x for x in observation) or len(set(observation)) != len(observation):
        raise ValueError("observation_predictors must be unique non-empty values")
    overlap = sorted(set(ecological) & set(observation))
    if overlap:
        raise ValueError("ecological and observation predictors overlap: " + ", ".join(overlap))
    processes = _unique(process_universe, name="process_universe")
    specs = tuple(model_specs)
    if not specs or len({s.label for s in specs}) != len(specs):
        raise ValueError("model_specs must contain unique model identities")
    if occurrence_split is not None:
        occurrence_split.assert_model_pool_only(presence, id_col=occurrence_id_col)

    model_predictors = ecological + observation
    for predictor in model_predictors:
        if predictor not in presence.columns or predictor not in background.columns:
            raise KeyError(f"predictor absent from model-pool tables: {predictor}")
    registry = normalize_process_information_registry(
        process_registry,
        process_universe=processes,
        predictor_universe=ecological,
    )
    knockout_registry = freeze_process_information_knockout_registry(
        base_candidates=tuple(spec.label for spec in specs),
        ecological_predictors=ecological,
        process_registry=registry,
        process_universe=processes,
        observation_predictors=observation,
    )
    folds = _fold_indices(
        len(presence),
        len(background),
        np.asarray(presence_groups),
        np.asarray(background_groups),
        n_splits=n_splits,
    )
    corrections = _prepare_observation_corrections(
        presence,
        background,
        np.asarray(presence_groups),
        np.asarray(background_groups),
        observation,
        folds,
        observation_signal_chance=observation_signal_chance,
        observation_signal_margin=observation_signal_margin,
        observation_signal_sem_multiplier=observation_signal_sem_multiplier,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
        observation_weight_probability_epsilon=observation_weight_probability_epsilon,
    )

    evidence: list[pd.DataFrame] = []
    baseline_rows: list[dict[str, object]] = []
    for spec in specs:
        fold_frame = _route_cv(
            presence,
            background,
            ecological,
            observation,
            spec,
            folds,
            corrections,
            route=f"baseline::{spec.label}",
            route_type="baseline",
        )
        evidence.append(fold_frame)
        pred = _summary(
            fold_frame,
            "presence_rank",
            chance_score=chance_score,
            minimum_margin=minimum_margin,
            sem_multiplier=sem_multiplier,
        )
        eco = _summary(
            fold_frame,
            "ecological_presence_rank",
            chance_score=chance_score,
            minimum_margin=minimum_margin,
            sem_multiplier=sem_multiplier,
        )
        baseline_rows.append(
            {
                "model_label": spec.label,
                "complete": bool(pred["complete"] and eco["complete"]),
                "mean_presence_rank": pred["mean"],
                "prediction_adequate": pred["adequate"],
                "mean_ecological_presence_rank": eco["mean"],
                "ecological_adequate": eco["adequate"],
            }
        )
    baseline_summary = pd.DataFrame(baseline_rows).sort_values("model_label").reset_index(drop=True)
    admitted = tuple(
        baseline_summary.loc[
            baseline_summary["prediction_adequate"].astype(bool), "model_label"
        ].astype(str)
    )
    if not admitted:
        raise ValueError("no baseline learner passed the predictive adequacy gate")
    spec_by_label = {spec.label: spec for spec in specs}

    knockout_rows: list[dict[str, object]] = []
    for route_row in knockout_registry.itertuples(index=False):
        label = str(route_row.base_candidate)
        if label not in admitted:
            continue
        retained_ecological = tuple(
            x for x in str(route_row.retained_ecological_predictors).split(",") if x
        )
        fold_frame = _route_cv(
            presence,
            background,
            retained_ecological,
            observation,
            spec_by_label[label],
            folds,
            corrections,
            route=str(route_row.candidate),
            route_type="process_knockout",
            excluded_process=str(route_row.excluded_process),
        )
        evidence.append(fold_frame)
        pred = _summary(
            fold_frame,
            "presence_rank",
            chance_score=chance_score,
            minimum_margin=minimum_margin,
            sem_multiplier=sem_multiplier,
        )
        eco = _summary(
            fold_frame,
            "ecological_presence_rank",
            chance_score=chance_score,
            minimum_margin=minimum_margin,
            sem_multiplier=sem_multiplier,
        )
        route_adequate = bool(pred["adequate"] and eco["adequate"])
        knockout_rows.append(
            {
                "model_label": label,
                "route": str(route_row.candidate),
                "excluded_process": str(route_row.excluded_process),
                "retained_ecological_predictors": ",".join(retained_ecological),
                "complete": bool(pred["complete"] and eco["complete"]),
                "prediction_adequate": bool(pred["adequate"]),
                "ecological_adequate": bool(eco["adequate"]),
                "route_adequate": route_adequate,
                "mean_presence_rank": pred["mean"],
                "mean_ecological_presence_rank": eco["mean"],
            }
        )
    knockout_summary = pd.DataFrame(knockout_rows)

    process_rows: list[dict[str, object]] = []
    for process in processes:
        group = knockout_summary.loc[knockout_summary["excluded_process"].eq(process)]
        expected = len(admitted)
        complete_n = int(group["complete"].astype(bool).sum()) if len(group) else 0
        witnesses = group.loc[group["route_adequate"].astype(bool), "route"].astype(str).tolist()
        if witnesses:
            status = "refuted_as_necessary"
        elif len(group) == expected and complete_n == expected:
            status = "required_by_evidence_contract"
        else:
            status = "unresolved"
        process_rows.append(
            {
                "process": process,
                "status": status,
                "n_admitted_baseline_models": expected,
                "n_complete_knockout_routes": complete_n,
                "n_adequate_witness_routes": len(witnesses),
                "adequate_witness_routes": ",".join(sorted(witnesses)),
            }
        )
    process_summary = pd.DataFrame(process_rows)

    fitted: list[tuple[str, object]] = []
    for label in admitted:
        fitted.append(
            (
                label,
                fit_relative_suitability_model(
                    presence,
                    background,
                    model_predictors,
                    model_spec=spec_by_label[label],
                ),
            )
        )
    receipt_parts = [
        "ecological=" + ",".join(ecological),
        "observation=" + ",".join(observation),
        "process_registry=" + registry.to_csv(index=False),
        "admitted=" + ",".join(admitted),
        "process_status=" + process_summary[["process", "status"]].to_csv(index=False),
        f"chance={chance_score:.12g}",
        f"floor={chance_score + minimum_margin:.12g}",
        f"sem={sem_multiplier:.12g}",
        "observation_corrections="
        + ",".join(
            f"{int(c.complete)}:{int(c.active)}:{c.signal_auc:.12g}:{c.effective_sample_size:.12g}"
            for c in corrections
        ),
    ]
    if occurrence_split is not None:
        receipt_parts.append("outer_split=" + occurrence_split.split_digest)
    receipt = hashlib.sha256("\n".join(receipt_parts).encode("utf-8")).hexdigest()

    return ObservationAwareIdentificationFit(
        ecological_predictors=ecological,
        observation_predictors=observation,
        process_universe=processes,
        fold_evidence=pd.concat(evidence, ignore_index=True),
        baseline_summary=baseline_summary,
        knockout_summary=knockout_summary,
        process_summary=process_summary,
        admissible_model_labels=admitted,
        fitted_models=tuple(fitted),
        observation_reference=background[list(observation)].copy() if observation else pd.DataFrame(index=background.index),
        selection_receipt=receipt,
        chance_score=float(chance_score),
        adequacy_floor=float(chance_score + minimum_margin),
        sem_multiplier=float(sem_multiplier),
    )
