"""Outcome-blind audit for residual process information in predictor sets.

The audit never receives occurrence labels, suitability values, model scores or
known-truth process labels. It uses predictor/background rows only and asks:

* after removing the predictors already assigned to process P, how well can the
  remaining predictor set reconstruct P's declared anchor variables?
* which individual retained predictors carry the strongest reconstructive signal?

This is a proposal/audit layer, not an automatic registry mutation. Scientific
process assignments remain human-approved and must be frozen before an outcome
is used for model fitting or process claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from .process_information_closure import normalize_process_information_registry


@dataclass(frozen=True)
class ProcessProxyAudit:
    process_summary: pd.DataFrame
    candidate_summary: pd.DataFrame
    predictor_universe: tuple[str, ...]
    n_splits: int
    degree: int


def _folds(n: int, *, groups: np.ndarray | None, n_splits: int):
    indices = np.arange(n)
    if groups is None:
        splitter = KFold(n_splits=n_splits, shuffle=True, random_state=0)
        return tuple(splitter.split(indices))
    g = np.asarray(groups)
    if len(g) != n:
        raise ValueError("groups must align with predictor rows")
    if len(np.unique(g)) < n_splits:
        raise ValueError("insufficient unique groups for process proxy audit")
    splitter = GroupKFold(n_splits=n_splits)
    return tuple(splitter.split(indices, groups=g))


def _model(degree: int):
    return make_pipeline(
        PolynomialFeatures(degree=degree, include_bias=False),
        StandardScaler(),
        Ridge(alpha=1.0),
    )


def _cv_r2(x: np.ndarray, y: np.ndarray, folds, *, degree: int) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    keep = np.isfinite(y) & np.isfinite(x).all(axis=1)
    if int(keep.sum()) < max(12, len(folds) * 3):
        return float("nan")
    # Preserve the original fold membership while excluding incomplete rows.
    predictions = np.full(len(y), np.nan, dtype=float)
    for train_idx, test_idx in folds:
        train = np.asarray(train_idx)[keep[np.asarray(train_idx)]]
        test = np.asarray(test_idx)[keep[np.asarray(test_idx)]]
        if len(train) < 4 or len(test) < 2:
            continue
        estimator = TransformedTargetRegressor(
            regressor=_model(degree),
            transformer=StandardScaler(),
        )
        estimator.fit(x[train], y[train])
        predictions[test] = estimator.predict(x[test])
    scored = keep & np.isfinite(predictions)
    if int(scored.sum()) < max(8, len(folds) * 2):
        return float("nan")
    return float(r2_score(y[scored], predictions[scored]))


def audit_process_proxy_reconstructability(
    predictor_frame: pd.DataFrame,
    process_registry: pd.DataFrame,
    *,
    process_universe: Sequence[str],
    predictor_universe: Sequence[str],
    groups: Sequence[object] | None = None,
    n_splits: int = 5,
    degree: int = 2,
) -> ProcessProxyAudit:
    """Audit process-information closure without using any biological outcome.

    ``predictor_universe`` is explicit so unrelated columns (presence labels,
    truth, IDs, coordinates unless deliberately treated as predictors) cannot
    silently enter the audit.
    """
    predictors = tuple(str(x).strip() for x in predictor_universe)
    processes = tuple(str(x).strip() for x in process_universe)
    if not predictors or len(set(predictors)) != len(predictors):
        raise ValueError("predictor_universe must contain unique predictors")
    if not processes or len(set(processes)) != len(processes):
        raise ValueError("process_universe must contain unique processes")
    missing = [x for x in predictors if x not in predictor_frame.columns]
    if missing:
        raise KeyError("predictor_frame is missing predictors: " + ", ".join(missing))
    if int(n_splits) < 2:
        raise ValueError("n_splits must be at least 2")
    if int(degree) not in (1, 2):
        raise ValueError("degree must be 1 or 2")

    registry = normalize_process_information_registry(
        process_registry,
        process_universe=processes,
        predictor_universe=predictors,
    )
    frame = predictor_frame.loc[:, list(predictors)].apply(pd.to_numeric, errors="coerce")
    fold_indices = _folds(
        len(frame),
        groups=None if groups is None else np.asarray(groups),
        n_splits=int(n_splits),
    )

    process_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    for process in processes:
        assigned = tuple(
            registry.loc[registry["process"].astype(str).eq(process), "predictor"].astype(str)
        )
        direct = tuple(
            registry.loc[
                registry["process"].astype(str).eq(process)
                & registry["role"].astype(str).eq("direct"),
                "predictor",
            ].astype(str)
        )
        anchors = direct if direct else assigned
        retained = tuple(x for x in predictors if x not in set(assigned))
        anchor_scores = []
        for anchor in anchors:
            score = (
                _cv_r2(
                    frame.loc[:, list(retained)].to_numpy(float),
                    frame[anchor].to_numpy(float),
                    fold_indices,
                    degree=int(degree),
                )
                if retained
                else float("nan")
            )
            anchor_scores.append(score)

            for candidate in retained:
                univariate = _cv_r2(
                    frame[[candidate]].to_numpy(float),
                    frame[anchor].to_numpy(float),
                    fold_indices,
                    degree=int(degree),
                )
                pair = frame[[candidate, anchor]].dropna()
                spearman = (
                    float(pair[candidate].corr(pair[anchor], method="spearman"))
                    if len(pair) >= 4
                    else float("nan")
                )
                current_processes = tuple(
                    sorted(
                        registry.loc[
                            registry["predictor"].astype(str).eq(candidate), "process"
                        ].astype(str)
                    )
                )
                candidate_rows.append(
                    {
                        "target_process": process,
                        "anchor_predictor": anchor,
                        "candidate_predictor": candidate,
                        "suggested_role": "proxy",
                        "current_processes": ",".join(current_processes),
                        "univariate_cv_r2": univariate,
                        "spearman": spearman,
                        "abs_spearman": abs(spearman) if np.isfinite(spearman) else float("nan"),
                        "n_complete_pairs": int(len(pair)),
                        "auto_frozen": False,
                        "requires_human_review": True,
                    }
                )

        finite = np.asarray([x for x in anchor_scores if np.isfinite(x)], dtype=float)
        process_rows.append(
            {
                "process": process,
                "declared_predictors": ",".join(assigned),
                "anchor_predictors": ",".join(anchors),
                "retained_predictor_count": len(retained),
                "mean_anchor_reconstruction_cv_r2": float(np.mean(finite)) if len(finite) else float("nan"),
                "max_anchor_reconstruction_cv_r2": float(np.max(finite)) if len(finite) else float("nan"),
                "outcome_used": False,
                "registry_modified": False,
            }
        )

    candidate_summary = pd.DataFrame(candidate_rows)
    if len(candidate_summary):
        candidate_summary = candidate_summary.sort_values(
            ["target_process", "univariate_cv_r2", "abs_spearman", "candidate_predictor"],
            ascending=[True, False, False, True],
            kind="mergesort",
        ).reset_index(drop=True)
    return ProcessProxyAudit(
        process_summary=pd.DataFrame(process_rows),
        candidate_summary=candidate_summary,
        predictor_universe=predictors,
        n_splits=int(n_splits),
        degree=int(degree),
    )
