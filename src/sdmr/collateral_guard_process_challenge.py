"""v7 collateral-guard process challenge.

v6 established that erasing a target process's full environmental covariance can
increase true-process recall while also creating cross-process false attribution.
v7 changes the intervention, not the scientific decision thresholds:

* residualize retained predictors only against the target process component that
  is not explained by the other declared process closures; and
* audit, on background environments only, whether that intervention preserves
  the other declared process representations.

A target process is allowed to contribute route evidence only when every
collateral audit is positively classified as preserved. Structural overlap,
measured collateral loss, incomplete evidence, and indeterminate preservation all
force the target process routes to the existing indeterminate evidence state.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import hashlib

import numpy as np
import pandas as pd

from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .interval_evidence_process_challenge import (
    INCOMPLETE_EVIDENCE,
    INDETERMINATE_EVIDENCE,
    INFERIOR_EVIDENCE,
    NONINFERIOR_EVIDENCE,
    _classify_processes as _classify_interval_processes,
    interval_evidence_state,
)
from .model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability, score_relative_suitability
from .observation_aware_identification import _fold_indices, _prepare_observation_corrections, _summary, _weighted_presence_rank
from .process_information_closure import process_information_closure, summarize_process_information_closures
from .process_specific_information_purge import (
    COLLATERAL_PRESERVED,
    cross_validated_collateral_information_audit,
    fit_process_specific_information_purge,
)
from .proxy_closed_route_process_challenge import (
    ProxyClosedRouteProcessChallengeFit,
    _paired_delta,
    _presence_rank,
    fit_proxy_closed_route_process_challenge,
)
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


@dataclass(frozen=True)
class CollateralGuardProcessChallengeFit:
    v6_fit: ProxyClosedRouteProcessChallengeFit
    process_specific_fold_evidence: pd.DataFrame
    process_specific_route_summary: pd.DataFrame
    process_summary: pd.DataFrame
    specificity_audit: pd.DataFrame
    closure_summary: pd.DataFrame
    selection_receipt: str

    @property
    def prediction_model_label(self) -> str:
        return self.v6_fit.prediction_model_label

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v6_fit.predict_relative_suitability(frame)

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v6_fit.predict_ecological_suitability(frame)


def _specific_route_cv(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: tuple[str, ...],
    competing_predictors: tuple[str, ...],
    retained_ecological_predictors: tuple[str, ...],
    observation_predictors: tuple[str, ...],
    model_spec: ModelSpec,
    folds,
    corrections,
    purge_degree: int,
    purge_ridge_alpha: float,
    density_probability_epsilon: float,
) -> pd.DataFrame:
    route = f"specific_purged_knockout::{model_spec.label}::{process}"
    rows: list[dict[str, object]] = []
    for fold, ((p_train_idx, b_train_idx, p_test_idx, b_test_idx), correction) in enumerate(
        zip(folds, corrections, strict=True)
    ):
        row: dict[str, object] = {
            "route": route,
            "route_type": "process_specific_proxy_closed_knockout",
            "excluded_process": str(process),
            "model_label": model_spec.label,
            "fold": int(fold),
            "complete": False,
            "purge_complete": False,
            "presence_rank": float("nan"),
            "ecological_presence_rank": float("nan"),
            "balanced_density_log_score": float("nan"),
            "ecological_density_log_score": float("nan"),
        }
        try:
            if not retained_ecological_predictors:
                raise ValueError("process closure leaves no retained ecological predictor")
            if not correction.complete:
                raise ValueError("candidate-independent observation correction unavailable")
            if min(len(p_train_idx), len(b_train_idx), len(p_test_idx), len(b_test_idx)) < 2:
                raise ValueError("fold lacks sufficient presence/background rows")

            p_train = presence.iloc[p_train_idx].reset_index(drop=True)
            b_train = background.iloc[b_train_idx].reset_index(drop=True)
            p_test = presence.iloc[p_test_idx].reset_index(drop=True)
            b_test = background.iloc[b_test_idx].reset_index(drop=True)
            purge = fit_process_specific_information_purge(
                b_train,
                process=str(process),
                process_predictors=process_predictors,
                competing_predictors=competing_predictors,
                retained_predictors=retained_ecological_predictors,
                degree=int(purge_degree),
                ridge_alpha=float(purge_ridge_alpha),
                minimum_complete_rows=5,
            )
            p_train_after = purge.transform(p_train)
            b_train_after = purge.transform(b_train)
            p_test_after = purge.transform(p_test)
            b_test_after = purge.transform(b_test)
            model_predictors = retained_ecological_predictors + observation_predictors

            model = fit_relative_suitability_model(
                p_train_after,
                b_train_after,
                model_predictors,
                model_spec=model_spec,
            )
            p_full = score_relative_suitability(model, p_test_after, model_predictors)
            b_full = score_relative_suitability(model, b_test_after, model_predictors)
            prediction_rank = _presence_rank(p_full, b_full)
            p_eco = score_ecological_suitability(
                model,
                p_test_after,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_after,
            )
            b_eco = score_ecological_suitability(
                model,
                b_test_after,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_after,
            )
            ecological_rank = _weighted_presence_rank(p_eco, b_eco, correction.weights)
            full_density = balanced_density_ratio_log_score(
                p_full,
                b_full,
                probability_epsilon=float(density_probability_epsilon),
            )
            eco_density = balanced_density_ratio_log_score(
                p_eco,
                b_eco,
                presence_weights=correction.weights,
                probability_epsilon=float(density_probability_epsilon),
            )
            values = (prediction_rank, ecological_rank, full_density, eco_density)
            if not all(np.isfinite(float(x)) for x in values):
                raise ValueError("process-specific purged route produced non-finite evidence")
            row.update(
                {
                    "complete": True,
                    "purge_complete": True,
                    "presence_rank": float(prediction_rank),
                    "ecological_presence_rank": float(ecological_rank),
                    "balanced_density_log_score": float(full_density),
                    "ecological_density_log_score": float(eco_density),
                    "purge_fit_background_rows": int(purge.n_fit_rows),
                }
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
    return pd.DataFrame(rows)


def fit_collateral_guard_process_challenge(
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
    purge_degree: int = 2,
    purge_ridge_alpha: float = 1.0,
    collateral_sem_multiplier: float = 1.0,
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> CollateralGuardProcessChallengeFit:
    """Fit v7 using the v6 scientific thresholds plus a truth-blind specificity guard."""

    ecological = tuple(str(x) for x in ecological_predictors)
    observation = tuple(str(x) for x in observation_predictors)
    processes = tuple(str(x) for x in process_universe)
    specs = tuple(model_specs)
    spec_by_label = {spec.label: spec for spec in specs}
    if len(spec_by_label) != len(specs):
        raise ValueError("model_specs must have unique labels")

    v6 = fit_proxy_closed_route_process_challenge(
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
        purge_degree=int(purge_degree),
        purge_ridge_alpha=float(purge_ridge_alpha),
        observation_signal_chance=float(observation_signal_chance),
        observation_signal_margin=float(observation_signal_margin),
        observation_signal_sem_multiplier=float(observation_signal_sem_multiplier),
        observation_weight_truncation_quantile=float(observation_weight_truncation_quantile),
        observation_weight_probability_epsilon=float(observation_weight_probability_epsilon),
        occurrence_split=occurrence_split,
        occurrence_id_col=occurrence_id_col,
    )
    expected_labels = tuple(sorted(set(v6.v5_fit.v4_fit.v3_fit.route_summary["model_label"].astype(str))))
    unknown = sorted(set(expected_labels) - set(spec_by_label))
    if unknown:
        raise ValueError("v5 baseline uses model specs not supplied to v7: " + ", ".join(unknown))

    folds = _fold_indices(
        len(presence),
        len(background),
        np.asarray(presence_groups),
        np.asarray(background_groups),
        n_splits=int(n_splits),
    )
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
    closure_summary = summarize_process_information_closures(process_registry, process_universe=processes)
    closures = {p: tuple(process_information_closure(process_registry, p)) for p in processes}
    rank_baseline = v6.v5_fit.v4_fit.v3_fit.base_fit.fold_evidence
    density_baseline = v6.v5_fit.v4_fit.density_fold_evidence

    audits: list[pd.DataFrame] = []
    fold_frames: list[pd.DataFrame] = []
    route_rows: list[dict[str, object]] = []
    process_guard: dict[str, bool] = {}

    for process in processes:
        closure = closures[process]
        retained = tuple(p for p in ecological if p not in set(closure))
        competing_map = {q: closures[q] for q in processes if q != process}
        competing_union = tuple(
            dict.fromkeys(
                predictor
                for q, cols in competing_map.items()
                for predictor in cols
                if predictor not in set(closure)
            )
        )
        try:
            audit = cross_validated_collateral_information_audit(
                background,
                process=process,
                process_predictors=closure,
                competing_process_predictors=competing_map,
                retained_predictors=retained,
                groups=np.asarray(background_groups),
                n_splits=min(int(n_splits), len(np.unique(background_groups))),
                degree=int(purge_degree),
                ridge_alpha=float(purge_ridge_alpha),
                sem_multiplier=float(collateral_sem_multiplier),
            )
            audit["diagnostic_complete"] = True
        except (ValueError, KeyError, np.linalg.LinAlgError):
            audit = pd.DataFrame(
                [
                    {
                        "target_process": process,
                        "audited_process": "",
                        "audited_predictor": "",
                        "audit_role": "collateral_preservation",
                        "complete": False,
                        "structural_overlap": False,
                        "mean_pre_r2": np.nan,
                        "mean_post_r2": np.nan,
                        "mean_r2_loss": np.nan,
                        "sem_r2_loss": np.nan,
                        "mean_pre_rank_correlation": np.nan,
                        "mean_post_rank_correlation": np.nan,
                        "collateral_state": "collateral_incomplete",
                        "n_folds": 0,
                        "diagnostic_complete": False,
                    }
                ]
            )
        audits.append(audit)
        collateral = audit.loc[audit["audit_role"].astype(str).eq("collateral_preservation")]
        guard_pass = bool(
            len(collateral)
            and collateral["complete"].astype(bool).all()
            and collateral["collateral_state"].astype(str).eq(COLLATERAL_PRESERVED).all()
        )
        process_guard[process] = guard_pass

        for model_label in expected_labels:
            spec = spec_by_label[model_label]
            fold_frame = _specific_route_cv(
                presence,
                background,
                process=process,
                process_predictors=closure,
                competing_predictors=competing_union,
                retained_ecological_predictors=retained,
                observation_predictors=observation,
                model_spec=spec,
                folds=folds,
                corrections=corrections,
                purge_degree=int(purge_degree),
                purge_ridge_alpha=float(purge_ridge_alpha),
                density_probability_epsilon=float(density_probability_epsilon),
            )
            fold_frames.append(fold_frame)
            prediction = _summary(fold_frame, "presence_rank", chance_score=float(chance_score), minimum_margin=float(minimum_margin), sem_multiplier=float(sem_multiplier))
            ecology = _summary(fold_frame, "ecological_presence_rank", chance_score=float(chance_score), minimum_margin=float(minimum_margin), sem_multiplier=float(sem_multiplier))
            route_adequate = bool(prediction["adequate"] and ecology["adequate"])

            pred_delta = _paired_delta(rank_baseline, fold_frame, model_label=model_label, baseline_metric="presence_rank", route_metric="presence_rank")
            eco_delta = _paired_delta(rank_baseline, fold_frame, model_label=model_label, baseline_metric="ecological_presence_rank", route_metric="ecological_presence_rank")
            density_delta = _paired_delta(density_baseline, fold_frame, model_label=model_label, baseline_metric="balanced_density_log_score", route_metric="balanced_density_log_score")
            eco_density_delta = _paired_delta(density_baseline, fold_frame, model_label=model_label, baseline_metric="ecological_density_log_score", route_metric="ecological_density_log_score")
            pred_state = interval_evidence_state(pred_delta["mean_delta"], pred_delta["sem_delta"], margin=float(relative_noninferiority_margin), sem_multiplier=float(relative_sem_multiplier), complete=bool(pred_delta["complete"]))
            eco_state = interval_evidence_state(eco_delta["mean_delta"], eco_delta["sem_delta"], margin=float(relative_noninferiority_margin), sem_multiplier=float(relative_sem_multiplier), complete=bool(eco_delta["complete"]))
            density_state = interval_evidence_state(density_delta["mean_delta"], density_delta["sem_delta"], margin=float(density_noninferiority_margin), sem_multiplier=float(density_sem_multiplier), complete=bool(density_delta["complete"]))
            eco_density_state = interval_evidence_state(eco_density_delta["mean_delta"], eco_density_delta["sem_delta"], margin=float(density_noninferiority_margin), sem_multiplier=float(density_sem_multiplier), complete=bool(eco_density_delta["complete"]))
            states = tuple(str(x["state"]) for x in (pred_state, eco_state, density_state, eco_density_state))
            complete = bool(fold_frame["complete"].astype(bool).all())
            if not complete or INCOMPLETE_EVIDENCE in states:
                raw_state = INCOMPLETE_EVIDENCE
            elif all(state == NONINFERIOR_EVIDENCE for state in states):
                raw_state = NONINFERIOR_EVIDENCE
            elif any(state == INFERIOR_EVIDENCE for state in states):
                raw_state = INFERIOR_EVIDENCE
            else:
                raw_state = INDETERMINATE_EVIDENCE
            guarded_state = raw_state if guard_pass else INDETERMINATE_EVIDENCE
            route_rows.append(
                {
                    "process": process,
                    "excluded_process": process,
                    "model_label": model_label,
                    "route": f"specific_purged_knockout::{model_label}::{process}",
                    "route_type": "process_specific_proxy_closed_knockout",
                    "closure_predictors": ",".join(closure),
                    "competing_process_predictors": ",".join(competing_union),
                    "retained_ecological_predictors": ",".join(retained),
                    "complete": complete,
                    "route_adequate": route_adequate,
                    "collateral_guard_pass": guard_pass,
                    "mean_presence_rank": prediction["mean"],
                    "mean_ecological_presence_rank": ecology["mean"],
                    "prediction_interval_state": pred_state["state"],
                    "prediction_delta_mean": pred_delta["mean_delta"],
                    "prediction_delta_sem": pred_delta["sem_delta"],
                    "ecological_rank_interval_state": eco_state["state"],
                    "ecological_rank_delta_mean": eco_delta["mean_delta"],
                    "ecological_rank_delta_sem": eco_delta["sem_delta"],
                    "density_interval_state": density_state["state"],
                    "density_delta_mean": density_delta["mean_delta"],
                    "density_delta_sem": density_delta["sem_delta"],
                    "ecological_density_interval_state": eco_density_state["state"],
                    "ecological_density_delta_mean": eco_density_delta["mean_delta"],
                    "ecological_density_delta_sem": eco_density_delta["sem_delta"],
                    "raw_relative_evidence_state": raw_state,
                    "relative_evidence_state": guarded_state,
                    "n_folds": int(len(fold_frame)),
                }
            )

    route_summary = pd.DataFrame(route_rows)
    raw_routes = route_summary.copy()
    raw_routes["relative_evidence_state"] = raw_routes["raw_relative_evidence_state"]
    raw_summary = _classify_interval_processes(raw_routes, processes, expected_model_labels=expected_labels)
    guarded_summary = _classify_interval_processes(route_summary, processes, expected_model_labels=expected_labels)
    raw_status = raw_summary.set_index("process")["status"].astype(str).to_dict()
    v6_status = v6.process_summary.set_index("process")["status"].astype(str).to_dict()
    guarded_summary["process_specific_unguarded_status"] = guarded_summary["process"].map(raw_status)
    guarded_summary["v6_status"] = guarded_summary["process"].map(v6_status)
    guarded_summary["collateral_guard_pass"] = guarded_summary["process"].map(process_guard).astype(bool)
    guarded_summary["status_changed_from_v6"] = guarded_summary["status"].astype(str) != guarded_summary["v6_status"].astype(str)

    specificity = pd.concat(audits, ignore_index=True) if audits else pd.DataFrame()
    fold_evidence = pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame()
    receipt_payload = "\n".join(
        [
            "v6_receipt=" + v6.selection_receipt,
            "purge_strategy=target_unique_component_given_other_declared_process_closures",
            f"collateral_sem_multiplier={float(collateral_sem_multiplier):.12g}",
            "collateral_margin=0",
            "guard=all_other_process_predictors_must_be_collateral_preserved",
            "process_status=" + guarded_summary[["process", "status", "collateral_guard_pass"]].to_csv(index=False),
            "closures=" + closure_summary.to_csv(index=False),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return CollateralGuardProcessChallengeFit(
        v6_fit=v6,
        process_specific_fold_evidence=fold_evidence,
        process_specific_route_summary=route_summary,
        process_summary=guarded_summary,
        specificity_audit=specificity,
        closure_summary=closure_summary,
        selection_receipt=receipt,
    )
