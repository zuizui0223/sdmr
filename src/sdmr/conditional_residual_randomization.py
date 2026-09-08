"""Background-only conditional residual randomization for process knockouts.

For a target process closure P and conditioning process representation Q, fit
P = m(Q) + r on background environments.  A randomized counterfactual keeps the
conditional mean m(Q) and replaces each row's target-specific residual by a
residual vector drawn deterministically from the background residual bank.

The intervention therefore preserves the target closure's conditional variance
and multivariate residual covariance while breaking row-specific P residual
information.  All non-target columns are left numerically unchanged.  No
occurrence labels, fitted SDM coefficients, biological labels, or generating
truth are accepted by this API.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .process_information_purge import _numeric_complete, _purge_regressor


def _unique(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    out = tuple(str(x).strip() for x in values)
    if not out or any(not x for x in out) or len(set(out)) != len(out):
        raise ValueError(f"{name} must contain unique non-empty names")
    return out


@dataclass(frozen=True)
class ConditionalResidualRandomizer:
    process: str
    process_predictors: tuple[str, ...]
    conditioning_predictors: tuple[str, ...]
    degree: int
    ridge_alpha: float
    random_state: int
    n_fit_rows: int
    conditional_model: object
    residual_bank: np.ndarray
    residual_order: np.ndarray

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        target, target_valid = _numeric_complete(frame, self.process_predictors)
        conditioning, cond_valid = _numeric_complete(frame, self.conditioning_predictors)
        valid = target_valid & cond_valid
        result = frame.copy()
        for predictor in self.process_predictors:
            result[predictor] = np.nan
        if not valid.any():
            return result
        shared = np.asarray(self.conditional_model.predict(conditioning[valid]), dtype=float)
        if shared.ndim == 1:
            shared = shared[:, None]
        n = int(valid.sum())
        order = self.residual_order
        chosen = self.residual_bank[order[np.arange(n) % len(order)]]
        randomized = shared + chosen
        if randomized.shape != target[valid].shape:
            raise RuntimeError("conditional residual randomizer returned unexpected shape")
        for j, predictor in enumerate(self.process_predictors):
            result.loc[valid, predictor] = randomized[:, j]
        return result


def fit_conditional_residual_randomizer(
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    conditioning_predictors: Sequence[str],
    degree: int = 2,
    ridge_alpha: float = 1.0,
    random_state: int = 0,
    minimum_complete_rows: int = 10,
) -> ConditionalResidualRandomizer:
    process_name = str(process).strip()
    if not process_name:
        raise ValueError("process must be non-empty")
    target = _unique(process_predictors, name="process_predictors")
    conditioning_names = _unique(conditioning_predictors, name="conditioning_predictors")
    overlap = sorted(set(target) & set(conditioning_names))
    if overlap:
        raise ValueError("target and conditioning predictors overlap: " + ", ".join(overlap))
    if int(minimum_complete_rows) < 5:
        raise ValueError("minimum_complete_rows must be >= 5")

    z, z_valid = _numeric_complete(background, target)
    q, q_valid = _numeric_complete(background, conditioning_names)
    valid = z_valid & q_valid
    n = int(valid.sum())
    if n < int(minimum_complete_rows):
        raise ValueError(
            f"conditional residual randomizer needs at least {int(minimum_complete_rows)} complete background rows; found {n}"
        )
    model = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
    model.fit(q[valid], z[valid])
    fitted = np.asarray(model.predict(q[valid]), dtype=float)
    if fitted.ndim == 1:
        fitted = fitted[:, None]
    residuals = z[valid] - fitted
    if not np.isfinite(residuals).all():
        raise ValueError("non-finite residual bank")
    rng = np.random.default_rng(int(random_state))
    order = rng.permutation(n)
    # Avoid an identity draw when possible; the intervention must actually
    # break row-specific residual pairing on the fit data.
    if n > 1 and np.array_equal(order, np.arange(n)):
        order = np.roll(order, 1)
    return ConditionalResidualRandomizer(
        process=process_name,
        process_predictors=target,
        conditioning_predictors=conditioning_names,
        degree=int(degree),
        ridge_alpha=float(ridge_alpha),
        random_state=int(random_state),
        n_fit_rows=n,
        conditional_model=model,
        residual_bank=np.asarray(residuals, dtype=float),
        residual_order=np.asarray(order, dtype=int),
    )


def verify_non_target_predictors_unchanged(
    before: pd.DataFrame,
    after: pd.DataFrame,
    *,
    target_predictors: Sequence[str],
) -> bool:
    target = set(str(x) for x in target_predictors)
    common = [c for c in before.columns if c in after.columns and c not in target]
    for column in common:
        a = before[column]
        b = after[column]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            if not np.allclose(pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce"), equal_nan=True):
                return False
        elif not a.equals(b):
            return False
    return True
