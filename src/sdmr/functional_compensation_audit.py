"""Development-only functional-compensation evidence for process attribution.

The audit asks a different question from representation/carrier reconstruction.
For target process P and a coalition S of other processes, it compares the
held-out recovery of an S-only hard knockout with a P+S hard knockout.  A
material additional loss after adding P means that S had been functionally
compensating for P under the fitted SDM/evidence contract.

Coalitions are supplied independently of outcomes; this module never uses
known-truth labels or external biological labels.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations

import numpy as np
import pandas as pd

from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability
from .observation_aware_identification import _prepare_observation_corrections, _weighted_presence_rank


EVIDENCE_COLUMNS = (
    "target_process", "coalition_processes", "coalition_size", "model_label", "fold",
    "complete", "coalition_route_adequate",
    "coalition_presence_rank", "target_plus_coalition_presence_rank",
    "conditional_rank_loss", "coalition_density_log_score",
    "target_plus_coalition_density_log_score", "conditional_density_loss",
)


def enumerate_process_coalitions(process_universe: Sequence[str], target_process: str) -> tuple[tuple[str, ...], ...]:
    processes = tuple(str(x) for x in process_universe)
    target = str(target_process)
    others = tuple(x for x in processes if x != target)
    return tuple(c for size in range(1, len(others) + 1) for c in combinations(others, size))


def _union_closure(processes: Sequence[str], closures: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(p for process in processes for p in closures[str(process)]))


def _fold_indices(labels: np.ndarray, block: int) -> tuple[np.ndarray, np.ndarray]:
    return np.flatnonzero(labels != block), np.flatnonzero(labels == block)


def functional_compensation_evidence(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_blocks: Sequence[int],
    background_blocks: Sequence[int],
    *,
    target_process: str,
    coalition_processes: Sequence[str],
    closures: Mapping[str, Sequence[str]],
    ecological_predictors: Sequence[str],
    observation_predictors: Sequence[str] = (),
    model_specs: Sequence[ModelSpec],
    chance_score: float,
    minimum_margin: float,
    density_probability_epsilon: float = 1e-6,
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    minimum_test_presence: int = 3,
    minimum_test_background: int = 10,
) -> pd.DataFrame:
    """Return fold/spec evidence for P's conditional contribution given S disabled."""
    target = str(target_process)
    coalition = tuple(str(x) for x in coalition_processes)
    if not coalition or target in coalition:
        raise ValueError("coalition must be non-empty and exclude target_process")
    eco = tuple(str(x) for x in ecological_predictors)
    obs = tuple(str(x) for x in observation_predictors)
    specs = tuple(model_specs)
    if not specs:
        raise ValueError("model_specs must be non-empty")

    s_removed = set(_union_closure(coalition, closures))
    ps_removed = s_removed | set(closures[target])
    s_eco = tuple(x for x in eco if x not in s_removed)
    ps_eco = tuple(x for x in eco if x not in ps_removed)
    if not s_eco or not ps_eco:
        return pd.DataFrame(columns=EVIDENCE_COLUMNS)

    pblocks = np.asarray(presence_blocks)
    bblocks = np.asarray(background_blocks)
    if pblocks.shape != (len(presence),) or bblocks.shape != (len(background),):
        raise ValueError("block labels must align with rows")
    blocks = tuple(sorted(set(int(x) for x in np.unique(pblocks)) & set(int(x) for x in np.unique(bblocks))))
    folds = tuple((*_fold_indices(pblocks, block), *_fold_indices(bblocks, block)) for block in blocks)
    folds = tuple((pt, bt, pe, be) for pt, pe, bt, be in folds)
    corrections = _prepare_observation_corrections(
        presence, background, pblocks, bblocks, obs, folds,
        observation_signal_chance=float(observation_signal_chance),
        observation_signal_margin=float(observation_signal_margin),
        observation_signal_sem_multiplier=float(observation_signal_sem_multiplier),
        observation_weight_truncation_quantile=float(observation_weight_truncation_quantile),
        observation_weight_probability_epsilon=float(observation_weight_probability_epsilon),
    )
    floor = float(chance_score) + float(minimum_margin)
    rows: list[dict[str, object]] = []
    for fold_no, ((p_train, b_train, p_test, b_test), correction) in enumerate(zip(folds, corrections, strict=True)):
        for spec in specs:
            row = {
                "target_process": target,
                "coalition_processes": "+".join(coalition),
                "coalition_size": len(coalition),
                "model_label": spec.label,
                "fold": fold_no,
                "complete": False,
                "coalition_route_adequate": False,
                "coalition_presence_rank": np.nan,
                "target_plus_coalition_presence_rank": np.nan,
                "conditional_rank_loss": np.nan,
                "coalition_density_log_score": np.nan,
                "target_plus_coalition_density_log_score": np.nan,
                "conditional_density_loss": np.nan,
            }
            try:
                if not correction.complete:
                    raise ValueError("observation correction unavailable")
                if len(p_test) < int(minimum_test_presence) or len(b_test) < int(minimum_test_background):
                    raise ValueError("held-out fold too small")
                p_tr = presence.iloc[p_train].reset_index(drop=True)
                b_tr = background.iloc[b_train].reset_index(drop=True)
                p_te = presence.iloc[p_test].reset_index(drop=True)
                b_te = background.iloc[b_test].reset_index(drop=True)

                s_pred = s_eco + obs
                ps_pred = ps_eco + obs
                s_model = fit_relative_suitability_model(p_tr, b_tr, s_pred, model_spec=spec)
                ps_model = fit_relative_suitability_model(p_tr, b_tr, ps_pred, model_spec=spec)
                p_s = score_ecological_suitability(s_model, p_te, s_pred, observation_predictors=obs, observation_reference=b_tr)
                b_s = score_ecological_suitability(s_model, b_te, s_pred, observation_predictors=obs, observation_reference=b_tr)
                p_ps = score_ecological_suitability(ps_model, p_te, ps_pred, observation_predictors=obs, observation_reference=b_tr)
                b_ps = score_ecological_suitability(ps_model, b_te, ps_pred, observation_predictors=obs, observation_reference=b_tr)
                s_rank = _weighted_presence_rank(p_s, b_s, correction.weights)
                ps_rank = _weighted_presence_rank(p_ps, b_ps, correction.weights)
                s_den = balanced_density_ratio_log_score(p_s, b_s, presence_weights=correction.weights, probability_epsilon=float(density_probability_epsilon))
                ps_den = balanced_density_ratio_log_score(p_ps, b_ps, presence_weights=correction.weights, probability_epsilon=float(density_probability_epsilon))
                values = (s_rank, ps_rank, s_den, ps_den)
                if not all(np.isfinite(float(x)) for x in values):
                    raise ValueError("non-finite compensation evidence")
                row.update({
                    "complete": True,
                    "coalition_route_adequate": bool(float(s_rank) >= floor - 1e-12),
                    "coalition_presence_rank": float(s_rank),
                    "target_plus_coalition_presence_rank": float(ps_rank),
                    "conditional_rank_loss": float(s_rank - ps_rank),
                    "coalition_density_log_score": float(s_den),
                    "target_plus_coalition_density_log_score": float(ps_den),
                    "conditional_density_loss": float(s_den - ps_den),
                })
            except (ValueError, KeyError, np.linalg.LinAlgError):
                pass
            rows.append(row)
    return pd.DataFrame(rows, columns=EVIDENCE_COLUMNS)


