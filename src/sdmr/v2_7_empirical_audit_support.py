"""Partition-aware empirical audit support for Product-A v2.7 development.

Product-A candidate procedures may still consider the full predeclared CHELSA
predictor universe.  The ecological audit geometry is a separate object: it must
be candidate-independent, selected from model-pool availability only, and have
enough complete environmental rows in every predeclared outer spatial fold for
the niche-recovery metrics to be mathematically defined.

This module starts from :func:`select_empirical_audit_space`, then applies only
missingness-based fold support pruning.  It never reads candidate scores,
response magnitudes, knockout outcomes, or outer sealed rows.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .empirical_audit_space import EmpiricalAuditSpace, select_empirical_audit_space
from .validation import SpatialPartition


@dataclass(frozen=True)
class PartitionAwareEmpiricalAuditSpace:
    predictors: tuple[str, ...]
    processes: tuple[str, ...]
    initial_predictors: tuple[str, ...]
    initial_processes: tuple[str, ...]
    minimum_predictor_coverage: float
    minimum_joint_coverage: float
    minimum_processes: int
    minimum_fit_background_rows: int
    minimum_evaluation_background_rows: int
    minimum_heldout_occurrence_rows: int
    support_ledger: pd.DataFrame
    pruning_ledger: pd.DataFrame
    base_audit_ledger: pd.DataFrame


def _complete_count(frame: pd.DataFrame, predictors: Sequence[str]) -> int:
    cols = tuple(str(x) for x in predictors)
    if not cols or len(frame) == 0:
        return 0
    if any(col not in frame.columns for col in cols):
        return 0
    matrix = frame.loc[:, cols].apply(pd.to_numeric, errors="coerce")
    return int(matrix.notna().all(axis=1).sum())


def _joint_coverage(frame: pd.DataFrame, predictors: Sequence[str]) -> float:
    if len(frame) == 0:
        return 0.0
    return float(_complete_count(frame, predictors) / len(frame))


def audit_support_ledger(
    occurrence: pd.DataFrame,
    backgrounds: Mapping[str, pd.DataFrame],
    partitions: Mapping[str, SpatialPartition],
    predictors: Sequence[str],
    *,
    outer_folds: int,
    minimum_fit_background_rows: int = 5,
    minimum_evaluation_background_rows: int = 5,
    minimum_heldout_occurrence_rows: int = 2,
) -> pd.DataFrame:
    """Return candidate-independent complete-row support for every M × fold.

    The row minima come directly from
    ``observation_corrected_heldout_niche_recovery_profile``: at least five
    complete audit rows in the fit background, five in the evaluation
    background, and two in the held-out occurrence fold.
    """

    predictors = tuple(dict.fromkeys(str(x) for x in predictors))
    if not predictors:
        raise ValueError("partition-aware audit support requires predictors")
    if int(outer_folds) < 2:
        raise ValueError("outer_folds must be >= 2")
    for value, name in (
        (minimum_fit_background_rows, "minimum_fit_background_rows"),
        (minimum_evaluation_background_rows, "minimum_evaluation_background_rows"),
        (minimum_heldout_occurrence_rows, "minimum_heldout_occurrence_rows"),
    ):
        if int(value) < 1:
            raise ValueError(f"{name} must be >= 1")

    p = occurrence.reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for m_name in sorted(str(x) for x in backgrounds):
        if m_name not in partitions:
            raise KeyError(f"audit support partition missing M: {m_name}")
        b = backgrounds[m_name].reset_index(drop=True)
        partition = partitions[m_name]
        p_groups = np.asarray(partition.presence_blocks)
        b_groups = np.asarray(partition.background_blocks)
        if len(p_groups) != len(p) or len(b_groups) != len(b):
            raise ValueError(f"audit support partition does not align in {m_name}")
        folds = min(int(outer_folds), len(np.unique(p_groups)))
        if folds != int(outer_folds):
            raise ValueError(
                f"requested audit-support folds unavailable in {m_name}: "
                f"requested={outer_folds} available={folds}"
            )
        splitter = GroupKFold(n_splits=folds)
        dummy = np.zeros(len(p), dtype=int)
        for fold, (train_idx, test_idx) in enumerate(splitter.split(dummy, groups=p_groups)):
            train_blocks = np.unique(p_groups[train_idx])
            test_blocks = np.unique(p_groups[test_idx])
            bg_train_mask = np.isin(b_groups, train_blocks)
            bg_test_mask = np.isin(b_groups, test_blocks)
            p_test = p.iloc[test_idx]
            b_train = b.loc[bg_train_mask]
            b_test = b.loc[bg_test_mask]
            fit_n = _complete_count(b_train, predictors)
            eval_n = _complete_count(b_test, predictors)
            heldout_n = _complete_count(p_test, predictors)
            fit_ok = fit_n >= int(minimum_fit_background_rows)
            eval_ok = eval_n >= int(minimum_evaluation_background_rows)
            heldout_ok = heldout_n >= int(minimum_heldout_occurrence_rows)
            rows.append(
                {
                    "M": m_name,
                    "fold": int(fold),
                    "n_fit_background": int(len(b_train)),
                    "n_evaluation_background": int(len(b_test)),
                    "n_heldout_occurrences": int(len(p_test)),
                    "n_complete_fit_background": fit_n,
                    "n_complete_evaluation_background": eval_n,
                    "n_complete_heldout_occurrences": heldout_n,
                    "fit_background_supported": bool(fit_ok),
                    "evaluation_background_supported": bool(eval_ok),
                    "heldout_occurrence_supported": bool(heldout_ok),
                    "audit_support_complete": bool(fit_ok and eval_ok and heldout_ok),
                    "predictors": ",".join(predictors),
                }
            )
    ledger = pd.DataFrame(rows)
    expected = len(backgrounds) * int(outer_folds)
    if len(ledger) != expected:
        raise AssertionError(
            f"audit support ledger expected {expected} M-fold cells, found {len(ledger)}"
        )
    return ledger


def _minimum_support_ratio(
    ledger: pd.DataFrame,
    *,
    minimum_fit_background_rows: int,
    minimum_evaluation_background_rows: int,
    minimum_heldout_occurrence_rows: int,
) -> float:
    if ledger.empty:
        return 0.0
    ratios = np.column_stack(
        [
            pd.to_numeric(ledger["n_complete_fit_background"], errors="coerce").to_numpy(float)
            / float(minimum_fit_background_rows),
            pd.to_numeric(ledger["n_complete_evaluation_background"], errors="coerce").to_numpy(float)
            / float(minimum_evaluation_background_rows),
            pd.to_numeric(ledger["n_complete_heldout_occurrences"], errors="coerce").to_numpy(float)
            / float(minimum_heldout_occurrence_rows),
        ]
    )
    finite = ratios[np.isfinite(ratios)]
    return float(finite.min()) if finite.size else 0.0


def select_partition_aware_empirical_audit_space(
    manifest: pd.DataFrame,
    occurrence: pd.DataFrame,
    backgrounds: Mapping[str, pd.DataFrame],
    partitions: Mapping[str, SpatialPartition],
    *,
    outer_folds: int,
    minimum_predictor_coverage: float = 0.95,
    minimum_joint_coverage: float = 0.80,
    minimum_processes: int = 4,
    minimum_fit_background_rows: int = 5,
    minimum_evaluation_background_rows: int = 5,
    minimum_heldout_occurrence_rows: int = 2,
) -> PartitionAwareEmpiricalAuditSpace:
    """Freeze a process-representative audit space before candidate benchmarking.

    Stage 1 reuses the existing model-pool-only empirical audit-space selector.
    Stage 2 checks the exact outer spatial partitions.  If a selected process axis
    causes mathematically insufficient complete rows in any M × fold, whole
    process axes are deterministically pruned down to the predeclared minimum.
    The pruning objective uses only complete-row counts and model-pool joint
    coverage; candidate metrics are not an input.
    """

    if int(minimum_processes) < 1:
        raise ValueError("minimum_processes must be >= 1")
    if not backgrounds:
        raise ValueError("partition-aware audit selection requires backgrounds")
    model_pool_frames = [occurrence, *[backgrounds[name] for name in sorted(backgrounds)]]
    base: EmpiricalAuditSpace = select_empirical_audit_space(
        manifest,
        model_pool_frames,
        minimum_predictor_coverage=float(minimum_predictor_coverage),
        minimum_joint_coverage=float(minimum_joint_coverage),
        minimum_processes=int(minimum_processes),
    )
    selected = list(base.predictors)
    process_by_predictor = {
        str(row.representative_predictor): str(row.process)
        for row in base.ledger.loc[base.ledger["selected"].astype(bool)].itertuples(index=False)
    }
    if set(selected) - set(process_by_predictor):
        raise AssertionError("selected audit predictor lacks process identity")

    pruning_rows: list[dict[str, object]] = []
    iteration = 0
    while True:
        support = audit_support_ledger(
            occurrence,
            backgrounds,
            partitions,
            selected,
            outer_folds=int(outer_folds),
            minimum_fit_background_rows=int(minimum_fit_background_rows),
            minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
            minimum_heldout_occurrence_rows=int(minimum_heldout_occurrence_rows),
        )
        all_supported = bool(support["audit_support_complete"].astype(bool).all())
        pruning_rows.append(
            {
                "iteration": int(iteration),
                "action": "accept" if all_supported else "evaluate_pruning",
                "removed_predictor": None,
                "removed_process": None,
                "n_processes": len(selected),
                "n_supported_M_fold_cells": int(support["audit_support_complete"].sum()),
                "n_total_M_fold_cells": len(support),
                "minimum_support_ratio": _minimum_support_ratio(
                    support,
                    minimum_fit_background_rows=int(minimum_fit_background_rows),
                    minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
                    minimum_heldout_occurrence_rows=int(minimum_heldout_occurrence_rows),
                ),
                "predictors": ",".join(selected),
            }
        )
        if all_supported:
            break
        if len(selected) <= int(minimum_processes):
            failing = support.loc[~support["audit_support_complete"].astype(bool)]
            raise ValueError(
                "partition-aware model-pool availability cannot support the minimum "
                f"{minimum_processes} ecological audit processes; failing_cells="
                + ";".join(f"{row.M}:fold{row.fold}" for row in failing.itertuples(index=False))
            )

        trials: list[tuple[tuple[float, float, float, str], str, pd.DataFrame]] = []
        for predictor in selected:
            trial_predictors = [x for x in selected if x != predictor]
            trial_support = audit_support_ledger(
                occurrence,
                backgrounds,
                partitions,
                trial_predictors,
                outer_folds=int(outer_folds),
                minimum_fit_background_rows=int(minimum_fit_background_rows),
                minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
                minimum_heldout_occurrence_rows=int(minimum_heldout_occurrence_rows),
            )
            n_supported = float(trial_support["audit_support_complete"].sum())
            min_ratio = _minimum_support_ratio(
                trial_support,
                minimum_fit_background_rows=int(minimum_fit_background_rows),
                minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
                minimum_heldout_occurrence_rows=int(minimum_heldout_occurrence_rows),
            )
            min_joint = float(
                min(_joint_coverage(frame, trial_predictors) for frame in model_pool_frames)
            )
            # sort descending on evidence support; lexical predictor makes ties deterministic
            key = (n_supported, min_ratio, min_joint, "".join(chr(255 - ord(c)) for c in predictor))
            trials.append((key, predictor, trial_support))
        trials.sort(key=lambda item: item[0], reverse=True)
        _, removed, chosen_support = trials[0]
        pruning_rows.append(
            {
                "iteration": int(iteration),
                "action": "remove_process_axis",
                "removed_predictor": removed,
                "removed_process": process_by_predictor[removed],
                "n_processes": len(selected) - 1,
                "n_supported_M_fold_cells": int(chosen_support["audit_support_complete"].sum()),
                "n_total_M_fold_cells": len(chosen_support),
                "minimum_support_ratio": _minimum_support_ratio(
                    chosen_support,
                    minimum_fit_background_rows=int(minimum_fit_background_rows),
                    minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
                    minimum_heldout_occurrence_rows=int(minimum_heldout_occurrence_rows),
                ),
                "predictors": ",".join(x for x in selected if x != removed),
            }
        )
        selected.remove(removed)
        iteration += 1

    processes = tuple(process_by_predictor[p] for p in selected)
    return PartitionAwareEmpiricalAuditSpace(
        predictors=tuple(selected),
        processes=processes,
        initial_predictors=tuple(base.predictors),
        initial_processes=tuple(base.processes),
        minimum_predictor_coverage=float(minimum_predictor_coverage),
        minimum_joint_coverage=float(minimum_joint_coverage),
        minimum_processes=int(minimum_processes),
        minimum_fit_background_rows=int(minimum_fit_background_rows),
        minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
        minimum_heldout_occurrence_rows=int(minimum_heldout_occurrence_rows),
        support_ledger=support.reset_index(drop=True),
        pruning_ledger=pd.DataFrame(pruning_rows),
        base_audit_ledger=base.ledger.copy(),
    )
