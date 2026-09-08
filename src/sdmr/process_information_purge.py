"""Outcome-blind process-information purging for proxy-closed challenges.

A declared process knockout can fail to remove process information when retained
predictors remain correlated with direct/derived process representations.  This
module provides a deliberately stronger *diagnostic intervention*: learn, from
background environments only, the component of each retained predictor that is
predictable from the excluded process closure and replace the retained predictor
by its residual.

The purge never reads occurrence labels, presence/background class labels,
external biological positive-control labels, fitted SDM coefficients or process
truth.  It is therefore suitable as a development-time information-erasure
operator, but it is not a causal residualization claim.  Whether the stronger
operator creates false process calls must be tested prospectively after the rule
is frozen.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler


def _unique_nonempty(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(x).strip() for x in values)
    if not result or any(not x for x in result):
        raise ValueError(f"{name} must contain non-empty values")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _numeric_complete(frame: pd.DataFrame, columns: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    cols = list(columns)
    missing = sorted(set(cols) - set(frame.columns))
    if missing:
        raise KeyError("frame missing purge predictors: " + ", ".join(missing))
    values = frame[cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    valid = np.isfinite(values).all(axis=1)
    return values, valid


def _purge_regressor(*, degree: int, ridge_alpha: float):
    if int(degree) not in (1, 2):
        raise ValueError("degree must be 1 or 2")
    if not float(ridge_alpha) > 0:
        raise ValueError("ridge_alpha must be > 0")
    return make_pipeline(
        PolynomialFeatures(degree=int(degree), include_bias=False),
        StandardScaler(),
        Ridge(alpha=float(ridge_alpha)),
    )


@dataclass(frozen=True)
class ProcessInformationPurge:
    """A background-fitted transform that residualizes retained predictors."""

    process: str
    process_predictors: tuple[str, ...]
    retained_predictors: tuple[str, ...]
    degree: int
    ridge_alpha: float
    n_fit_rows: int
    regressor: object

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with retained predictors replaced by purge residuals.

        Process predictors are left in the returned frame so callers can retain a
        complete audit table, but a process-exclusion model must fit only the
        declared ``retained_predictors`` (plus any separately declared observation
        predictors). Rows that lack either process or retained values receive NaN
        residuals and therefore fail closed in downstream model fitting/scoring.
        """

        process_values, process_valid = _numeric_complete(frame, self.process_predictors)
        retained_values, retained_valid = _numeric_complete(frame, self.retained_predictors)
        valid = process_valid & retained_valid
        result = frame.copy()
        for predictor in self.retained_predictors:
            result[predictor] = np.nan
        if not valid.any():
            return result
        predicted = np.asarray(self.regressor.predict(process_values[valid]), dtype=float)
        if predicted.ndim == 1:
            predicted = predicted[:, None]
        observed = retained_values[valid]
        if predicted.shape != observed.shape:
            raise RuntimeError("purge regressor returned an unexpected shape")
        residual = observed - predicted
        for j, predictor in enumerate(self.retained_predictors):
            result.loc[valid, predictor] = residual[:, j]
        return result


def fit_process_information_purge(
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    retained_predictors: Sequence[str],
    degree: int = 2,
    ridge_alpha: float = 1.0,
    minimum_complete_rows: int = 10,
) -> ProcessInformationPurge:
    """Fit the purge using environmental background rows only.

    No response/class column is accepted by the API.  This makes the chronology
    explicit: learn the environmental covariance operator first, then apply it to
    presence/background rows inside a matched process-knockout route.
    """

    process_name = str(process).strip()
    if not process_name:
        raise ValueError("process must be non-empty")
    process_cols = _unique_nonempty(process_predictors, name="process_predictors")
    retained_cols = _unique_nonempty(retained_predictors, name="retained_predictors")
    overlap = sorted(set(process_cols) & set(retained_cols))
    if overlap:
        raise ValueError("process and retained predictors must be disjoint: " + ", ".join(overlap))
    if int(minimum_complete_rows) < 5:
        raise ValueError("minimum_complete_rows must be >= 5")

    x, x_valid = _numeric_complete(background, process_cols)
    y, y_valid = _numeric_complete(background, retained_cols)
    valid = x_valid & y_valid
    n = int(valid.sum())
    if n < int(minimum_complete_rows):
        raise ValueError(
            f"process purge needs at least {int(minimum_complete_rows)} complete background rows; found {n}"
        )
    regressor = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
    regressor.fit(x[valid], y[valid])
    return ProcessInformationPurge(
        process=process_name,
        process_predictors=process_cols,
        retained_predictors=retained_cols,
        degree=int(degree),
        ridge_alpha=float(ridge_alpha),
        n_fit_rows=n,
        regressor=regressor,
    )


