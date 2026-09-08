"""Proxy-closed matched-route ecological process challenge (v6 development).

v5 fixed a state-space error by preserving indeterminate evidence as unresolved.
This development successor keeps that rule and changes the *counterfactual route*.
A declared process knockout may leave substantial process information in retained
predictors.  v6 therefore compares each prediction/ecology-adequate baseline model
with the same ModelSpec after:

1. removing every declared direct/derived/proxy/composite representation in the
   process-information closure; and
2. residualizing the retained ecological predictors against that closure using
   training-background environments only.

The residualization operator never reads occurrence labels or external biological
truth.  It is a stronger information-erasure diagnostic, not a causal adjustment.
Prospective known-truth and fresh biological validation are required before any
performance promotion.
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
    IntervalEvidenceProcessChallengeFit,
    _classify_processes as _classify_interval_processes,
    fit_interval_evidence_process_challenge,
    interval_evidence_state,
)
from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .observation_aware_identification import (
    _fold_indices,
    _prepare_observation_corrections,
    _summary,
    _weighted_presence_rank,
)
from .process_information_closure import (
    process_information_closure,
    summarize_process_information_closures,
)
from .process_information_purge import (
    cross_validated_process_reconstruction,
    fit_process_information_purge,
)
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


@dataclass(frozen=True)
class ProxyClosedRouteProcessChallengeFit:
    v5_fit: IntervalEvidenceProcessChallengeFit
    purged_fold_evidence: pd.DataFrame
    purged_route_summary: pd.DataFrame
    process_summary: pd.DataFrame
    closure_summary: pd.DataFrame
    leakage_diagnostic: pd.DataFrame
    selection_receipt: str

    @property
    def prediction_model_label(self) -> str:
        return self.v5_fit.prediction_model_label

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v5_fit.predict_relative_suitability(frame)

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v5_fit.predict_ecological_suitability(frame)


def _paired_delta(
    baseline_evidence: pd.DataFrame,
    route_evidence: pd.DataFrame,
    *,
    model_label: str,
    baseline_metric: str,
    route_metric: str,
) -> dict[str, object]:
    baseline_route = f"baseline::{model_label}"
    baseline = baseline_evidence.loc[
        baseline_evidence["model_label"].astype(str).eq(str(model_label))
        & baseline_evidence["route"].astype(str).eq(baseline_route),
        ["fold", "complete", baseline_metric],
    ].rename(columns={"complete": "baseline_complete", baseline_metric: "baseline_value"})
    route = route_evidence.loc[
        route_evidence["model_label"].astype(str).eq(str(model_label)),
        ["fold", "complete", route_metric],
    ].rename(columns={"complete": "route_complete", route_metric: "route_value"})
    if baseline["fold"].duplicated().any() or route["fold"].duplicated().any():
        raise ValueError("matched-route evidence has duplicate model-route-fold keys")
    paired = baseline.merge(route, on="fold", how="inner", validate="one_to_one")
    expected = max(len(baseline), len(route))
    complete = bool(
        expected > 0
        and len(baseline) == len(route) == len(paired)
        and paired["baseline_complete"].astype(bool).all()
        and paired["route_complete"].astype(bool).all()
    )
    values = (
        pd.to_numeric(paired["route_value"], errors="coerce")
        - pd.to_numeric(paired["baseline_value"], errors="coerce")
    ).to_numpy(float)
    complete = bool(complete and len(values) and np.isfinite(values).all())
    finite = values[np.isfinite(values)]
    mean = float(np.mean(finite)) if len(finite) else float("nan")
    sem = (
        float(np.std(finite, ddof=1) / np.sqrt(len(finite)))
        if len(finite) >= 2
        else (0.0 if len(finite) == 1 else float("nan"))
    )
    return {
        "complete": complete,
        "mean_delta": mean,
        "sem_delta": sem,
        "n_folds": int(len(paired)),
    }


def _purged_route_cv(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: tuple[str, ...],
    retained_ecological_predictors: tuple[str, ...],
    observation_predictors: tuple[str, ...],
    model_spec: ModelSpec,
    folds,
    corrections,
    purge_degree: int,
    purge_ridge_alpha: float,
    density_probability_epsilon: float,
) -> pd.DataFrame:
    route = f"purged_knockout::{model_spec.label}::{process}"
    rows: list[dict[str, object]] = []
    for fold, ((p_train_idx, b_train_idx, p_test_idx, b_test_idx), correction) in enumerate(
        zip(folds, corrections, strict=True)
    ):
        row: dict[str, object] = {
            "route": route,
            "route_type": "proxy_closed_process_knockout",
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

            purge = fit_process_information_purge(
                b_train,
                process=str(process),
                process_predictors=process_predictors,
                retained_predictors=retained_ecological_predictors,
                degree=int(purge_degree),
                ridge_alpha=float(purge_ridge_alpha),
                minimum_complete_rows=5,
            )
            p_train_purged = purge.transform(p_train)
            b_train_purged = purge.transform(b_train)
            p_test_purged = purge.transform(p_test)
            b_test_purged = purge.transform(b_test)
            model_predictors = retained_ecological_predictors + observation_predictors

            model = fit_relative_suitability_model(
                p_train_purged,
                b_train_purged,
                model_predictors,
                model_spec=model_spec,
            )
            p_full = score_relative_suitability(model, p_test_purged, model_predictors)
            b_full = score_relative_suitability(model, b_test_purged, model_predictors)
            prediction_rank = _presence_rank(p_full, b_full)

            p_eco = score_ecological_suitability(
                model,
                p_test_purged,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_purged,
            )
            b_eco = score_ecological_suitability(
                model,
                b_test_purged,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train_purged,
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
                raise ValueError("purged route produced non-finite evidence")
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


def _presence_rank(presence_scores: np.ndarray, background_scores: np.ndarray) -> float:
    p = np.asarray(presence_scores, dtype=float)
    b = np.asarray(background_scores, dtype=float)
    p = p[np.isfinite(p)]
    b = b[np.isfinite(b)]
    if not len(p) or not len(b):
        return float("nan")
    b_sorted = np.sort(b)
    lower = np.searchsorted(b_sorted, p, side="left")
    upper = np.searchsorted(b_sorted, p, side="right")
    return float(np.mean((lower + 0.5 * (upper - lower)) / len(b_sorted)))


def fit_proxy_closed_route_process_challenge(
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
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> ProxyClosedRouteProcessChallengeFit:
    """Fit v6 development learner with v5 states and proxy-closed matched routes."""

    ecological = tuple(str(x) for x in ecological_predictors)
    observation = tuple(str(x) for x in observation_predictors)
    processes = tuple(str(x) for x in process_universe)
    specs = tuple(model_specs)
    spec_by_label = {spec.label: spec for spec in specs}
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

    expected_labels = tuple(
        sorted(set(v5.v4_fit.v3_fit.route_summary["model_label"].astype(str)))
    )
    unknown_specs = sorted(set(expected_labels) - set(spec_by_label))
    if unknown_specs:
        raise ValueError("v5 baseline uses model specs not supplied to v6: " + ", ".join(unknown_specs))

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

    closure_summary = summarize_process_information_closures(
        process_registry,
        process_universe=processes,
    )
    leakage_frames: list[pd.DataFrame] = []
    fold_frames: list[pd.DataFrame] = []
    route_rows: list[dict[str, object]] = []

    rank_baseline = v5.v4_fit.v3_fit.base_fit.fold_evidence
    density_baseline = v5.v4_fit.density_fold_evidence

    for process in processes:
        closure = tuple(process_information_closure(process_registry, process))
        retained = tuple(p for p in ecological if p not in set(closure))
        if retained:
            try:
                diagnostic = cross_validated_process_reconstruction(
                    background,
                    process=process,
                    process_predictors=closure,
                    retained_predictors=retained,
                    groups=np.asarray(background_groups),
                    n_splits=min(int(n_splits), len(np.unique(background_groups))),
                    degree=int(purge_degree),
                    ridge_alpha=float(purge_ridge_alpha),
                )
                diagnostic["diagnostic_complete"] = True
            except (ValueError, KeyError, np.linalg.LinAlgError):
                diagnostic = pd.DataFrame(
                    [
                        {
                            "process": process,
                            "process_predictor": "",
                            "n_test_rows": 0,
                            "pre_purge_r2": np.nan,
                            "post_purge_r2": np.nan,
                            "pre_purge_rank_correlation": np.nan,
                            "post_purge_rank_correlation": np.nan,
                            "diagnostic_complete": False,
                        }
                    ]
                )
        else:
            diagnostic = pd.DataFrame(
                [
                    {
                        "process": process,
                        "process_predictor": "",
                        "n_test_rows": 0,
                        "pre_purge_r2": np.nan,
                        "post_purge_r2": np.nan,
                        "pre_purge_rank_correlation": np.nan,
                        "post_purge_rank_correlation": np.nan,
                        "diagnostic_complete": False,
                    }
                ]
            )
        leakage_frames.append(diagnostic)

        for model_label in expected_labels:
            spec = spec_by_label[model_label]
            fold_frame = _purged_route_cv(
                presence,
                background,
                process=process,
                process_predictors=closure,
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
            route_name = f"purged_knockout::{model_label}::{process}"

            prediction = _summary(
                fold_frame,
                "presence_rank",
                chance_score=float(chance_score),
                minimum_margin=float(minimum_margin),
                sem_multiplier=float(sem_multiplier),
            )
            ecology = _summary(
                fold_frame,
                "ecological_presence_rank",
                chance_score=float(chance_score),
                minimum_margin=float(minimum_margin),
                sem_multiplier=float(sem_multiplier),
            )
            route_adequate = bool(prediction["adequate"] and ecology["adequate"])

            pred_delta = _paired_delta(
                rank_baseline,
                fold_frame,
                model_label=model_label,
                baseline_metric="presence_rank",
                route_metric="presence_rank",
            )
            eco_delta = _paired_delta(
                rank_baseline,
                fold_frame,
                model_label=model_label,
                baseline_metric="ecological_presence_rank",
                route_metric="ecological_presence_rank",
            )
            density_delta = _paired_delta(
                density_baseline,
                fold_frame,
                model_label=model_label,
                baseline_metric="balanced_density_log_score",
                route_metric="balanced_density_log_score",
            )
            eco_density_delta = _paired_delta(
                density_baseline,
                fold_frame,
                model_label=model_label,
                baseline_metric="ecological_density_log_score",
                route_metric="ecological_density_log_score",
            )

            pred_state = interval_evidence_state(
                pred_delta["mean_delta"],
                pred_delta["sem_delta"],
                margin=float(relative_noninferiority_margin),
                sem_multiplier=float(relative_sem_multiplier),
                complete=bool(pred_delta["complete"]),
            )
            eco_state = interval_evidence_state(
                eco_delta["mean_delta"],
                eco_delta["sem_delta"],
                margin=float(relative_noninferiority_margin),
                sem_multiplier=float(relative_sem_multiplier),
                complete=bool(eco_delta["complete"]),
            )
            density_state = interval_evidence_state(
                density_delta["mean_delta"],
                density_delta["sem_delta"],
                margin=float(density_noninferiority_margin),
                sem_multiplier=float(density_sem_multiplier),
                complete=bool(density_delta["complete"]),
            )
            eco_density_state = interval_evidence_state(
                eco_density_delta["mean_delta"],
                eco_density_delta["sem_delta"],
                margin=float(density_noninferiority_margin),
                sem_multiplier=float(density_sem_multiplier),
                complete=bool(eco_density_delta["complete"]),
            )
            states = tuple(
                str(x["state"])
                for x in (pred_state, eco_state, density_state, eco_density_state)
            )
            complete = bool(fold_frame["complete"].astype(bool).all())
            if not complete or INCOMPLETE_EVIDENCE in states:
                relative_state = INCOMPLETE_EVIDENCE
            elif all(state == NONINFERIOR_EVIDENCE for state in states):
                relative_state = NONINFERIOR_EVIDENCE
            elif any(state == INFERIOR_EVIDENCE for state in states):
                relative_state = INFERIOR_EVIDENCE
            else:
                relative_state = INDETERMINATE_EVIDENCE

            route_rows.append(
                {
                    "process": process,
                    "excluded_process": process,
                    "model_label": model_label,
                    "route": route_name,
                    "route_type": "proxy_closed_process_knockout",
                    "closure_predictors": ",".join(closure),
                    "retained_ecological_predictors": ",".join(retained),
                    "complete": complete,
                    "route_adequate": route_adequate,
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
                    "relative_evidence_state": relative_state,
                    "n_folds": int(len(fold_frame)),
                }
            )

    purged_folds = pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame()
    routes = pd.DataFrame(route_rows)
    process_summary = _classify_interval_processes(
        routes,
        processes,
        expected_model_labels=expected_labels,
    )
    old_status = v5.process_summary.set_index("process")["status"].astype(str).to_dict()
    process_summary["v5_status"] = process_summary["process"].map(old_status)
    process_summary["status_changed_from_v5"] = (
        process_summary["status"].astype(str) != process_summary["v5_status"].astype(str)
    )
    leakage = pd.concat(leakage_frames, ignore_index=True) if leakage_frames else pd.DataFrame()

    receipt_payload = "\n".join(
        [
            "v5_receipt=" + v5.selection_receipt,
            f"purge_degree={int(purge_degree)}",
            f"purge_ridge_alpha={float(purge_ridge_alpha):.12g}",
            "purge_training=background_only_no_occurrence_or_external_truth",
            "process_status=" + process_summary[["process", "status"]].to_csv(index=False),
            "closures=" + closure_summary.to_csv(index=False),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return ProxyClosedRouteProcessChallengeFit(
        v5_fit=v5,
        purged_fold_evidence=purged_folds,
        purged_route_summary=routes,
        process_summary=process_summary,
        closure_summary=closure_summary,
        leakage_diagnostic=leakage,
        selection_receipt=receipt,
    )
