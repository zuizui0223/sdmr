"""Sealed answer-check separator for v24 set refinement.

The separator consumes fold-level evidence whose outcome rows come from a
spatially sealed occurrence answer-check source.  It does not refine v23 sets
itself; it emits one of the four evidence states accepted by v24.
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

        # Coverage is an outcome-source property, not multiplied by the number
        # of model specifications.  Counts must therefore agree within a fold.
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
