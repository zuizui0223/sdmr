"""Three-state interval evidence for ecological process challenges.

This successor fixes one logical error exposed by v4 development: failure to
establish non-inferiority is not positive evidence of inferiority. Each paired
relative metric is therefore assigned one of three states around the frozen
non-inferiority margin:

- noninferior: lower uncertainty bound >= -margin;
- inferior: upper uncertainty bound < -margin;
- indeterminate: the uncertainty band overlaps -margin.

The prediction model, process-information closure, spatial folds, observation
correction, absolute adequacy gates, density/rank margins and shared-carrier
logic are inherited unchanged. The only scientific change is the state space
used for relative process evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import hashlib

import numpy as np
import pandas as pd

from .density_ratio_process_challenge import (
    DensityRatioProcessChallengeFit,
    fit_density_ratio_process_challenge,
)
from .model import ModelSpec
from .process_challenge_learner import CONTRIBUTORY, REPLACEABLE, REQUIRED, UNRESOLVED
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


NONINFERIOR_EVIDENCE = "noninferior"
INFERIOR_EVIDENCE = "inferior"
INDETERMINATE_EVIDENCE = "indeterminate"
INCOMPLETE_EVIDENCE = "incomplete"


@dataclass(frozen=True)
class IntervalEvidenceProcessChallengeFit:
    v4_fit: DensityRatioProcessChallengeFit
    route_summary: pd.DataFrame
    process_summary: pd.DataFrame
    selection_receipt: str

    @property
    def prediction_model_label(self) -> str:
        return self.v4_fit.prediction_model_label

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v4_fit.predict_relative_suitability(frame)

    def predict_ecological_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        return self.v4_fit.predict_ecological_suitability(frame)


def interval_evidence_state(
    mean_delta: float,
    sem_delta: float,
    *,
    margin: float,
    sem_multiplier: float,
    complete: bool = True,
) -> dict[str, object]:
    """Classify paired relative evidence without collapsing uncertainty into loss."""
    if float(margin) < 0:
        raise ValueError("margin must be non-negative")
    if float(sem_multiplier) < 0:
        raise ValueError("sem_multiplier must be non-negative")
    mean = float(mean_delta)
    sem = float(sem_delta)
    if not bool(complete) or not np.isfinite(mean) or not np.isfinite(sem) or sem < 0:
        return {
            "state": INCOMPLETE_EVIDENCE,
            "lower": float("nan"),
            "upper": float("nan"),
        }
    lower = mean - float(sem_multiplier) * sem
    upper = mean + float(sem_multiplier) * sem
    boundary = -float(margin)
    if lower >= boundary - 1e-12:
        state = NONINFERIOR_EVIDENCE
    elif upper < boundary - 1e-12:
        state = INFERIOR_EVIDENCE
    else:
        state = INDETERMINATE_EVIDENCE
    return {"state": state, "lower": float(lower), "upper": float(upper)}


def _enrich_routes(
    v4: DensityRatioProcessChallengeFit,
    *,
    rank_margin: float,
    rank_sem_multiplier: float,
    density_margin: float,
    density_sem_multiplier: float,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in v4.route_summary.to_dict(orient="records"):
        rank_complete = bool(row.get("relative_complete", False))
        density_complete = bool(row.get("density_complete", False))
        pred = interval_evidence_state(
            row.get("mean_prediction_delta_vs_baseline", float("nan")),
            row.get("prediction_delta_sem", float("nan")),
            margin=rank_margin,
            sem_multiplier=rank_sem_multiplier,
            complete=rank_complete,
        )
        eco_rank = interval_evidence_state(
            row.get("mean_ecological_delta_vs_baseline", float("nan")),
            row.get("ecological_delta_sem", float("nan")),
            margin=rank_margin,
            sem_multiplier=rank_sem_multiplier,
            complete=rank_complete,
        )
        density = interval_evidence_state(
            row.get("mean_density_delta_vs_baseline", float("nan")),
            row.get("density_delta_sem", float("nan")),
            margin=density_margin,
            sem_multiplier=density_sem_multiplier,
            complete=density_complete,
        )
        eco_density = interval_evidence_state(
            row.get("mean_ecological_density_delta_vs_baseline", float("nan")),
            row.get("ecological_density_delta_sem", float("nan")),
            margin=density_margin,
            sem_multiplier=density_sem_multiplier,
            complete=density_complete,
        )
        states = tuple(str(x["state"]) for x in (pred, eco_rank, density, eco_density))
        if INCOMPLETE_EVIDENCE in states:
            relative_state = INCOMPLETE_EVIDENCE
        elif all(state == NONINFERIOR_EVIDENCE for state in states):
            relative_state = NONINFERIOR_EVIDENCE
        elif any(state == INFERIOR_EVIDENCE for state in states):
            relative_state = INFERIOR_EVIDENCE
        else:
            relative_state = INDETERMINATE_EVIDENCE

        enriched = dict(row)
        enriched.update(
            {
                "prediction_interval_state": pred["state"],
                "prediction_interval_upper": pred["upper"],
                "ecological_rank_interval_state": eco_rank["state"],
                "ecological_rank_interval_upper": eco_rank["upper"],
                "density_interval_state": density["state"],
                "density_interval_upper": density["upper"],
                "ecological_density_interval_state": eco_density["state"],
                "ecological_density_interval_upper": eco_density["upper"],
                "relative_evidence_state": relative_state,
            }
        )
        rows.append(enriched)
    return pd.DataFrame(rows)


def _classify_processes(
    route_summary: pd.DataFrame,
    process_universe: Sequence[str],
    *,
    expected_model_labels: Sequence[str],
) -> pd.DataFrame:
    expected = tuple(str(x) for x in expected_model_labels)
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("expected_model_labels must be unique and non-empty")
    rows: list[dict[str, object]] = []
    for process in tuple(str(x) for x in process_universe):
        group = route_summary.loc[route_summary["excluded_process"].astype(str).eq(process)].copy()
        if group.empty:
            rows.append(
                {
                    "process": process,
                    "status": UNRESOLVED,
                    "process_detected": False,
                    "n_expected_routes": len(expected),
                    "n_absolute_adequate_routes": 0,
                    "n_noninferior_routes": 0,
                    "n_inferior_viable_routes": 0,
                    "n_indeterminate_viable_routes": 0,
                    "n_incomplete_routes": len(expected),
                }
            )
            continue
        if group[["model_label", "excluded_process"]].duplicated().any():
            raise ValueError(f"duplicate model-process route evidence for {process!r}")
        labels = tuple(sorted(group["model_label"].astype(str)))
        if labels != tuple(sorted(expected)) or len(group) != len(expected):
            rows.append(
                {
                    "process": process,
                    "status": UNRESOLVED,
                    "process_detected": False,
                    "n_expected_routes": len(expected),
                    "n_absolute_adequate_routes": int(group["route_adequate"].astype(bool).sum()),
                    "n_noninferior_routes": 0,
                    "n_inferior_viable_routes": 0,
                    "n_indeterminate_viable_routes": 0,
                    "n_incomplete_routes": max(0, len(expected) - len(group)),
                }
            )
            continue

        absolute_complete = group["complete"].astype(bool)
        if not bool(absolute_complete.all()):
            status = UNRESOLVED
        else:
            viable = group.loc[group["route_adequate"].astype(bool)].copy()
            if viable.empty:
                status = REQUIRED
            else:
                noninferior = viable["relative_evidence_state"].astype(str).eq(NONINFERIOR_EVIDENCE)
                inferior = viable["relative_evidence_state"].astype(str).eq(INFERIOR_EVIDENCE)
                if bool(noninferior.any()):
                    status = REPLACEABLE
                elif bool(inferior.all()):
                    status = CONTRIBUTORY
                else:
                    status = UNRESOLVED

        viable = group.loc[group["route_adequate"].astype(bool)].copy()
        state = viable["relative_evidence_state"].astype(str) if len(viable) else pd.Series(dtype=str)
        rows.append(
            {
                "process": process,
                "status": status,
                "process_detected": status in {CONTRIBUTORY, REQUIRED},
                "n_expected_routes": len(expected),
                "n_absolute_adequate_routes": int(len(viable)),
                "n_noninferior_routes": int(state.eq(NONINFERIOR_EVIDENCE).sum()),
                "n_inferior_viable_routes": int(state.eq(INFERIOR_EVIDENCE).sum()),
                "n_indeterminate_viable_routes": int(state.eq(INDETERMINATE_EVIDENCE).sum()),
                "n_incomplete_routes": int(
                    (~group["complete"].astype(bool)).sum()
                    + state.eq(INCOMPLETE_EVIDENCE).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def fit_interval_evidence_process_challenge(
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
) -> IntervalEvidenceProcessChallengeFit:
    """Fit v5 using unchanged v4 scores but an abstention-preserving state rule."""
    v4 = fit_density_ratio_process_challenge(
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
        relative_noninferiority_margin=relative_noninferiority_margin,
        relative_sem_multiplier=relative_sem_multiplier,
        density_noninferiority_margin=density_noninferiority_margin,
        density_sem_multiplier=density_sem_multiplier,
        density_probability_epsilon=density_probability_epsilon,
        observation_signal_chance=observation_signal_chance,
        observation_signal_margin=observation_signal_margin,
        observation_signal_sem_multiplier=observation_signal_sem_multiplier,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
        observation_weight_probability_epsilon=observation_weight_probability_epsilon,
        occurrence_split=occurrence_split,
        occurrence_id_col=occurrence_id_col,
    )
    routes = _enrich_routes(
        v4,
        rank_margin=float(relative_noninferiority_margin),
        rank_sem_multiplier=float(relative_sem_multiplier),
        density_margin=float(density_noninferiority_margin),
        density_sem_multiplier=float(density_sem_multiplier),
    )
    expected_labels = tuple(sorted(set(v4.v3_fit.route_summary["model_label"].astype(str))))
    process_summary = _classify_processes(
        routes,
        process_universe,
        expected_model_labels=expected_labels,
    )
    receipt_payload = "\n".join(
        [
            "v4_receipt=" + v4.selection_receipt,
            "relative_state_rule=lower>=-margin;upper<-margin;otherwise_indeterminate",
            "process_status=" + process_summary[["process", "status"]].to_csv(index=False),
        ]
    )
    return IntervalEvidenceProcessChallengeFit(
        v4_fit=v4,
        route_summary=routes,
        process_summary=process_summary,
        selection_receipt=hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest(),
    )
