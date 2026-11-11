"""Process-specific counterfactual ecological-recovery scoring.

For one case and one declared process, compare the best held-out ecological
niche overlap achievable by adequate candidates that carry the process with the
best overlap achievable when all declared representations of that process are
excluded.  The score is computed separately in each predeclared perturbation and
then averaged.  It uses no hidden process truth.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .known_truth_response import DEFAULT_PROCESS_ALIASES
from .niche_recovery_cv import RecoveryCandidate


def candidate_processes(
    candidate: RecoveryCandidate,
    *,
    process_aliases: Mapping[str, str] = DEFAULT_PROCESS_ALIASES,
) -> tuple[str, ...]:
    observation = set(candidate.observation_predictors)
    return tuple(
        sorted(
            {
                str(process_aliases.get(str(p), str(p)))
                for p in candidate.predictors
                if p not in observation
            }
        )
    )


def _adequate_candidate_overlap(
    metrics: pd.DataFrame,
    *,
    candidate_col: str = "candidate",
    auc_col: str = "presence_rank",
    overlap_col: str = "niche_overlap_schoener_d_pc12",
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> pd.DataFrame:
    required = {candidate_col, auc_col, overlap_col}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"counterfactual metrics missing columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for candidate, group in metrics.groupby(candidate_col, sort=True):
        auc = pd.to_numeric(group[auc_col], errors="coerce")
        auc = auc[np.isfinite(auc)]
        overlap = pd.to_numeric(group[overlap_col], errors="coerce")
        overlap = overlap[np.isfinite(overlap)]
        if not len(auc) or not len(overlap):
            continue
        mean_auc = float(auc.mean())
        sem_auc = float(auc.std(ddof=1) / np.sqrt(len(auc))) if len(auc) >= 2 else 0.0
        adequate = bool(
            mean_auc >= float(chance_auc + minimum_auc_margin) - 1e-12
            and mean_auc - float(auc_sem_multiplier) * sem_auc >= float(chance_auc) - 1e-12
        )
        if adequate:
            rows.append(
                {
                    "candidate": str(candidate),
                    "mean_auc": mean_auc,
                    "sem_auc": sem_auc,
                    "mean_overlap": float(overlap.mean()),
                }
            )
    return pd.DataFrame(rows)


def counterfactual_process_gap(
    metrics: pd.DataFrame,
    process: str,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    perturbation_col: str = "perturbation",
    process_aliases: Mapping[str, str] = DEFAULT_PROCESS_ALIASES,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> dict[str, object]:
    """Return one truth-free counterfactual recovery score for ``process``.

    Per perturbation, adequate candidates are split into those carrying the
    declared process and those that exclude every declared representation of it.
    The overlap gap is normalized by the overlap range of all adequate candidates.
    A missing adequate excluded class scores +1; a missing adequate containing
    class scores -1.  The case score is the arithmetic mean across available
    predeclared perturbations.
    """

    process = str(process)
    if perturbation_col not in metrics.columns:
        raise KeyError(f"missing perturbation column {perturbation_col!r}")
    process_by_candidate = {
        str(name): set(candidate_processes(candidate, process_aliases=process_aliases))
        for name, candidate in candidates.items()
    }
    rows: list[dict[str, object]] = []
    for perturbation, group in metrics.groupby(perturbation_col, sort=True):
        adequate = _adequate_candidate_overlap(
            group,
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
        )
        if adequate.empty:
            rows.append(
                {
                    "perturbation": str(perturbation),
                    "score": float("nan"),
                    "status": "no_adequate_candidate",
                    "n_adequate": 0,
                    "n_containing": 0,
                    "n_excluded": 0,
                }
            )
            continue
        containing = adequate.loc[
            adequate["candidate"].map(lambda name: process in process_by_candidate[str(name)])
        ]
        excluded = adequate.loc[
            adequate["candidate"].map(lambda name: process not in process_by_candidate[str(name)])
        ]
        if containing.empty and excluded.empty:
            score = float("nan")
            status = "no_comparable_class"
        elif containing.empty:
            score = -1.0
            status = "no_adequate_process_candidate"
        elif excluded.empty:
            score = 1.0
            status = "no_adequate_excluded_candidate"
        else:
            values = adequate["mean_overlap"].to_numpy(float)
            span = float(np.max(values) - np.min(values))
            if span <= 1e-12:
                score = 0.0
                status = "zero_overlap_range"
            else:
                score = float(
                    (containing["mean_overlap"].max() - excluded["mean_overlap"].max()) / span
                )
                status = "compared"
        rows.append(
            {
                "perturbation": str(perturbation),
                "score": score,
                "status": status,
                "n_adequate": int(len(adequate)),
                "n_containing": int(len(containing)),
                "n_excluded": int(len(excluded)),
                "best_containing_overlap": (
                    float(containing["mean_overlap"].max()) if len(containing) else float("nan")
                ),
                "best_excluded_overlap": (
                    float(excluded["mean_overlap"].max()) if len(excluded) else float("nan")
                ),
            }
        )
    per_perturbation = pd.DataFrame(rows)
    finite = pd.to_numeric(per_perturbation["score"], errors="coerce")
    finite = finite[np.isfinite(finite)]
    return {
        "process": process,
        "case_score": float(finite.mean()) if len(finite) else float("nan"),
        "n_scored_perturbations": int(len(finite)),
        "per_perturbation": per_perturbation,
    }


def classify_counterfactual_processes(
    metrics: pd.DataFrame,
    candidates: Mapping[str, RecoveryCandidate],
    thresholds: Mapping[str, float],
    *,
    processes: Sequence[str],
) -> tuple[tuple[str, ...], pd.DataFrame]:
    """Classify process membership using frozen counterfactual-score thresholds."""

    rows = []
    selected = []
    for process in tuple(str(x) for x in processes):
        if process not in thresholds:
            raise KeyError(f"missing frozen threshold for process {process!r}")
        result = counterfactual_process_gap(metrics, process, candidates)
        score = float(result["case_score"])
        threshold = float(thresholds[process])
        supported = bool(np.isfinite(score) and score >= threshold)
        if supported:
            selected.append(process)
        rows.append(
            {
                "process": process,
                "counterfactual_score": score,
                "threshold": threshold,
                "supported": supported,
                "n_scored_perturbations": int(result["n_scored_perturbations"]),
            }
        )
    return tuple(sorted(selected)), pd.DataFrame(rows)
