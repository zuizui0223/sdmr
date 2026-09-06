"""Baseline-relative ecological process challenge learner.

This module deliberately separates three inferential targets:

1. prediction: choose a single canonical predictive winner;
2. contribution: ask whether excluding a process causes a material loss relative
   to a matched baseline model while some absolutely adequate alternative survives;
3. necessity: ask whether every complete process-exclusion route loses absolute
   adequacy.

The implementation wraps the existing observation-aware identification learner,
so spatial folds, process-information closure, observation correction and sealed
occurrence barriers remain unchanged. The only additional ingredient is a paired,
baseline-relative non-inferiority challenge on the same inner folds.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .model import ModelSpec, score_ecological_suitability, score_relative_suitability
from .observation_aware_identification import (
    ObservationAwareIdentificationFit,
    fit_observation_aware_identification,
)
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


REPLACEABLE = "replaceable_under_evidence_contract"
CONTRIBUTORY = "contributory_under_evidence_contract"
REQUIRED = "required_by_evidence_contract"
UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ProcessChallengeFit:
    base_fit: ObservationAwareIdentificationFit
    route_summary: pd.DataFrame
    process_summary: pd.DataFrame
    prediction_model_label: str
    selection_receipt: str
    relative_noninferiority_margin: float
    relative_sem_multiplier: float

    @property
    def prediction_model(self):
        by_label = dict(self.base_fit.fitted_models)
        return by_label[self.prediction_model_label]

    @property
    def model_predictors(self) -> tuple[str, ...]:
        return self.base_fit.model_predictors

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return score_relative_suitability(
            self.prediction_model,
            frame,
            self.model_predictors,
        )

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return score_ecological_suitability(
            self.prediction_model,
            frame,
            self.model_predictors,
            observation_predictors=self.base_fit.observation_predictors,
            observation_reference=self.base_fit.observation_reference,
        )


def _paired_delta_summary(
    fold_evidence: pd.DataFrame,
    *,
    model_label: str,
    knockout_route: str,
    metric: str,
    margin: float,
    sem_multiplier: float,
) -> dict[str, object]:
    baseline_route = f"baseline::{model_label}"
    baseline = fold_evidence.loc[
        fold_evidence["route"].astype(str).eq(baseline_route),
        ["fold", "complete", metric],
    ].rename(columns={"complete": "baseline_complete", metric: "baseline_value"})
    knockout = fold_evidence.loc[
        fold_evidence["route"].astype(str).eq(str(knockout_route)),
        ["fold", "complete", metric],
    ].rename(columns={"complete": "knockout_complete", metric: "knockout_value"})
    paired = baseline.merge(knockout, on="fold", how="inner", validate="one_to_one")
    if paired.empty:
        return {
            "complete": False,
            "mean_delta": float("nan"),
            "sem_delta": float("nan"),
            "lower_delta": float("nan"),
            "noninferior": False,
            "n_folds": 0,
        }
    values = (
        pd.to_numeric(paired["knockout_value"], errors="coerce")
        - pd.to_numeric(paired["baseline_value"], errors="coerce")
    ).to_numpy(float)
    complete = bool(
        paired["baseline_complete"].astype(bool).all()
        and paired["knockout_complete"].astype(bool).all()
        and np.isfinite(values).all()
    )
    finite = values[np.isfinite(values)]
    mean = float(np.mean(finite)) if len(finite) else float("nan")
    sem = (
        float(np.std(finite, ddof=1) / np.sqrt(len(finite)))
        if len(finite) >= 2
        else (0.0 if len(finite) == 1 else float("nan"))
    )
    lower = mean - float(sem_multiplier) * sem if np.isfinite(mean) and np.isfinite(sem) else float("nan")
    noninferior = bool(
        complete
        and np.isfinite(lower)
        and lower >= -float(margin) - 1e-12
    )
    return {
        "complete": complete,
        "mean_delta": mean,
        "sem_delta": sem,
        "lower_delta": lower,
        "noninferior": noninferior,
        "n_folds": int(len(paired)),
    }


def _canonical_prediction_winner(base_fit: ObservationAwareIdentificationFit) -> str:
    frame = base_fit.baseline_summary.copy()
    frame = frame.loc[frame["prediction_adequate"].astype(bool)].copy()
    if frame.empty:
        raise ValueError("process challenge learner has no prediction-adequate baseline model")
    frame["mean_presence_rank"] = pd.to_numeric(frame["mean_presence_rank"], errors="coerce")
    frame = frame.loc[np.isfinite(frame["mean_presence_rank"])].copy()
    if frame.empty:
        raise ValueError("process challenge learner has no finite predictive baseline")
    frame = frame.sort_values(
        ["mean_presence_rank", "model_label"],
        ascending=[False, True],
        kind="mergesort",
    )
    return str(frame.iloc[0]["model_label"])


def fit_process_challenge_learner(
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
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> ProcessChallengeFit:
    """Fit the dual-output prediction/process challenge learner.

    The 0.02 default relative margin intentionally matches the already-used
    sealed prediction non-inferiority guardrail; it is not calibrated here.
    """
    if not 0.0 <= float(relative_noninferiority_margin) < 1.0:
        raise ValueError("relative_noninferiority_margin must be in [0, 1)")
    if float(relative_sem_multiplier) < 0:
        raise ValueError("relative_sem_multiplier must be non-negative")

    base_fit = fit_observation_aware_identification(
        presence,
        background,
        presence_groups,
        background_groups,
        ecological_predictors=ecological_predictors,
        observation_predictors=observation_predictors,
        process_registry=process_registry,
        process_universe=process_universe,
        model_specs=model_specs,
        n_splits=n_splits,
        chance_score=chance_score,
        minimum_margin=minimum_margin,
        sem_multiplier=sem_multiplier,
        observation_signal_chance=observation_signal_chance,
        observation_signal_margin=observation_signal_margin,
        observation_signal_sem_multiplier=observation_signal_sem_multiplier,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
        observation_weight_probability_epsilon=observation_weight_probability_epsilon,
        occurrence_split=occurrence_split,
        occurrence_id_col=occurrence_id_col,
    )

    baseline = base_fit.baseline_summary.copy()
    process_models = tuple(
        baseline.loc[
            baseline["prediction_adequate"].astype(bool)
            & baseline["ecological_adequate"].astype(bool),
            "model_label",
        ].astype(str)
    )
    if not process_models:
        raise ValueError("no baseline model passed both prediction and ecological adequacy")

    routes = base_fit.knockout_summary.loc[
        base_fit.knockout_summary["model_label"].astype(str).isin(process_models)
    ].copy()
    enriched_rows: list[dict[str, object]] = []
    for row in routes.to_dict(orient="records"):
        pred = _paired_delta_summary(
            base_fit.fold_evidence,
            model_label=str(row["model_label"]),
            knockout_route=str(row["route"]),
            metric="presence_rank",
            margin=float(relative_noninferiority_margin),
            sem_multiplier=float(relative_sem_multiplier),
        )
        eco = _paired_delta_summary(
            base_fit.fold_evidence,
            model_label=str(row["model_label"]),
            knockout_route=str(row["route"]),
            metric="ecological_presence_rank",
            margin=float(relative_noninferiority_margin),
            sem_multiplier=float(relative_sem_multiplier),
        )
        enriched = dict(row)
        enriched.update(
            {
                "mean_prediction_delta_vs_baseline": pred["mean_delta"],
                "prediction_delta_sem": pred["sem_delta"],
                "prediction_delta_lower": pred["lower_delta"],
                "prediction_noninferior": bool(pred["noninferior"]),
                "mean_ecological_delta_vs_baseline": eco["mean_delta"],
                "ecological_delta_sem": eco["sem_delta"],
                "ecological_delta_lower": eco["lower_delta"],
                "ecological_noninferior": bool(eco["noninferior"]),
                "relative_complete": bool(pred["complete"] and eco["complete"]),
                "relative_noninferior": bool(
                    row["route_adequate"]
                    and pred["noninferior"]
                    and eco["noninferior"]
                ),
            }
        )
        enriched_rows.append(enriched)
    route_summary = pd.DataFrame(enriched_rows)

    process_rows: list[dict[str, object]] = []
    for process in tuple(str(x) for x in process_universe):
        group = route_summary.loc[route_summary["excluded_process"].astype(str).eq(process)]
        expected = len(process_models)
        complete_n = int(group["relative_complete"].astype(bool).sum()) if len(group) else 0
        noninferior = group.loc[group["relative_noninferior"].astype(bool), "route"].astype(str).tolist()
        absolute = group.loc[group["route_adequate"].astype(bool), "route"].astype(str).tolist()
        if noninferior:
            status = REPLACEABLE
        elif len(group) != expected or complete_n != expected:
            status = UNRESOLVED
        elif absolute:
            status = CONTRIBUTORY
        else:
            status = REQUIRED
        process_rows.append(
            {
                "process": process,
                "status": status,
                "process_detected": status in (CONTRIBUTORY, REQUIRED),
                "n_process_baseline_models": expected,
                "n_complete_routes": complete_n,
                "n_absolute_adequate_routes": len(absolute),
                "n_relative_noninferior_routes": len(noninferior),
                "absolute_adequate_routes": ",".join(sorted(absolute)),
                "relative_noninferior_routes": ",".join(sorted(noninferior)),
            }
        )
    process_summary = pd.DataFrame(process_rows)
    prediction_model_label = _canonical_prediction_winner(base_fit)

    receipt_payload = "\n".join(
        [
            "base_receipt=" + base_fit.selection_receipt,
            "prediction_model=" + prediction_model_label,
            f"relative_margin={float(relative_noninferiority_margin):.12g}",
            f"relative_sem={float(relative_sem_multiplier):.12g}",
            "process_status=" + process_summary[["process", "status"]].to_csv(index=False),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return ProcessChallengeFit(
        base_fit=base_fit,
        route_summary=route_summary,
        process_summary=process_summary,
        prediction_model_label=prediction_model_label,
        selection_receipt=receipt,
        relative_noninferiority_margin=float(relative_noninferiority_margin),
        relative_sem_multiplier=float(relative_sem_multiplier),
    )
