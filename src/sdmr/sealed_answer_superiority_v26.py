"""Prospectively frozen sealed-answer superiority separator (v26).

v26 is a successor to the failed v25 non-inferiority separator. It consumes
source-disjoint sealed answer-check evidence with the same fold schema, but a
supported process may be excluded only when removing its full information
closure is predictively superior for every required frozen model specification.
"""
from __future__ import annotations

from collections.abc import Sequence
import math

import numpy as np
import pandas as pd


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


def classify_sealed_answer_superiority(
    fold_evidence: pd.DataFrame,
    *,
    required_model_labels: Sequence[str],
    sem_multiplier: float = 1.96,
    minimum_complete_occurrences: int = 10,
    minimum_sealed_blocks: int = 2,
) -> pd.DataFrame:
    """Classify sealed full-closure knockout superiority evidence.

    ``delta`` is excluded minus baseline balanced density log score. Exclusion
    requires every required model specification to have a strictly positive
    lower ``sem_multiplier``-SEM bound. A strictly negative upper bound in any
    required model is compatibility evidence for retaining the process. Exact
    zero boundaries and overlapping intervals remain indeterminate.
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
    if not np.isfinite(float(sem_multiplier)) or float(sem_multiplier) < 0:
        raise ValueError("sem_multiplier must be a finite nonnegative number")
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
            raise ValueError("sealed answer evidence must be source-disjoint from support inputs")
        if not _as_bool(
            row.prediction_frozen_before_answer_open,
            name="prediction_frozen_before_answer_open",
        ):
            raise ValueError("separator prediction must be frozen before answer-check opening")

    rows: list[dict[str, object]] = []
    for key, group in data.groupby(list(CONTEXT_KEY), sort=True, dropna=False):
        family, seed, target_block, target_process = key
        required_set = set(model_labels)
        observed_models = set(group["model_label"].astype(str))

        fold_counts: list[tuple[int, int, int]] = []
        coverage_consistent = True
        for fold, fold_group in group.groupby("fold", sort=True):
            answer_values = pd.to_numeric(
                fold_group["n_answer_occurrences"], errors="coerce"
            ).to_numpy(float)
            background_values = pd.to_numeric(
                fold_group["n_separator_background"], errors="coerce"
            ).to_numpy(float)
            answer_unique = set(answer_values[np.isfinite(answer_values)].tolist())
            background_unique = set(
                background_values[np.isfinite(background_values)].tolist()
            )
            if len(answer_unique) != 1 or len(background_unique) != 1:
                coverage_consistent = False
                continue
            answer_n = int(next(iter(answer_unique)))
            background_n = int(next(iter(background_unique)))
            if answer_n < 1 or background_n < 1:
                coverage_consistent = False
            fold_counts.append((int(fold), answer_n, background_n))

        n_blocks = len(fold_counts)
        n_answer = int(sum(item[1] for item in fold_counts))
        coverage_ok = bool(
            coverage_consistent
            and n_blocks >= int(minimum_sealed_blocks)
            and n_answer >= int(minimum_complete_occurrences)
        )
        roster_ok = observed_models == required_set

        model_rows: list[dict[str, object]] = []
        all_complete = bool(coverage_ok and roster_ok)
        for label in model_labels:
            model_group = group.loc[group["model_label"].eq(label)].sort_values("fold")
            complete = bool(len(model_group) == n_blocks and n_blocks > 0)
            if complete:
                baseline_flags = [
                    _as_bool(value, name="baseline_complete")
                    for value in model_group["baseline_complete"]
                ]
                excluded_flags = [
                    _as_bool(value, name="excluded_complete")
                    for value in model_group["excluded_complete"]
                ]
                baseline = pd.to_numeric(
                    model_group["baseline_density_log_score"], errors="coerce"
                ).to_numpy(float)
                excluded = pd.to_numeric(
                    model_group["excluded_density_log_score"], errors="coerce"
                ).to_numpy(float)
                complete = bool(
                    all(baseline_flags)
                    and all(excluded_flags)
                    and np.isfinite(baseline).all()
                    and np.isfinite(excluded).all()
                )
            if not complete:
                all_complete = False
                model_rows.append(
                    {
                        "model_label": label,
                        "complete": False,
                        "mean_delta": math.nan,
                        "sem_delta": math.nan,
                        "lower_superiority": math.nan,
                        "upper_superiority": math.nan,
                        "superior": False,
                        "nonsuperior": False,
                    }
                )
                continue

            delta = excluded - baseline
            mean = float(np.mean(delta))
            sem = _sem(delta)
            lower = mean - float(sem_multiplier) * sem
            upper = mean + float(sem_multiplier) * sem
            model_rows.append(
                {
                    "model_label": label,
                    "complete": True,
                    "mean_delta": mean,
                    "sem_delta": sem,
                    "lower_superiority": lower,
                    "upper_superiority": upper,
                    "superior": bool(lower > 0.0),
                    "nonsuperior": bool(upper < 0.0),
                }
            )

        complete_models = [row for row in model_rows if bool(row["complete"])]
        n_superior = sum(bool(row["superior"]) for row in complete_models)
        n_nonsuperior = sum(bool(row["nonsuperior"]) for row in complete_models)

        if not all_complete:
            state = "unavailable"
        elif n_superior == len(model_labels):
            state = "exclude"
        elif n_nonsuperior > 0:
            state = "compatible"
        else:
            state = "indeterminate"

        finite_means = np.asarray(
            [
                float(row["mean_delta"])
                for row in complete_models
                if np.isfinite(float(row["mean_delta"]))
            ],
            dtype=float,
        )
        rows.append(
            {
                "family": str(family),
                "seed": int(seed),
                "target_block": int(target_block),
                "target_process": str(target_process),
                "separator_id": "sealed_answer_superiority_v26",
                "evidence_state": state,
                "qualified": bool(all_complete),
                "source_disjoint_from_v21_support_inputs": True,
                "decision_rule_frozen_before_separator_outcomes": True,
                "sem_multiplier": float(sem_multiplier),
                "superiority_boundary": 0.0,
                "n_required_models": len(model_labels),
                "n_complete_models": len(complete_models),
                "n_superior_models": int(n_superior),
                "n_nonsuperior_models": int(n_nonsuperior),
                "n_sealed_blocks": int(n_blocks),
                "n_answer_occurrences": int(n_answer),
                "mean_density_delta": (
                    float(np.mean(finite_means)) if len(finite_means) else math.nan
                ),
            }
        )

    return pd.DataFrame(rows)
