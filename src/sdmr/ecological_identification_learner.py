"""Set-valued ecological-identification learner.

This is a prospective prototype and is not part of any frozen Product-A
scientific endpoint.  It learns an *admissible model set* from model-pool data
only, then challenges each declared ecological process by refitting the same
learner family after process-information closure knockout.

The outer sealed occurrence answer-check is never used for fitting, tuning,
process classification or process necessity.  It may be opened only after the
learner has produced a deterministic selection receipt.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import presence_rank_score
from .model import ModelSpec, fit_relative_suitability_model, score_relative_suitability
from .process_information_closure import freeze_process_information_knockout_registry
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


@dataclass(frozen=True)
class IdentificationLearnerFit:
    predictors: tuple[str, ...]
    process_universe: tuple[str, ...]
    fold_evidence: pd.DataFrame
    baseline_summary: pd.DataFrame
    process_summary: pd.DataFrame
    admissible_model_labels: tuple[str, ...]
    fitted_models: tuple[tuple[str, object], ...]
    selection_receipt: str
    chance_score: float
    adequacy_floor: float
    sem_multiplier: float

    def predict_relative_suitability(self, frame: pd.DataFrame) -> np.ndarray:
        """Mean prediction across the admissible fitted-model set."""

        if not self.fitted_models:
            raise RuntimeError("identification learner has no fitted admissible models")
        predictions = []
        for _, model in self.fitted_models:
            predictions.append(score_relative_suitability(model, frame, self.predictors))
        matrix = np.vstack(predictions)
        with np.errstate(invalid="ignore"):
            return np.nanmean(matrix, axis=0)

    def evaluate_answer_check(
        self,
        full_occurrence_features: pd.DataFrame,
        answer_background: pd.DataFrame,
        split: OccurrenceAnswerCheckSplit,
        *,
        id_col: str | None = None,
    ) -> dict[str, float | int | str]:
        """Open and score the sealed occurrence answer-check after selection."""

        sealed_presence = split.open_answer_check(
            full_occurrence_features,
            selection_receipt=self.selection_receipt,
            id_col=id_col,
        )
        p_scores = self.predict_relative_suitability(sealed_presence)
        b_scores = self.predict_relative_suitability(answer_background)
        return {
            "selection_receipt": self.selection_receipt,
            "presence_rank": float(presence_rank_score(p_scores, b_scores)),
            "n_answer_check_presence": int(np.isfinite(p_scores).sum()),
            "n_answer_check_background": int(np.isfinite(b_scores).sum()),
        }


def _unique_strings(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if not result or any(not value for value in result):
        raise ValueError(f"{name} must contain non-empty values")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _model_specs_by_label(model_specs: Sequence[ModelSpec]) -> dict[str, ModelSpec]:
    specs = tuple(model_specs)
    if not specs:
        raise ValueError("model_specs must be non-empty")
    mapping = {spec.label: spec for spec in specs}
    if len(mapping) != len(specs):
        raise ValueError("model_specs must have unique labels")
    return mapping


def _summarize_route(
    frame: pd.DataFrame,
    *,
    chance_score: float,
    minimum_margin: float,
    sem_multiplier: float,
) -> dict[str, object]:
    scores = pd.to_numeric(frame["presence_rank"], errors="coerce")
    complete = bool(len(frame) and frame["complete"].astype(bool).all() and np.isfinite(scores).all())
    finite = scores[np.isfinite(scores)].to_numpy(float)
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
        "mean_presence_rank": mean,
        "sem_presence_rank": sem,
        "lower_evidence_bound": lower,
        "adequate": adequate,
        "n_folds": int(len(frame)),
    }


def _cross_validated_route(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    predictors: Sequence[str],
    model_spec: ModelSpec,
    *,
    n_splits: int,
    route_label: str,
    route_type: str,
    excluded_process: str = "",
) -> pd.DataFrame:
    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("group arrays must align with presence/background rows")
    groups = np.concatenate((p_groups, b_groups))
    unique_groups = np.unique(groups)
    if len(unique_groups) < int(n_splits):
        raise ValueError(
            f"n_splits={n_splits} exceeds available spatial groups={len(unique_groups)}"
        )

    n_presence = len(presence)
    indices = np.arange(n_presence + len(background))
    splitter = GroupKFold(n_splits=int(n_splits))
    rows: list[dict[str, object]] = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(indices, groups=groups)):
        p_train = train_idx[train_idx < n_presence]
        b_train = train_idx[train_idx >= n_presence] - n_presence
        p_test = test_idx[test_idx < n_presence]
        b_test = test_idx[test_idx >= n_presence] - n_presence
        complete = True
        score = float("nan")
        try:
            if min(len(p_train), len(b_train), len(p_test), len(b_test)) < 2:
                raise ValueError("fold lacks sufficient presence/background rows")
            model = fit_relative_suitability_model(
                presence.iloc[p_train],
                background.iloc[b_train],
                predictors,
                model_spec=model_spec,
            )
            p_scores = score_relative_suitability(model, presence.iloc[p_test], predictors)
            b_scores = score_relative_suitability(model, background.iloc[b_test], predictors)
            score = float(presence_rank_score(p_scores, b_scores))
            if not np.isfinite(score):
                complete = False
        except (ValueError, KeyError, np.linalg.LinAlgError):
            complete = False
        rows.append(
            {
                "route": route_label,
                "route_type": route_type,
                "excluded_process": excluded_process,
                "model_label": model_spec.label,
                "fold": int(fold),
                "complete": bool(complete),
                "presence_rank": score,
                "n_train_presence": int(len(p_train)),
                "n_train_background": int(len(b_train)),
                "n_test_presence": int(len(p_test)),
                "n_test_background": int(len(b_test)),
            }
        )
    return pd.DataFrame(rows)


def fit_ecological_identification_learner(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    *,
    predictors: Sequence[str],
    process_registry: pd.DataFrame,
    process_universe: Sequence[str],
    model_specs: Sequence[ModelSpec],
    n_splits: int = 4,
    chance_score: float = 0.50,
    minimum_margin: float = 0.01,
    sem_multiplier: float = 1.0,
    occurrence_split: OccurrenceAnswerCheckSplit | None = None,
    occurrence_id_col: str | None = None,
) -> IdentificationLearnerFit:
    """Learn an admissible model set and process certificate from model-pool data.

    Algorithm
    ---------
    1. Evaluate every predeclared model specification by grouped inner CV using
       the full ecological predictor set.
    2. Retain *all* model specifications that pass an absolute predictive
       adequacy gate; no single best model is selected.
    3. For every retained model specification and every declared process,
       remove the complete predeclared process-information closure and refit in
       the same inner folds.
    4. A process is refuted as necessary if at least one retained learner remains
       adequate without that process information; required only if all retained
       routes are complete and none remains adequate; otherwise unresolved.
    5. Refit every admitted baseline learner on the full model-pool data and use
       their mean prediction as the predictive output.

    The outer answer-check split, when supplied, is used only as a leakage guard.
    It is not opened or scored here.
    """

    predictor_tuple = _unique_strings(predictors, name="predictors")
    processes = _unique_strings(process_universe, name="process_universe")
    specs = _model_specs_by_label(model_specs)
    if not 0 <= chance_score < 1:
        raise ValueError("chance_score must lie in [0, 1)")
    if minimum_margin < 0 or chance_score + minimum_margin > 1:
        raise ValueError("minimum_margin produces an invalid adequacy floor")
    if sem_multiplier < 0:
        raise ValueError("sem_multiplier must be >= 0")
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")

    if occurrence_split is not None:
        occurrence_split.assert_model_pool_only(presence, id_col=occurrence_id_col)

    for predictor in predictor_tuple:
        if predictor not in presence.columns or predictor not in background.columns:
            raise KeyError(f"predictor absent from model-pool tables: {predictor}")

    knockout_registry = freeze_process_information_knockout_registry(
        base_candidates=tuple(specs),
        ecological_predictors=predictor_tuple,
        process_registry=process_registry,
        process_universe=processes,
    )

    evidence_frames: list[pd.DataFrame] = []
    baseline_rows: list[dict[str, object]] = []
    for label, spec in specs.items():
        route = f"baseline::{label}"
        fold = _cross_validated_route(
            presence,
            background,
            presence_groups,
            background_groups,
            predictor_tuple,
            spec,
            n_splits=n_splits,
            route_label=route,
            route_type="baseline",
        )
        evidence_frames.append(fold)
        summary = _summarize_route(
            fold,
            chance_score=chance_score,
            minimum_margin=minimum_margin,
            sem_multiplier=sem_multiplier,
        )
        baseline_rows.append({"model_label": label, "route": route, **summary})

    baseline_summary = pd.DataFrame(baseline_rows).sort_values("model_label").reset_index(drop=True)
    admitted = tuple(
        baseline_summary.loc[baseline_summary["adequate"].astype(bool), "model_label"].astype(str)
    )
    if not admitted:
        raise ValueError("no baseline learner passed the predictive adequacy gate")

    knockout_summaries: list[dict[str, object]] = []
    for row in knockout_registry.itertuples(index=False):
        if row.base_candidate not in admitted:
            continue
        retained = tuple(x for x in str(row.retained_ecological_predictors).split(",") if x)
        spec = specs[str(row.base_candidate)]
        fold = _cross_validated_route(
            presence,
            background,
            presence_groups,
            background_groups,
            retained,
            spec,
            n_splits=n_splits,
            route_label=str(row.candidate),
            route_type="process_knockout",
            excluded_process=str(row.excluded_process),
        )
        evidence_frames.append(fold)
        summary = _summarize_route(
            fold,
            chance_score=chance_score,
            minimum_margin=minimum_margin,
            sem_multiplier=sem_multiplier,
        )
        knockout_summaries.append(
            {
                "model_label": str(row.base_candidate),
                "excluded_process": str(row.excluded_process),
                "route": str(row.candidate),
                "retained_predictors": ",".join(retained),
                **summary,
            }
        )

    knockout_summary = pd.DataFrame(knockout_summaries)
    process_rows: list[dict[str, object]] = []
    for process in processes:
        group = knockout_summary.loc[knockout_summary["excluded_process"].eq(process)]
        adequate_routes = group.loc[group["adequate"].astype(bool), "route"].astype(str).tolist()
        n_expected = len(admitted)
        n_complete = int(group["complete"].astype(bool).sum()) if len(group) else 0
        if adequate_routes:
            status = "refuted_as_necessary"
        elif len(group) == n_expected and n_complete == n_expected:
            status = "required_by_evidence_contract"
        else:
            status = "unresolved"
        process_rows.append(
            {
                "process": process,
                "status": status,
                "n_admitted_baseline_models": int(n_expected),
                "n_complete_knockout_routes": int(n_complete),
                "n_adequate_knockout_routes": int(len(adequate_routes)),
                "adequate_witness_routes": ",".join(sorted(adequate_routes)),
            }
        )
    process_summary = pd.DataFrame(process_rows)

    fitted_models: list[tuple[str, object]] = []
    for label in admitted:
        model = fit_relative_suitability_model(
            presence,
            background,
            predictor_tuple,
            model_spec=specs[label],
        )
        fitted_models.append((label, model))

    receipt_payload = "\n".join(
        [
            "admitted=" + ",".join(admitted),
            "process=" + process_summary[["process", "status"]].to_csv(index=False),
            f"chance={chance_score:.12g}",
            f"floor={chance_score + minimum_margin:.12g}",
            f"sem={sem_multiplier:.12g}",
        ]
    ).encode("utf-8")
    receipt = hashlib.sha256(receipt_payload).hexdigest()

    return IdentificationLearnerFit(
        predictors=predictor_tuple,
        process_universe=processes,
        fold_evidence=pd.concat(evidence_frames, ignore_index=True),
        baseline_summary=baseline_summary,
        process_summary=process_summary,
        admissible_model_labels=admitted,
        fitted_models=tuple(fitted_models),
        selection_receipt=receipt,
        chance_score=float(chance_score),
        adequacy_floor=float(chance_score + minimum_margin),
        sem_multiplier=float(sem_multiplier),
    )