def classify_functional_compensation(
    evidence: pd.DataFrame,
    *,
    expected_model_specs: int,
    rank_margin: float = 0.02,
    density_margin: float = 0.01,
    sem_multiplier: float = 1.0,
) -> dict[str, object]:
    """Average specs within fold; classify using folds as uncertainty units."""
    if evidence.empty:
        return {"state": "incomplete", "n_folds": 0}
    fold_rows = []
    for fold, group in evidence.groupby("fold", sort=True):
        complete = group.loc[group["complete"].astype(bool) & group["coalition_route_adequate"].astype(bool)]
        if len(complete) != int(expected_model_specs):
            continue
        fold_rows.append((
            int(fold),
            float(complete["conditional_rank_loss"].mean()),
            float(complete["conditional_density_loss"].mean()),
        ))
    if not fold_rows:
        return {"state": "incomplete", "n_folds": 0}
    rank = np.asarray([x[1] for x in fold_rows], dtype=float)
    density = np.asarray([x[2] for x in fold_rows], dtype=float)
    def mean_sem(x):
        return float(np.mean(x)), float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0
    rmean, rsem = mean_sem(rank); dmean, dsem = mean_sem(density)
    qualifies = (rmean - sem_multiplier * rsem > rank_margin) and (dmean - sem_multiplier * dsem > density_margin)
    return {
        "state": "functional_compensator" if qualifies else "no_revealed_compensation",
        "n_folds": len(fold_rows),
        "mean_conditional_rank_loss": rmean,
        "sem_conditional_rank_loss": rsem,
        "mean_conditional_density_loss": dmean,
        "sem_conditional_density_loss": dsem,
        "rank_margin": float(rank_margin),
        "density_margin": float(density_margin),
        "sem_multiplier": float(sem_multiplier),
    }