def _rank_correlation(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    keep = np.isfinite(a) & np.isfinite(b)
    if int(keep.sum()) < 3:
        return float("nan")
    ar = pd.Series(a[keep]).rank(method="average").to_numpy(float)
    br = pd.Series(b[keep]).rank(method="average").to_numpy(float)
    if np.allclose(ar, ar[0]) or np.allclose(br, br[0]):
        return 0.0
    return float(np.corrcoef(ar, br)[0, 1])


def cross_validated_process_reconstruction(
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    retained_predictors: Sequence[str],
    groups: Sequence[object] | np.ndarray | None = None,
    n_splits: int = 3,
    degree: int = 2,
    ridge_alpha: float = 1.0,
) -> pd.DataFrame:
    """Measure process information in retained predictors before/after purging.

    Every fold fits both the purge and the reconstruction model on training
    background rows only.  The diagnostic reports target-wise out-of-fold R2 and
    rank correlation.  It is an environmental information diagnostic, not an SDM
    performance metric and not a thresholded promotion rule.
    """

    process_name = str(process).strip()
    process_cols = _unique_nonempty(process_predictors, name="process_predictors")
    retained_cols = _unique_nonempty(retained_predictors, name="retained_predictors")
    overlap = sorted(set(process_cols) & set(retained_cols))
    if overlap:
        raise ValueError("process and retained predictors must be disjoint: " + ", ".join(overlap))
    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")

    p_all, p_valid = _numeric_complete(background, process_cols)
    r_all, r_valid = _numeric_complete(background, retained_cols)
    valid = p_valid & r_valid
    index = np.flatnonzero(valid)
    if len(index) < max(10, 2 * int(n_splits)):
        raise ValueError("insufficient complete background rows for reconstruction diagnostic")

    if groups is None:
        splitter = KFold(n_splits=int(n_splits), shuffle=False)
        split_iter = splitter.split(index)
    else:
        g = np.asarray(groups)
        if len(g) != len(background):
            raise ValueError("groups must align with background rows")
        g_valid = g[index]
        if len(np.unique(g_valid)) < int(n_splits):
            raise ValueError("insufficient unique groups for reconstruction diagnostic")
        splitter = GroupKFold(n_splits=int(n_splits))
        split_iter = splitter.split(index, groups=g_valid)

    before_truth: list[np.ndarray] = []
    before_pred: list[np.ndarray] = []
    after_truth: list[np.ndarray] = []
    after_pred: list[np.ndarray] = []

    for train_local, test_local in split_iter:
        train_idx = index[np.asarray(train_local)]
        test_idx = index[np.asarray(test_local)]
        train = background.iloc[train_idx].reset_index(drop=True)
        test = background.iloc[test_idx].reset_index(drop=True)

        # Reconstruct process from the original retained predictors.
        before = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
        before.fit(
            train[list(retained_cols)].to_numpy(float),
            train[list(process_cols)].to_numpy(float),
        )
        pred_before = np.asarray(before.predict(test[list(retained_cols)].to_numpy(float)), dtype=float)
        if pred_before.ndim == 1:
            pred_before = pred_before[:, None]

        # Fit the purge on training background only, then test whether process
        # information remains reconstructable from held-out residuals.
        purge = fit_process_information_purge(
            train,
            process=process_name,
            process_predictors=process_cols,
            retained_predictors=retained_cols,
            degree=int(degree),
            ridge_alpha=float(ridge_alpha),
            minimum_complete_rows=5,
        )
        train_purged = purge.transform(train)
        test_purged = purge.transform(test)
        after = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
        after.fit(
            train_purged[list(retained_cols)].to_numpy(float),
            train[list(process_cols)].to_numpy(float),
        )
        pred_after = np.asarray(after.predict(test_purged[list(retained_cols)].to_numpy(float)), dtype=float)
        if pred_after.ndim == 1:
            pred_after = pred_after[:, None]

        truth = test[list(process_cols)].to_numpy(float)
        before_truth.append(truth)
        before_pred.append(pred_before)
        after_truth.append(truth)
        after_pred.append(pred_after)

    truth = np.vstack(before_truth)
    pred_before = np.vstack(before_pred)
    pred_after = np.vstack(after_pred)
    rows: list[dict[str, object]] = []
    for j, predictor in enumerate(process_cols):
        rows.append(
            {
                "process": process_name,
                "process_predictor": predictor,
                "n_test_rows": int(len(truth)),
                "pre_purge_r2": float(r2_score(truth[:, j], pred_before[:, j])),
                "post_purge_r2": float(r2_score(truth[:, j], pred_after[:, j])),
                "pre_purge_rank_correlation": _rank_correlation(truth[:, j], pred_before[:, j]),
                "post_purge_rank_correlation": _rank_correlation(truth[:, j], pred_after[:, j]),
            }
        )
    return pd.DataFrame(rows)
