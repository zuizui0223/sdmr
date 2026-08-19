"""Model-outcome-free spatial support gates for cross-taxon Product-A v2.

This module answers a question that must be settled before any candidate SDM is
fit: can the predeclared spatial outer folds be evaluated with enough model-pool
presence and background rows?  The gate uses only spatial group labels and row
counts.  It never sees environmental predictor values, prediction scores,
ecological recovery metrics, or sealed outcomes.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold


def spatial_support_fold_ledger(
    presence_groups: Sequence[int] | np.ndarray,
    background_groups: Sequence[int] | np.ndarray,
    *,
    outer_folds: int = 2,
    minimum_background_rows_per_side: int = 5,
    minimum_presence_rows_per_side: int = 2,
) -> pd.DataFrame:
    """Return pre-model outer-fold support diagnostics.

    The row-count conditions mirror the hard pre-fit conditions used by the
    nested recovery benchmark.  Requiring both train and test sides to satisfy
    them prevents a taxon/M cell from entering cross-taxon comparison when one
    side of the spatial split is structurally unsupported.
    """

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if p_groups.ndim != 1 or b_groups.ndim != 1:
        raise ValueError("spatial group arrays must be one-dimensional")
    if len(p_groups) < 2 or len(b_groups) < 2:
        return pd.DataFrame(
            [
                {
                    "outer_fold": -1,
                    "n_presence_train": 0,
                    "n_presence_test": 0,
                    "n_background_train": 0,
                    "n_background_test": 0,
                    "eligible_fold": False,
                    "failure_reason": "insufficient_rows_before_spatial_cv",
                }
            ]
        )
    unique_groups = np.unique(p_groups)
    folds = min(int(outer_folds), len(unique_groups))
    if folds < 2:
        return pd.DataFrame(
            [
                {
                    "outer_fold": -1,
                    "n_presence_train": len(p_groups),
                    "n_presence_test": 0,
                    "n_background_train": len(b_groups),
                    "n_background_test": 0,
                    "eligible_fold": False,
                    "failure_reason": "fewer_than_two_presence_spatial_groups",
                }
            ]
        )

    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(p_groups), dtype=int)
    rows: list[dict[str, object]] = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(dummy, groups=p_groups)):
        train_blocks = np.unique(p_groups[train_idx])
        test_blocks = np.unique(p_groups[test_idx])
        bg_train = np.isin(b_groups, train_blocks)
        bg_test = np.isin(b_groups, test_blocks)
        n_p_train = int(len(train_idx))
        n_p_test = int(len(test_idx))
        n_b_train = int(bg_train.sum())
        n_b_test = int(bg_test.sum())
        failures: list[str] = []
        if n_p_train < int(minimum_presence_rows_per_side):
            failures.append("presence_train")
        if n_p_test < int(minimum_presence_rows_per_side):
            failures.append("presence_test")
        if n_b_train < int(minimum_background_rows_per_side):
            failures.append("background_train")
        if n_b_test < int(minimum_background_rows_per_side):
            failures.append("background_test")
        rows.append(
            {
                "outer_fold": int(fold),
                "n_presence_train": n_p_train,
                "n_presence_test": n_p_test,
                "n_background_train": n_b_train,
                "n_background_test": n_b_test,
                "eligible_fold": not failures,
                "failure_reason": ",".join(failures),
            }
        )
    return pd.DataFrame(rows)


def assign_outcome_blind_taxon_roles(
    eligible_taxa: Sequence[str],
    *,
    seed: int,
    validation_fraction: float,
    minimum_validation_taxa: int = 2,
    minimum_discovery_taxa: int = 2,
) -> pd.DataFrame:
    """Assign discovery/validation roles after a model-free eligibility gate."""

    taxa = tuple(sorted(dict.fromkeys(str(x) for x in eligible_taxa)))
    if not 0 < float(validation_fraction) < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    minimum_total = int(minimum_validation_taxa) + int(minimum_discovery_taxa)
    if len(taxa) < minimum_total:
        raise ValueError(
            f"need at least {minimum_total} eligible taxa for discovery/validation transfer"
        )
    shuffled = np.array(taxa, dtype=object)
    np.random.default_rng(int(seed)).shuffle(shuffled)
    n_validation = max(
        int(minimum_validation_taxa),
        int(math.ceil(len(taxa) * float(validation_fraction))),
    )
    n_validation = min(n_validation, len(taxa) - int(minimum_discovery_taxa))
    validation = set(str(x) for x in shuffled[:n_validation])
    rows = [
        {
            "scientific_name": taxon,
            "role": "validation" if taxon in validation else "discovery",
        }
        for taxon in taxa
    ]
    return pd.DataFrame(rows)
