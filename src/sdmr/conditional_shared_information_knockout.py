"""Background-only conditional shared-information knockout for v8.

The intervention replaces the target process closure P by the component
predictable from all other declared process closures Q. Retained Q predictors
are left numerically unchanged. The resulting route therefore removes only the
part of P not recoverable from the competing process representation while
preserving shared environmental structure.

This is an information intervention, not a causal or physiological claim. The
API accepts no occurrence labels, suitability values, external biological
labels, fitted SDM coefficients, or generating-process truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .process_information_purge import _numeric_complete, _purge_regressor


def _unique(values: Sequence[str], *, name: str, allow_empty: bool = False) -> tuple[str, ...]:
    out = tuple(str(x).strip() for x in values)
    if not out and not allow_empty:
        raise ValueError(f"{name} must be non-empty")
    if any(not x for x in out):
        raise ValueError(f"{name} must not contain empty strings")
    if len(set(out)) != len(out):
        raise ValueError(f"{name} must not contain duplicates")
    return out


@dataclass(frozen=True)
class ConditionalSharedInformationKnockout:
    process: str
    process_predictors: tuple[str, ...]
    conditioning_predictors: tuple[str, ...]
    degree: int
    ridge_alpha: float
    n_fit_rows: int
    regressor: object

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        q, q_valid = _numeric_complete(frame, self.conditioning_predictors)
        p, p_valid = _numeric_complete(frame, self.process_predictors)
        valid = q_valid & p_valid
        out = frame.copy()
        for col in self.process_predictors:
            out[col] = np.nan
        if not valid.any():
            return out
        pred = np.asarray(self.regressor.predict(q[valid]), dtype=float)
        if pred.ndim == 1:
            pred = pred[:, None]
        if pred.shape != p[valid].shape:
            raise RuntimeError("conditional knockout regressor returned unexpected shape")
        for j, col in enumerate(self.process_predictors):
            out.loc[valid, col] = pred[:, j]
        return out


def fit_conditional_shared_information_knockout(
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    conditioning_predictors: Sequence[str],
    degree: int = 2,
    ridge_alpha: float = 1.0,
    minimum_complete_rows: int = 10,
) -> ConditionalSharedInformationKnockout:
    process_name = str(process).strip()
    if not process_name:
        raise ValueError("process must be non-empty")
    pcols = _unique(process_predictors, name="process_predictors")
    qcols = _unique(conditioning_predictors, name="conditioning_predictors")
    overlap = sorted(set(pcols) & set(qcols))
    if overlap:
        raise ValueError("target and conditioning closures overlap structurally: " + ", ".join(overlap))
    if int(minimum_complete_rows) < 5:
        raise ValueError("minimum_complete_rows must be >= 5")
    p, p_valid = _numeric_complete(background, pcols)
    q, q_valid = _numeric_complete(background, qcols)
    valid = p_valid & q_valid
    n = int(valid.sum())
    if n < int(minimum_complete_rows):
        raise ValueError(
            f"conditional knockout needs at least {int(minimum_complete_rows)} complete background rows; found {n}"
        )
    regressor = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
    regressor.fit(q[valid], p[valid])
    return ConditionalSharedInformationKnockout(
        process=process_name,
        process_predictors=pcols,
        conditioning_predictors=qcols,
        degree=int(degree),
        ridge_alpha=float(ridge_alpha),
        n_fit_rows=n,
        regressor=regressor,
    )


def verify_retained_predictors_unchanged(
    before: pd.DataFrame,
    after: pd.DataFrame,
    *,
    retained_predictors: Sequence[str],
) -> bool:
    cols = _unique(retained_predictors, name="retained_predictors")
    a, av = _numeric_complete(before, cols)
    b, bv = _numeric_complete(after, cols)
    if not np.array_equal(av, bv):
        return False
    valid = av & bv
    if not valid.any():
        return False
    return bool(np.array_equal(a[valid], b[valid]))
