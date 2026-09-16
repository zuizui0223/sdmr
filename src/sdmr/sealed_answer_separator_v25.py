"""Sealed answer-check separator for v24 set refinement.

The separator consumes fold-level evidence whose outcome rows come from a
spatially sealed occurrence answer-check source.  It does not refine v23 sets
itself; it emits one of the four evidence states accepted by v24.
"""
from __future__ import annotations

from collections.abc import Sequence
import hashlib
import math

import numpy as np
import pandas as pd

from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_ecological_suitability,
)
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit
from .validation import assign_spatial_blocks, make_presence_spatial_partition


EVIDENCE_STATES = ("exclude", "compatible", "indeterminate", "unavailable")
CONTEXT_KEY = ("family", "seed", "target_block", "target_process")


def _as_bool(value: object, *, name: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and int(value) in (0, 1):
        return bool(int(value))
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    raise ValueError(f"{name} must be boolean")


def _sem(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0 if len(values) == 1 else float("nan")
    return float(np.std(values, ddof=1) / np.sqrt(len(values)))


def _coordinate_keys(frame: pd.DataFrame) -> set[tuple[float, float]]:
    required = {"longitude", "latitude"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError("frame missing coordinates: " + ", ".join(missing))
    lon = pd.to_numeric(frame["longitude"], errors="raise").to_numpy(float)
    lat = pd.to_numeric(frame["latitude"], errors="raise").to_numpy(float)
    if not np.isfinite(lon).all() or not np.isfinite(lat).all():
        raise ValueError("coordinates must be finite")
    # Twelve decimals is finer than the coordinate precision used by SDMR while
    # making exact source reuse fail closed despite CSV float round-trips.
    return set(zip(np.round(lon, 12), np.round(lat, 12), strict=True))


def _hash_frame(frame: pd.DataFrame, columns: Sequence[str]) -> bytes:
    cols = tuple(str(x) for x in columns)
    missing = sorted(set(cols) - set(frame.columns))
    if missing:
        raise KeyError("receipt frame missing columns: " + ", ".join(missing))
    canonical = frame[list(cols)].copy()
    for col in cols:
        canonical[col] = pd.to_numeric(canonical[col], errors="raise")
    canonical = canonical.sort_values(list(cols), kind="mergesort").reset_index(drop=True)
    return canonical.to_csv(index=False, float_format="%.12g").encode("utf-8")


def _prediction_receipt(
    *,
    upstream_receipt: str,
    split_digest: str,
    target_process: str,
    baseline_predictors: Sequence[str],
    excluded_predictors: Sequence[str],
    model_specs: Sequence[ModelSpec],
    model_pool: pd.DataFrame,
    support_background: pd.DataFrame,
) -> str:
    hasher = hashlib.sha256()
    for value in (
        str(upstream_receipt),
        str(split_digest),
        str(target_process),
        ",".join(str(x) for x in baseline_predictors),
        ",".join(str(x) for x in excluded_predictors),
        ",".join(str(x.label) for x in model_specs),
    ):
        hasher.update(value.encode("utf-8"))
        hasher.update(b"\0")
    hasher.update(_hash_frame(model_pool, baseline_predictors))
    hasher.update(b"\0")
    hasher.update(_hash_frame(support_background, baseline_predictors))
    return hasher.hexdigest()


def _fit_route_models(
    model_pool: pd.DataFrame,
    support_background: pd.DataFrame,
    *,
    baseline_predictors: tuple[str, ...],
    excluded_predictors: tuple[str, ...],
    model_specs: tuple[ModelSpec, ...],
) -> dict[str, tuple[object | None, object | None]]:
    fitted: dict[str, tuple[object | None, object | None]] = {}
    for spec in model_specs:
        baseline_model = excluded_model = None
        try:
            baseline_model = fit_relative_suitability_model(
                model_pool,
                support_background,
                baseline_predictors,
                model_spec=spec,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        try:
            excluded_model = fit_relative_suitability_model(
                model_pool,
                support_background,
                excluded_predictors,
                model_spec=spec,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        fitted[spec.label] = (baseline_model, excluded_model)
    return fitted


def _ecological_scores(
    model: object,
    frame: pd.DataFrame,
    predictors: tuple[str, ...],
    *,
    observation_predictors: tuple[str, ...],
    support_background: pd.DataFrame,
) -> np.ndarray:
    return score_ecological_suitability(
        model,
        frame,
        predictors,
        observation_predictors=observation_predictors,
        observation_reference=(support_background if observation_predictors else None),
    )


def build_sealed_answer_fold_evidence(
    occurrences: pd.DataFrame,
    support_background: pd.DataFrame,
    separator_background: pd.DataFrame,
    *,
    occurrence_split: OccurrenceAnswerCheckSplit,
    family: str,
    seed: int,
    target_block: int,
    target_process: str,
    process_registry: pd.DataFrame,
    ecological_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    model_specs: Sequence[ModelSpec],
    selection_receipt: str,
    outer_n_blocks: int,
    outer_holdout_fraction: float,
    outer_random_state: int,
    occurrence_id_col: str = "occurrence_id",
    probability_epsilon: float = 1e-6,
) -> pd.DataFrame:
    """Build fold evidence on answer-check outcomes not used by v21 support.

    Baseline and process-excluded models are fitted on the model-pool occurrence
    rows and the original support background first.  Only after those fits and a
    deterministic prediction receipt are frozen are the answer-check occurrence
    rows opened.  Separator background rows must be coordinate-disjoint from all
    v21 occurrence/support-background rows and are used only to score the sealed
    presence/background density-ratio contrast.
    """
    upstream_receipt = str(selection_receipt).strip()
    if not upstream_receipt:
        raise ValueError("selection_receipt must be non-empty before answer-check opening")
    if not 0.0 < float(probability_epsilon) < 0.5:
        raise ValueError("probability_epsilon must lie in (0, 0.5)")

    ecological = tuple(dict.fromkeys(str(x) for x in ecological_predictors))
    observation = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    specs = tuple(model_specs)
    if not ecological:
        raise ValueError("ecological_predictors must be non-empty")
    if not specs or len({x.label for x in specs}) != len(specs):
        raise ValueError("model_specs must be a nonempty unique roster")
    if set(ecological) & set(observation):
        raise ValueError("ecological and observation predictor roles must be disjoint")

    registry_required = {"predictor", "process", "role"}
    missing_registry = sorted(registry_required - set(process_registry.columns))
    if missing_registry:
        raise KeyError("process registry missing columns: " + ", ".join(missing_registry))
    closure = tuple(
        dict.fromkeys(
            process_registry.loc[
                process_registry["process"].astype(str).eq(str(target_process)), "predictor"
            ].astype(str)
        )
    )
    if not closure:
        raise ValueError(f"target process has no declared information closure: {target_process}")
    closure_set = set(closure)
    unknown_closure = sorted(closure_set - set(ecological))
    if unknown_closure:
        raise ValueError("process closure is outside ecological predictors: " + ", ".join(unknown_closure))

    baseline_predictors = tuple(ecological) + tuple(observation)
    excluded_ecological = tuple(x for x in ecological if x not in closure_set)
    excluded_predictors = excluded_ecological + tuple(observation)
    if not excluded_ecological:
        raise ValueError("process exclusion leaves no ecological predictors")

    required_inputs = set(baseline_predictors) | {"longitude", "latitude"}
    if occurrence_id_col not in occurrences.columns:
        raise KeyError(f"occurrences missing identity column: {occurrence_id_col}")
    for label, frame in (
        ("occurrences", occurrences),
        ("support_background", support_background),
        ("separator_background", separator_background),
    ):
        missing = sorted(required_inputs - set(frame.columns))
        if missing:
            raise KeyError(f"{label} missing columns: {missing}")

    separator_coords = _coordinate_keys(separator_background)
    used_coords = _coordinate_keys(occurrences) | _coordinate_keys(support_background)
    if separator_coords & used_coords:
        raise ValueError("separator background must be source-disjoint from v21 occurrence/background rows")

    model_pool = occurrence_split.model_pool(occurrences, id_col=occurrence_id_col)

    # Fit every route before answer-check rows can be materialized.  The fitted
    # models may use upstream model-pool evidence; the *separator outcome source*
    # is independent and remains unopened until the receipt below exists.
    fitted = _fit_route_models(
        model_pool,
        support_background,
        baseline_predictors=baseline_predictors,
        excluded_predictors=excluded_predictors,
        model_specs=specs,
    )
    prediction_receipt = _prediction_receipt(
        upstream_receipt=upstream_receipt,
        split_digest=occurrence_split.split_digest,
        target_process=str(target_process),
        baseline_predictors=baseline_predictors,
        excluded_predictors=excluded_predictors,
        model_specs=specs,
        model_pool=model_pool,
        support_background=support_background,
    )

    answer = occurrence_split.open_answer_check(
        occurrences,
        selection_receipt=prediction_receipt,
        id_col=occurrence_id_col,
    )

    # Reconstruct the occurrence-derived spatial centers and verify exact parity
    # with the split frozen before environmental feature use.
    canonical_occ = occurrences.sort_values(occurrence_id_col, kind="mergesort").reset_index(drop=True)
    partition = make_presence_spatial_partition(
        pd.to_numeric(canonical_occ["longitude"], errors="raise").to_numpy(float),
        pd.to_numeric(canonical_occ["latitude"], errors="raise").to_numpy(float),
        n_blocks=int(outer_n_blocks),
        holdout_fraction=float(outer_holdout_fraction),
        random_state=int(outer_random_state),
    )
    reconstructed = pd.DataFrame(
        {
            occurrence_id_col: canonical_occ[occurrence_id_col].astype(str).to_numpy(),
            "reconstructed_block": partition.presence_blocks.astype(int),
        }
    )
    frozen_assignment = occurrence_split.assignment[[occurrence_id_col, "spatial_block"]].copy()
    frozen_assignment[occurrence_id_col] = frozen_assignment[occurrence_id_col].astype(str)
    parity = frozen_assignment.merge(reconstructed, on=occurrence_id_col, how="outer", validate="one_to_one")
    if len(parity) != len(frozen_assignment) or not (
        pd.to_numeric(parity["spatial_block"], errors="coerce")
        .eq(pd.to_numeric(parity["reconstructed_block"], errors="coerce"))
        .all()
    ):
        raise ValueError("outer spatial partition does not reproduce frozen occurrence split")

    answer_assignment = occurrence_split.assignment[[occurrence_id_col, "spatial_block", "outer_role"]].copy()
    answer_assignment[occurrence_id_col] = answer_assignment[occurrence_id_col].astype(str)
    answer = answer.copy()
    answer[occurrence_id_col] = answer[occurrence_id_col].astype(str)
    answer = answer.merge(answer_assignment, on=occurrence_id_col, how="left", validate="one_to_one")
    if answer["spatial_block"].isna().any():
        raise ValueError("answer-check rows lack frozen spatial block")

    separator = separator_background.copy().reset_index(drop=True)
    separator["spatial_block"] = assign_spatial_blocks(
        pd.to_numeric(separator["longitude"], errors="raise").to_numpy(float),
        pd.to_numeric(separator["latitude"], errors="raise").to_numpy(float),
        partition.centers_xyz,
    )

    rows: list[dict[str, object]] = []
    answer_blocks = sorted(int(x) for x in answer["spatial_block"].unique())
    for block in answer_blocks:
        p_eval = answer.loc[answer["spatial_block"].eq(block)].reset_index(drop=True)
        b_eval = separator.loc[separator["spatial_block"].eq(block)].reset_index(drop=True)
        for spec in specs:
            baseline_model, excluded_model = fitted[spec.label]
            row = {
                "family": str(family),
                "seed": int(seed),
                "target_block": int(target_block),
                "target_process": str(target_process),
                "model_label": str(spec.label),
                "fold": int(block),
                "baseline_complete": False,
                "excluded_complete": False,
                "baseline_density_log_score": float("nan"),
                "excluded_density_log_score": float("nan"),
                "n_answer_occurrences": int(len(p_eval)),
                "n_separator_background": int(len(b_eval)),
                "sealed_answer_source_disjoint": True,
                "prediction_frozen_before_answer_open": True,
                "prediction_receipt": prediction_receipt,
                "baseline_predictors": ",".join(baseline_predictors),
                "excluded_predictors": ",".join(excluded_predictors),
            }
            if baseline_model is not None and len(p_eval) >= 2 and len(b_eval) >= 2:
                p_scores = _ecological_scores(
                    baseline_model,
                    p_eval,
                    baseline_predictors,
                    observation_predictors=observation,
                    support_background=support_background,
                )
                b_scores = _ecological_scores(
                    baseline_model,
                    b_eval,
                    baseline_predictors,
                    observation_predictors=observation,
                    support_background=support_background,
                )
                baseline_score = balanced_density_ratio_log_score(
                    p_scores,
                    b_scores,
                    probability_epsilon=float(probability_epsilon),
                )
                if np.isfinite(baseline_score):
                    row["baseline_complete"] = True
                    row["baseline_density_log_score"] = float(baseline_score)
            if excluded_model is not None and len(p_eval) >= 2 and len(b_eval) >= 2:
                p_scores = _ecological_scores(
                    excluded_model,
                    p_eval,
                    excluded_predictors,
                    observation_predictors=observation,
                    support_background=support_background,
                )
                b_scores = _ecological_scores(
                    excluded_model,
                    b_eval,
                    excluded_predictors,
                    observation_predictors=observation,
                    support_background=support_background,
                )
                excluded_score = balanced_density_ratio_log_score(
                    p_scores,
                    b_scores,
                    probability_epsilon=float(probability_epsilon),
                )
                if np.isfinite(excluded_score):
                    row["excluded_complete"] = True
                    row["excluded_density_log_score"] = float(excluded_score)
            rows.append(row)
    return pd.DataFrame(rows)


def classify_sealed_answer_separator(
    fold_evidence: pd.DataFrame,
    *,
    required_model_labels: Sequence[str],
    margin: float = 0.01,
    sem_multiplier: float = 1.0,
    minimum_complete_occurrences: int = 10,
    minimum_sealed_blocks: int = 2,
) -> pd.DataFrame:
    """Classify source-disjoint sealed process-exclusion evidence.

    For each required model specification and sealed spatial block,
    ``delta = excluded_density_log_score - baseline_density_log_score``.
    Process exclusion is non-inferior for a model only when its lower
    one-SEM bound is at least ``-margin``.  A process is excluded only when
    every required model is complete and non-inferior.  A clearly inferior
    exclusion in any required model is positive compatibility evidence for
    retaining the process.  Overlapping intervals remain indeterminate.
    """
    required_columns = {
        *CONTEXT_KEY,
        "model_label",
        "fold",
        "baseline_complete",
        "excluded_complete",
        "baseline_density_log_score",
        "excluded_density_log_score",
        "n_answer_occurrences",
        "n_separator_background",
        "sealed_answer_source_disjoint",
        "prediction_frozen_before_answer_open",
    }
    missing = sorted(required_columns - set(fold_evidence.columns))
    if missing:
        raise KeyError("sealed answer evidence missing columns: " + ", ".join(missing))

    model_labels = tuple(str(x) for x in required_model_labels)
    if not model_labels or len(set(model_labels)) != len(model_labels):
        raise ValueError("required_model_labels must be a nonempty unique sequence")
    if float(margin) < 0 or float(sem_multiplier) < 0:
        raise ValueError("margin and sem_multiplier must be nonnegative")
    if int(minimum_complete_occurrences) < 1:
        raise ValueError("minimum_complete_occurrences must be >= 1")
    if int(minimum_sealed_blocks) < 2:
        raise ValueError("minimum_sealed_blocks must be >= 2")

    data = fold_evidence.copy()
    data["family"] = data["family"].astype(str)
    data["seed"] = pd.to_numeric(data["seed"], errors="raise").astype(int)
    data["target_block"] = pd.to_numeric(data["target_block"], errors="raise").astype(int)
    data["target_process"] = data["target_process"].astype(str)
    data["model_label"] = data["model_label"].astype(str)
    data["fold"] = pd.to_numeric(data["fold"], errors="raise").astype(int)

    duplicate_key = list(CONTEXT_KEY) + ["model_label", "fold"]
    if data.duplicated(duplicate_key).any():
        raise ValueError("duplicate context-model-fold evidence key")

    for row in data.itertuples(index=False):
        if not _as_bool(
            row.sealed_answer_source_disjoint,
            name="sealed_answer_source_disjoint",
        ):
            raise ValueError("sealed answer evidence must be source-disjoint from v21 support")
        if not _as_bool(
            row.prediction_frozen_before_answer_open,
            name="prediction_frozen_before_answer_open",
        ):
            raise ValueError("separator prediction must be frozen before answer-check opening")

    rows: list[dict[str, object]] = []
    for key, group in data.groupby(list(CONTEXT_KEY), sort=True, dropna=False):
        family, seed, target_block, target_process = key
        observed_models = set(group["model_label"].astype(str))
        required_set = set(model_labels)

        fold_counts = []
        coverage_consistent = True
        for fold, fg in group.groupby("fold", sort=True):
            answer_counts = set(pd.to_numeric(fg["n_answer_occurrences"], errors="coerce").tolist())
            background_counts = set(pd.to_numeric(fg["n_separator_background"], errors="coerce").tolist())
            if len(answer_counts) != 1 or len(background_counts) != 1:
                coverage_consistent = False
                continue
            answer_n = int(next(iter(answer_counts)))
            background_n = int(next(iter(background_counts)))
            if answer_n < 1 or background_n < 1:
                coverage_consistent = False
            fold_counts.append((int(fold), answer_n, background_n))

        n_blocks = len(fold_counts)
        n_answer = int(sum(x[1] for x in fold_counts))
        coverage_ok = bool(
            coverage_consistent
            and n_blocks >= int(minimum_sealed_blocks)
            and n_answer >= int(minimum_complete_occurrences)
        )
        roster_ok = observed_models == required_set

        model_rows: list[dict[str, object]] = []
        all_complete = bool(coverage_ok and roster_ok)
        for label in model_labels:
            mg = group.loc[group["model_label"].eq(label)].sort_values("fold")
            complete = bool(len(mg) == n_blocks and n_blocks > 0)
            if complete:
                baseline_complete = [
                    _as_bool(x, name="baseline_complete") for x in mg["baseline_complete"]
                ]
                excluded_complete = [
                    _as_bool(x, name="excluded_complete") for x in mg["excluded_complete"]
                ]
                baseline = pd.to_numeric(mg["baseline_density_log_score"], errors="coerce").to_numpy(float)
                excluded = pd.to_numeric(mg["excluded_density_log_score"], errors="coerce").to_numpy(float)
                complete = bool(
                    all(baseline_complete)
                    and all(excluded_complete)
                    and np.isfinite(baseline).all()
                    and np.isfinite(excluded).all()
                )
            if not complete:
                all_complete = False
                model_rows.append(
                    {
                        "model_label": label,
                        "complete": False,
                        "mean_delta": float("nan"),
                        "sem_delta": float("nan"),
                        "lower_delta": float("nan"),
                        "upper_delta": float("nan"),
                        "noninferior": False,
                        "clearly_inferior": False,
                    }
                )
                continue

            delta = excluded - baseline
            mean = float(np.mean(delta))
            sem = _sem(delta)
            lower = mean - float(sem_multiplier) * sem
            upper = mean + float(sem_multiplier) * sem
            noninferior = bool(lower >= -float(margin) - 1e-12)
            clearly_inferior = bool(upper < -float(margin) - 1e-12)
            model_rows.append(
                {
                    "model_label": label,
                    "complete": True,
                    "mean_delta": mean,
                    "sem_delta": sem,
                    "lower_delta": lower,
                    "upper_delta": upper,
                    "noninferior": noninferior,
                    "clearly_inferior": clearly_inferior,
                }
            )

        complete_models = [x for x in model_rows if bool(x["complete"])]
        n_noninferior = sum(bool(x["noninferior"]) for x in complete_models)
        n_inferior = sum(bool(x["clearly_inferior"]) for x in complete_models)

        if not all_complete:
            state = "unavailable"
        elif n_noninferior == len(model_labels):
            state = "exclude"
        elif n_inferior > 0:
            state = "compatible"
        else:
            state = "indeterminate"

        finite_means = np.asarray(
            [float(x["mean_delta"]) for x in complete_models if np.isfinite(float(x["mean_delta"]))],
            dtype=float,
        )
        rows.append(
            {
                "family": str(family),
                "seed": int(seed),
                "target_block": int(target_block),
                "target_process": str(target_process),
                "separator_id": "sealed_answer_process_exclusion_v25",
                "evidence_state": state,
                "qualified": bool(all_complete),
                "source_disjoint_from_v21_support_inputs": True,
                "decision_rule_frozen_before_separator_outcomes": True,
                "n_required_models": len(model_labels),
                "n_complete_models": len(complete_models),
                "n_noninferior_models": int(n_noninferior),
                "n_clearly_inferior_models": int(n_inferior),
                "n_sealed_blocks": int(n_blocks),
                "n_answer_occurrences": int(n_answer),
                "mean_density_delta": (
                    float(np.mean(finite_means)) if len(finite_means) else math.nan
                ),
            }
        )

    return pd.DataFrame(rows)
