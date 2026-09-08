"""v9 conditional-residual-randomization matched-route process challenge.

For target process P, fit P=m(Q)+r using background environments, where Q is the
union of all other declared process closures.  Replace row-specific residuals by
a deterministic permutation of the background residual bank while retaining
m(Q), target conditional variance, multivariate residual covariance, and every
non-P predictor.  The scientific evidence state space and thresholds are inherited
unchanged from v5.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import hashlib

import numpy as np
import pandas as pd

from .conditional_residual_randomization import (
    fit_conditional_residual_randomizer,
    verify_non_target_predictors_unchanged,
)
from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .interval_evidence_process_challenge import (
    INCOMPLETE_EVIDENCE,
    INDETERMINATE_EVIDENCE,
    INFERIOR_EVIDENCE,
    NONINFERIOR_EVIDENCE,
    IntervalEvidenceProcessChallengeFit,
    _classify_processes as _classify_interval_processes,
    fit_interval_evidence_process_challenge,
    interval_evidence_state,
)
from .model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability, score_relative_suitability
from .observation_aware_identification import _fold_indices, _prepare_observation_corrections, _summary, _weighted_presence_rank
from .process_information_closure import process_information_closure, summarize_process_information_closures
from .proxy_closed_route_process_challenge import _paired_delta, _presence_rank
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


@dataclass(frozen=True)
class ConditionalResidualRandomizationProcessChallengeFit:
    v5_fit: IntervalEvidenceProcessChallengeFit
    randomized_fold_evidence: pd.DataFrame
    randomized_route_summary: pd.DataFrame
    process_summary: pd.DataFrame
    closure_summary: pd.DataFrame
    intervention_audit: pd.DataFrame
    selection_receipt: str

    @property
    def prediction_model_label(self) -> str:
        return self.v5_fit.prediction_model_label

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v5_fit.predict_relative_suitability(frame)

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v5_fit.predict_ecological_suitability(frame)


def _randomized_route_cv(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: tuple[str, ...],
    conditioning_predictors: tuple[str, ...],
    ecological_predictors: tuple[str, ...],
    observation_predictors: tuple[str, ...],
    model_spec: ModelSpec,
    folds,
    corrections,
    degree: int,
    ridge_alpha: float,
    random_state: int,
    density_probability_epsilon: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    route = f"conditional_residual_randomization::{model_spec.label}::{process}"
    rows: list[dict[str, object]] = []
    audits: list[dict[str, object]] = []
    for fold, ((p_train_idx, b_train_idx, p_test_idx, b_test_idx), correction) in enumerate(zip(folds, corrections, strict=True)):
        row = {
            "route": route,
            "route_type": "conditional_residual_randomization",
            "excluded_process": str(process),
            "model_label": model_spec.label,
            "fold": int(fold),
            "complete": False,
            "presence_rank": float("nan"),
            "ecological_presence_rank": float("nan"),
            "balanced_density_log_score": float("nan"),
            "ecological_density_log_score": float("nan"),
        }
        audit = {
            "process": str(process),
            "model_label": model_spec.label,
            "fold": int(fold),
            "complete": False,
            "non_target_predictors_unchanged": False,
            "randomizer_fit_background_rows": 0,
            "residual_bank_rows": 0,
        }
        try:
            if not correction.complete:
                raise ValueError("candidate-independent observation correction unavailable")
            if min(len(p_train_idx), len(b_train_idx), len(p_test_idx), len(b_test_idx)) < 2:
                raise ValueError("fold lacks sufficient rows")
            p_train = presence.iloc[p_train_idx].reset_index(drop=True)
            b_train = background.iloc[b_train_idx].reset_index(drop=True)
            p_test = presence.iloc[p_test_idx].reset_index(drop=True)
            b_test = background.iloc[b_test_idx].reset_index(drop=True)
            randomizer = fit_conditional_residual_randomizer(
                b_train,
                process=str(process),
                process_predictors=process_predictors,
                conditioning_predictors=conditioning_predictors,
                degree=int(degree),
                ridge_alpha=float(ridge_alpha),
                random_state=int(random_state) + int(fold),
                minimum_complete_rows=5,
            )
            p_train_k = randomizer.transform(p_train)
            b_train_k = randomizer.transform(b_train)
            p_test_k = randomizer.transform(p_test)
            b_test_k = randomizer.transform(b_test)
            unchanged = all(
                verify_non_target_predictors_unchanged(before, after, target_predictors=process_predictors)
                for before, after in ((p_train, p_train_k), (b_train, b_train_k), (p_test, p_test_k), (b_test, b_test_k))
            )
            if not unchanged:
                raise ValueError("randomization altered a non-target predictor")
            model_predictors = ecological_predictors + observation_predictors
            model = fit_relative_suitability_model(p_train_k, b_train_k, model_predictors, model_spec=model_spec)
            p_full = score_relative_suitability(model, p_test_k, model_predictors)
            b_full = score_relative_suitability(model, b_test_k, model_predictors)
            p_eco = score_ecological_suitability(
                model,
                p_test_k,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_k,
            )
            b_eco = score_ecological_suitability(
                model,
                b_test_k,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_k,
            )
            values = (
                _presence_rank(p_full, b_full),
                _weighted_presence_rank(p_eco, b_eco, correction.weights),
                balanced_density_ratio_log_score(p_full, b_full, probability_epsilon=float(density_probability_epsilon)),
                balanced_density_ratio_log_score(
                    p_eco,
                    b_eco,
                    presence_weights=correction.weights,
                    probability_epsilon=float(density_probability_epsilon),
                ),
            )
            if not all(np.isfinite(float(x)) for x in values):
                raise ValueError("randomized route produced non-finite evidence")
            row.update(
                {
                    "complete": True,
                    "presence_rank": float(values[0]),
                    "ecological_presence_rank": float(values[1]),
                    "balanced_density_log_score": float(values[2]),
                    "ecological_density_log_score": float(values[3]),
                }
            )
            audit.update(
                {
                    "complete": True,
                    "non_target_predictors_unchanged": True,
                    "randomizer_fit_background_rows": int(randomizer.n_fit_rows),
                    "residual_bank_rows": int(len(randomizer.residual_bank)),
                }
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
        audits.append(audit)
    return pd.DataFrame(rows), pd.DataFrame(audits)


def fit_conditional_residual_randomization_process_challenge(
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
    relative_noninferiority_margin: float = 0.02,
    relative_sem_multiplier: float = 1.0,
    density_noninferiority_margin: float = 0.01,
    density_sem_multiplier: float = 1.0,
    density_probability_epsilon: float = 1e-6,
    randomization_degree: int = 2,
    randomization_ridge_alpha: float = 1.0,
    randomization_seed: int = 90401,
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> ConditionalResidualRandomizationProcessChallengeFit:
    ecological = tuple(str(x) for x in ecological_predictors)
    observation = tuple(str(x) for x in observation_predictors)
    processes = tuple(str(x) for x in process_universe)
    specs = tuple(model_specs)
    spec_by_label = {s.label: s for s in specs}
    if len(spec_by_label) != len(specs):
        raise ValueError("model_specs must have unique labels")

    v5 = fit_interval_evidence_process_challenge(
        presence,
        background,
        presence_groups,
        background_groups,
        ecological_predictors=ecological,
        observation_predictors=observation,
        process_registry=process_registry,
        process_universe=processes,
        model_specs=specs,
        n_splits=int(n_splits),
        chance_score=float(chance_score),
        minimum_margin=float(minimum_margin),
        sem_multiplier=float(sem_multiplier),
        relative_noninferiority_margin=float(relative_noninferiority_margin),
        relative_sem_multiplier=float(relative_sem_multiplier),
        density_noninferiority_margin=float(density_noninferiority_margin),
        density_sem_multiplier=float(density_sem_multiplier),
        density_probability_epsilon=float(density_probability_epsilon),
        observation_signal_chance=float(observation_signal_chance),
        observation_signal_margin=float(observation_signal_margin),
        observation_signal_sem_multiplier=float(observation_signal_sem_multiplier),
        observation_weight_truncation_quantile=float(observation_weight_truncation_quantile),
        observation_weight_probability_epsilon=float(observation_weight_probability_epsilon),
        occurrence_split=occurrence_split,
        occurrence_id_col=occurrence_id_col,
    )
    expected_labels = tuple(sorted(set(v5.v4_fit.v3_fit.route_summary["model_label"].astype(str))))
    folds = _fold_indices(len(presence), len(background), np.asarray(presence_groups), np.asarray(background_groups), n_splits=int(n_splits))
    corrections = _prepare_observation_corrections(
        presence,
        background,
        np.asarray(presence_groups),
        np.asarray(background_groups),
        observation,
        folds,
        observation_signal_chance=float(observation_signal_chance),
        observation_signal_margin=float(observation_signal_margin),
        observation_signal_sem_multiplier=float(observation_signal_sem_multiplier),
        observation_weight_truncation_quantile=float(observation_weight_truncation_quantile),
        observation_weight_probability_epsilon=float(observation_weight_probability_epsilon),
    )
    closures = {p: tuple(process_information_closure(process_registry, p)) for p in processes}
    closure_summary = summarize_process_information_closures(process_registry, process_universe=processes)
    rank_baseline = v5.v4_fit.v3_fit.base_fit.fold_evidence
    density_baseline = v5.v4_fit.density_fold_evidence
    fold_parts: list[pd.DataFrame] = []
    audit_parts: list[pd.DataFrame] = []
    route_rows: list[dict[str, object]] = []

    for process_index, process in enumerate(processes):
        closure = closures[process]
        other_closures = [closures[q] for q in processes if q != process]
        structural_overlap = sorted(set(closure) & set(x for cols in other_closures for x in cols))
        conditioning = tuple(dict.fromkeys(x for cols in other_closures for x in cols if x not in set(closure)))
        for model_label in expected_labels:
            spec = spec_by_label[model_label]
            if structural_overlap or not conditioning:
                fold_frame = pd.DataFrame([
                    {
                        "route": f"conditional_residual_randomization::{model_label}::{process}",
                        "route_type": "conditional_residual_randomization",
                        "excluded_process": process,
                        "model_label": model_label,
                        "fold": i,
                        "complete": False,
                        "presence_rank": np.nan,
                        "ecological_presence_rank": np.nan,
                        "balanced_density_log_score": np.nan,
                        "ecological_density_log_score": np.nan,
                    }
                    for i in range(int(n_splits))
                ])
                audit = pd.DataFrame([
                    {"process": process, "model_label": model_label, "fold": i, "complete": False, "non_target_predictors_unchanged": False, "randomizer_fit_background_rows": 0, "residual_bank_rows": 0}
                    for i in range(int(n_splits))
                ])
            else:
                fold_frame, audit = _randomized_route_cv(
                    presence,
                    background,
                    process=process,
                    process_predictors=closure,
                    conditioning_predictors=conditioning,
                    ecological_predictors=ecological,
                    observation_predictors=observation,
                    model_spec=spec,
                    folds=folds,
                    corrections=corrections,
                    degree=int(randomization_degree),
                    ridge_alpha=float(randomization_ridge_alpha),
                    random_state=int(randomization_seed) + 1000 * int(process_index),
                    density_probability_epsilon=float(density_probability_epsilon),
                )
            fold_parts.append(fold_frame)
            audit_parts.append(audit)
            prediction = _summary(fold_frame, "presence_rank", chance_score=float(chance_score), minimum_margin=float(minimum_margin), sem_multiplier=float(sem_multiplier))
            ecology = _summary(fold_frame, "ecological_presence_rank", chance_score=float(chance_score), minimum_margin=float(minimum_margin), sem_multiplier=float(sem_multiplier))
            pred_delta = _paired_delta(rank_baseline, fold_frame, model_label=model_label, baseline_metric="presence_rank", route_metric="presence_rank")
            eco_delta = _paired_delta(rank_baseline, fold_frame, model_label=model_label, baseline_metric="ecological_presence_rank", route_metric="ecological_presence_rank")
            den_delta = _paired_delta(density_baseline, fold_frame, model_label=model_label, baseline_metric="balanced_density_log_score", route_metric="balanced_density_log_score")
            eco_den_delta = _paired_delta(density_baseline, fold_frame, model_label=model_label, baseline_metric="ecological_density_log_score", route_metric="ecological_density_log_score")
            states = [
                interval_evidence_state(pred_delta["mean_delta"], pred_delta["sem_delta"], margin=float(relative_noninferiority_margin), sem_multiplier=float(relative_sem_multiplier), complete=bool(pred_delta["complete"])),
                interval_evidence_state(eco_delta["mean_delta"], eco_delta["sem_delta"], margin=float(relative_noninferiority_margin), sem_multiplier=float(relative_sem_multiplier), complete=bool(eco_delta["complete"])),
                interval_evidence_state(den_delta["mean_delta"], den_delta["sem_delta"], margin=float(density_noninferiority_margin), sem_multiplier=float(density_sem_multiplier), complete=bool(den_delta["complete"])),
                interval_evidence_state(eco_den_delta["mean_delta"], eco_den_delta["sem_delta"], margin=float(density_noninferiority_margin), sem_multiplier=float(density_sem_multiplier), complete=bool(eco_den_delta["complete"])),
            ]
            labels = tuple(str(x["state"]) for x in states)
            complete = bool(fold_frame["complete"].astype(bool).all())
            if not complete or INCOMPLETE_EVIDENCE in labels:
                relative_state = INCOMPLETE_EVIDENCE
            elif all(x == NONINFERIOR_EVIDENCE for x in labels):
                relative_state = NONINFERIOR_EVIDENCE
            elif any(x == INFERIOR_EVIDENCE for x in labels):
                relative_state = INFERIOR_EVIDENCE
            else:
                relative_state = INDETERMINATE_EVIDENCE
            route_rows.append(
                {
                    "process": process,
                    "excluded_process": process,
                    "model_label": model_label,
                    "route": f"conditional_residual_randomization::{model_label}::{process}",
                    "route_type": "conditional_residual_randomization",
                    "closure_predictors": ",".join(closure),
                    "conditioning_predictors": ",".join(conditioning),
                    "structural_overlap": bool(structural_overlap),
                    "complete": complete,
                    "route_adequate": bool(prediction["adequate"] and ecology["adequate"]),
                    "mean_presence_rank": prediction["mean"],
                    "mean_ecological_presence_rank": ecology["mean"],
                    "prediction_interval_state": states[0]["state"],
                    "prediction_delta_mean": pred_delta["mean_delta"],
                    "prediction_delta_sem": pred_delta["sem_delta"],
                    "ecological_rank_interval_state": states[1]["state"],
                    "ecological_rank_delta_mean": eco_delta["mean_delta"],
                    "ecological_rank_delta_sem": eco_delta["sem_delta"],
                    "density_interval_state": states[2]["state"],
                    "density_delta_mean": den_delta["mean_delta"],
                    "density_delta_sem": den_delta["sem_delta"],
                    "ecological_density_interval_state": states[3]["state"],
                    "ecological_density_delta_mean": eco_den_delta["mean_delta"],
                    "ecological_density_delta_sem": eco_den_delta["sem_delta"],
                    "relative_evidence_state": relative_state,
                    "n_folds": int(len(fold_frame)),
                }
            )

    routes = pd.DataFrame(route_rows)
    process_summary = _classify_interval_processes(routes, processes, expected_model_labels=expected_labels)
    v5_status = v5.process_summary.set_index("process")["status"].astype(str).to_dict()
    process_summary["v5_status"] = process_summary["process"].map(v5_status)
    process_summary["status_changed_from_v5"] = process_summary["status"].astype(str) != process_summary["v5_status"].astype(str)
    audit = pd.concat(audit_parts, ignore_index=True) if audit_parts else pd.DataFrame()
    folds_out = pd.concat(fold_parts, ignore_index=True) if fold_parts else pd.DataFrame()
    receipt_payload = "\n".join(
        [
            "v5_receipt=" + v5.selection_receipt,
            "intervention=conditional_residual_randomization_preserve_shared_mean_and_background_residual_distribution",
            f"randomization_degree={int(randomization_degree)}",
            f"randomization_ridge_alpha={float(randomization_ridge_alpha):.12g}",
            f"randomization_seed={int(randomization_seed)}",
            "non_target_predictors_must_be_numerically_unchanged",
            "process_status=" + process_summary[["process", "status"]].to_csv(index=False),
            "closures=" + closure_summary.to_csv(index=False),
        ]
    )
    return ConditionalResidualRandomizationProcessChallengeFit(
        v5_fit=v5,
        randomized_fold_evidence=folds_out,
        randomized_route_summary=routes,
        process_summary=process_summary,
        closure_summary=closure_summary,
        intervention_audit=audit,
        selection_receipt=hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest(),
    )
