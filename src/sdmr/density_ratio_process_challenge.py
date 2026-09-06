"""Density-ratio process challenge layered on the v3 rank challenge.

Presence-only SDMs do not identify absolute occurrence probability. A balanced
presence-vs-background classifier can nevertheless estimate an equal-prior
presence/background density ratio. This module adds a cross-fitted proper log
score for that discrimination problem to the existing v3 rank-based challenge.

Prediction output is unchanged. The extra score is used only to decide whether a
process-free route is sufficiently similar to its matched baseline to count as a
replaceability witness.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import hashlib

import numpy as np
import pandas as pd

from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .observation_aware_identification import _fold_indices, _prepare_observation_corrections
from .process_challenge_learner import (
    CONTRIBUTORY,
    REPLACEABLE,
    REQUIRED,
    UNRESOLVED,
    ProcessChallengeFit,
    fit_process_challenge_learner,
)
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


@dataclass(frozen=True)
class DensityRatioProcessChallengeFit:
    v3_fit: ProcessChallengeFit
    density_fold_evidence: pd.DataFrame
    route_summary: pd.DataFrame
    process_summary: pd.DataFrame
    density_noninferiority_margin: float
    density_sem_multiplier: float
    selection_receipt: str

    @property
    def prediction_model_label(self) -> str:
        return self.v3_fit.prediction_model_label

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v3_fit.predict_relative_suitability(frame)

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v3_fit.predict_ecological_suitability(frame)


def balanced_density_ratio_log_score(
    presence_scores: Sequence[float] | np.ndarray,
    background_scores: Sequence[float] | np.ndarray,
    *,
    presence_weights: Sequence[float] | np.ndarray | None = None,
    probability_epsilon: float = 1e-6,
) -> float:
    """Equal-prior proper log score for presence versus background discrimination.

    ``score_relative_suitability`` is the class probability under the balanced
    presence/background fitting objective. With equal class prior, its odds are
    proportional to the fitted presence/background density ratio. The balanced
    log score is therefore a proper score for the relative-distribution problem,
    not an estimate of absolute occurrence probability.
    """
    if not 0.0 < float(probability_epsilon) < 0.5:
        raise ValueError("probability_epsilon must lie in (0, 0.5)")
    p = np.asarray(presence_scores, dtype=float)
    b = np.asarray(background_scores, dtype=float)
    keep_p = np.isfinite(p)
    keep_b = np.isfinite(b)
    p = p[keep_p]
    b = b[keep_b]
    if not len(p) or not len(b):
        return float("nan")
    p = np.clip(p, probability_epsilon, 1.0 - probability_epsilon)
    b = np.clip(b, probability_epsilon, 1.0 - probability_epsilon)
    if presence_weights is None:
        p_term = float(np.mean(np.log(p)))
    else:
        w_all = np.asarray(presence_weights, dtype=float)
        if len(w_all) != len(keep_p):
            raise ValueError("presence_weights must align with unfiltered presence scores")
        w = w_all[keep_p]
        valid_w = np.isfinite(w) & (w > 0)
        if not valid_w.any() or not float(w[valid_w].sum()) > 0:
            return float("nan")
        p_term = float(np.average(np.log(p[valid_w]), weights=w[valid_w]))
    b_term = float(np.mean(np.log1p(-b)))
    return 0.5 * (p_term + b_term)


def _density_route_cv(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    ecological_predictors: tuple[str, ...],
    observation_predictors: tuple[str, ...],
    model_spec: ModelSpec,
    folds,
    corrections,
    *,
    route: str,
    route_type: str,
    excluded_process: str = "",
    probability_epsilon: float = 1e-6,
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
            "balanced_density_log_score": float("nan"),
            "ecological_density_log_score": float("nan"),
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
            full_score = balanced_density_ratio_log_score(
                p_full,
                b_full,
                probability_epsilon=probability_epsilon,
            )
            p_eco = score_ecological_suitability(
                model,
                p_test,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train,
            )
            b_eco = score_ecological_suitability(
                model,
                b_test,
                model_predictors,
                observation_predictors=observation_predictors,
                observation_reference=b_train,
            )
            eco_score = balanced_density_ratio_log_score(
                p_eco,
                b_eco,
                presence_weights=correction.weights,
                probability_epsilon=probability_epsilon,
            )
            if not np.isfinite(full_score) or not np.isfinite(eco_score):
                raise ValueError("route produced non-finite density log score")
            row.update(
                {
                    "complete": True,
                    "balanced_density_log_score": float(full_score),
                    "ecological_density_log_score": float(eco_score),
                }
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
    return pd.DataFrame(rows)


def _paired_density_delta_summary(
    fold_evidence: pd.DataFrame,
    *,
    model_label: str,
    knockout_route: str,
    metric: str,
    margin: float,
    sem_multiplier: float,
) -> dict[str, object]:
    """Compare one model's knockout route with its own matched baseline.

    Density evidence is keyed by model label, route and fold. Filtering on all
    three dimensions prevents a route label collision from silently pairing a
    knockout from one model with the baseline of another model.
    """
    baseline_route = f"baseline::{model_label}"
    baseline = fold_evidence.loc[
        fold_evidence["model_label"].astype(str).eq(str(model_label))
        & fold_evidence["route"].astype(str).eq(baseline_route),
        ["fold", "complete", metric],
    ].rename(columns={"complete": "baseline_complete", metric: "baseline_value"})
    knockout = fold_evidence.loc[
        fold_evidence["model_label"].astype(str).eq(str(model_label))
        & fold_evidence["route"].astype(str).eq(str(knockout_route)),
        ["fold", "complete", metric],
    ].rename(columns={"complete": "knockout_complete", metric: "knockout_value"})

    if baseline["fold"].duplicated().any() or knockout["fold"].duplicated().any():
        raise ValueError("density evidence has duplicate model-route-fold keys")
    paired = baseline.merge(knockout, on="fold", how="inner", validate="one_to_one")
    expected_n = max(len(baseline), len(knockout))
    if paired.empty or len(paired) != expected_n or len(baseline) != len(knockout):
        return {
            "complete": False,
            "mean_delta": float("nan"),
            "sem_delta": float("nan"),
            "lower_delta": float("nan"),
            "noninferior": False,
            "n_folds": int(len(paired)),
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


def _density_enriched_routes(
    v3_fit: ProcessChallengeFit,
    density_fold_evidence: pd.DataFrame,
    *,
    margin: float,
    sem_multiplier: float,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in v3_fit.route_summary.to_dict(orient="records"):
        full = _paired_density_delta_summary(
            density_fold_evidence,
            model_label=str(row["model_label"]),
            knockout_route=str(row["route"]),
            metric="balanced_density_log_score",
            margin=float(margin),
            sem_multiplier=float(sem_multiplier),
        )
        eco = _paired_density_delta_summary(
            density_fold_evidence,
            model_label=str(row["model_label"]),
            knockout_route=str(row["route"]),
            metric="ecological_density_log_score",
            margin=float(margin),
            sem_multiplier=float(sem_multiplier),
        )
        enriched = dict(row)
        enriched.update(
            {
                "mean_density_delta_vs_baseline": full["mean_delta"],
                "density_delta_sem": full["sem_delta"],
                "density_delta_lower": full["lower_delta"],
                "density_noninferior": bool(full["noninferior"]),
                "mean_ecological_density_delta_vs_baseline": eco["mean_delta"],
                "ecological_density_delta_sem": eco["sem_delta"],
                "ecological_density_delta_lower": eco["lower_delta"],
                "ecological_density_noninferior": bool(eco["noninferior"]),
                "density_complete": bool(full["complete"] and eco["complete"]),
                "multicriterion_noninferior": bool(
                    row["relative_noninferior"]
                    and full["noninferior"]
                    and eco["noninferior"]
                ),
            }
        )
        rows.append(enriched)
    return pd.DataFrame(rows)


def _classify_processes(
    route_summary: pd.DataFrame,
    process_universe: Sequence[str],
    *,
    expected_model_labels: Sequence[str] | None = None,
) -> pd.DataFrame:
    required_columns = {
        "model_label",
        "route",
        "excluded_process",
        "density_complete",
        "multicriterion_noninferior",
        "route_adequate",
    }
    missing = sorted(required_columns - set(route_summary.columns))
    if missing:
        raise KeyError("v4 route summary missing columns: " + ", ".join(missing))
    if route_summary.duplicated(["model_label", "excluded_process"]).any():
        raise ValueError("v4 route summary has duplicate model-process routes")

    if expected_model_labels is None:
        expected_models = tuple(sorted(set(route_summary["model_label"].astype(str))))
    else:
        expected_models = tuple(str(x) for x in expected_model_labels)
        if len(set(expected_models)) != len(expected_models):
            raise ValueError("expected_model_labels must be unique")
    expected_set = set(expected_models)

    rows = []
    for process in tuple(str(x) for x in process_universe):
        group = route_summary.loc[route_summary["excluded_process"].astype(str).eq(process)]
        group_models = set(group["model_label"].astype(str))
        expected = len(expected_models)
        density_complete = bool(
            len(group) == expected
            and group_models == expected_set
            and group["density_complete"].astype(bool).all()
        )
        complete_n = int(group["density_complete"].astype(bool).sum()) if len(group) else 0
        witnesses = group.loc[group["multicriterion_noninferior"].astype(bool), "route"].astype(str).tolist()
        absolute = group.loc[group["route_adequate"].astype(bool), "route"].astype(str).tolist()
        if witnesses:
            status = REPLACEABLE
        elif not density_complete:
            status = UNRESOLVED
        elif absolute:
            status = CONTRIBUTORY
        else:
            status = REQUIRED
        rows.append(
            {
                "process": process,
                "status": status,
                "process_detected": status in {CONTRIBUTORY, REQUIRED},
                "n_process_baseline_models": expected,
                "n_complete_density_routes": complete_n,
                "n_absolute_adequate_routes": len(absolute),
                "n_multicriterion_noninferior_routes": len(witnesses),
                "multicriterion_noninferior_routes": ",".join(sorted(witnesses)),
            }
        )
    return pd.DataFrame(rows)


def fit_density_ratio_process_challenge(
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
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> DensityRatioProcessChallengeFit:
    """Fit v4: v3 rank challenge plus matched density-ratio log-score challenge."""
    if not 0.0 <= float(density_noninferiority_margin) < 1.0:
        raise ValueError("density_noninferiority_margin must be in [0, 1)")
    if float(density_sem_multiplier) < 0:
        raise ValueError("density_sem_multiplier must be non-negative")

    ecological = tuple(str(x) for x in ecological_predictors)
    observation = tuple(str(x) for x in observation_predictors)
    processes = tuple(str(x) for x in process_universe)
    specs = tuple(model_specs)
    v3 = fit_process_challenge_learner(
        presence,
        background,
        presence_groups,
        background_groups,
        ecological_predictors=ecological,
        observation_predictors=observation,
        process_registry=process_registry,
        process_universe=processes,
        model_specs=specs,
        n_splits=n_splits,
        chance_score=chance_score,
        minimum_margin=minimum_margin,
        sem_multiplier=sem_multiplier,
        relative_noninferiority_margin=relative_noninferiority_margin,
        relative_sem_multiplier=relative_sem_multiplier,
        observation_signal_chance=observation_signal_chance,
        observation_signal_margin=observation_signal_margin,
        observation_signal_sem_multiplier=observation_signal_sem_multiplier,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
        observation_weight_probability_epsilon=observation_weight_probability_epsilon,
        occurrence_split=occurrence_split,
        occurrence_id_col=occurrence_id_col,
    )

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
        observation_signal_chance=observation_signal_chance,
        observation_signal_margin=observation_signal_margin,
        observation_signal_sem_multiplier=observation_signal_sem_multiplier,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
        observation_weight_probability_epsilon=observation_weight_probability_epsilon,
    )
    spec_by_label = {spec.label: spec for spec in specs}
    process_models = tuple(sorted(set(v3.route_summary["model_label"].astype(str))))
    if v3.route_summary.duplicated(["model_label", "excluded_process"]).any():
        raise ValueError("v3 route summary has duplicate model-process routes")

    density_frames = []
    for label in process_models:
        density_frames.append(
            _density_route_cv(
                presence,
                background,
                ecological,
                observation,
                spec_by_label[label],
                folds,
                corrections,
                route=f"baseline::{label}",
                route_type="baseline",
                probability_epsilon=density_probability_epsilon,
            )
        )

    seen_keys: set[tuple[str, str]] = set()
    for row in v3.route_summary.to_dict(orient="records"):
        label = str(row["model_label"])
        route = str(row["route"])
        key = (label, route)
        if key in seen_keys:
            raise ValueError("v3 route summary has duplicate model-route keys")
        seen_keys.add(key)
        retained = tuple(x for x in str(row["retained_ecological_predictors"]).split(",") if x)
        density_frames.append(
            _density_route_cv(
                presence,
                background,
                retained,
                observation,
                spec_by_label[label],
                folds,
                corrections,
                route=route,
                route_type="process_knockout",
                excluded_process=str(row["excluded_process"]),
                probability_epsilon=density_probability_epsilon,
            )
        )
    density_evidence = pd.concat(density_frames, ignore_index=True)
    if density_evidence.duplicated(["model_label", "route", "fold"]).any():
        raise ValueError("density evidence has duplicate model-route-fold keys")

    routes = _density_enriched_routes(
        v3,
        density_evidence,
        margin=float(density_noninferiority_margin),
        sem_multiplier=float(density_sem_multiplier),
    )
    process_summary = _classify_processes(
        routes,
        processes,
        expected_model_labels=process_models,
    )
    receipt_payload = "\n".join(
        [
            "v3_receipt=" + v3.selection_receipt,
            "process_models=" + ",".join(process_models),
            f"density_margin={float(density_noninferiority_margin):.12g}",
            f"density_sem={float(density_sem_multiplier):.12g}",
            f"density_epsilon={float(density_probability_epsilon):.12g}",
            "process_status=" + process_summary[["process", "status"]].to_csv(index=False),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return DensityRatioProcessChallengeFit(
        v3_fit=v3,
        density_fold_evidence=density_evidence,
        route_summary=routes,
        process_summary=process_summary,
        density_noninferiority_margin=float(density_noninferiority_margin),
        density_sem_multiplier=float(density_sem_multiplier),
        selection_receipt=receipt,
    )