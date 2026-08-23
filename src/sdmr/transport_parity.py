"""Fail-closed parity checks for transport-only recomputation paths.

Scientific structure and discrete decisions must remain exact. Floating model
outputs may be compared within a predeclared numerical envelope when the frozen
estimator itself is not bitwise reproducible across independent processes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_float_dtype, is_integer_dtype


@dataclass(frozen=True)
class FrameParitySummary:
    rows: int
    columns: int
    floating_cells_compared: int
    max_absolute_difference: float
    max_relative_difference: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


def assert_transport_frame_parity(
    reference: pd.DataFrame,
    reconstructed: pd.DataFrame,
    *,
    rtol: float,
    atol: float,
) -> FrameParitySummary:
    """Require exact structure/discrete values and close floating outputs.

    Integer, boolean, string/object, categorical and datetime-like columns are
    exact. Only floating columns receive the supplied tolerance. NaN/non-finite
    locations must still match exactly, and the function fails closed on any
    value outside the frozen envelope.
    """

    if float(rtol) < 0 or float(atol) < 0:
        raise ValueError("rtol and atol must be non-negative")
    if list(reference.columns) != list(reconstructed.columns):
        raise AssertionError("transport parity column order changed")
    if reference.shape != reconstructed.shape:
        raise AssertionError(
            f"transport parity shape changed: {reference.shape} != {reconstructed.shape}"
        )

    floating_cells = 0
    max_abs = 0.0
    max_rel = 0.0

    for column in reference.columns:
        left = reference[column]
        right = reconstructed[column]
        left_float = is_float_dtype(left.dtype)
        right_float = is_float_dtype(right.dtype)

        if left_float != right_float:
            raise AssertionError(
                f"transport parity floating dtype class changed for column {column}"
            )

        if left_float and right_float:
            a = left.to_numpy(dtype=float, na_value=np.nan)
            b = right.to_numpy(dtype=float, na_value=np.nan)
            a_finite = np.isfinite(a)
            b_finite = np.isfinite(b)
            if not np.array_equal(a_finite, b_finite):
                raise AssertionError(
                    f"transport parity finite/non-finite mask changed for column {column}"
                )
            nonfinite = ~a_finite
            if np.any(nonfinite) and not np.array_equal(
                a[nonfinite], b[nonfinite], equal_nan=True
            ):
                raise AssertionError(
                    f"transport parity non-finite values changed for column {column}"
                )
            finite = a_finite
            if not np.any(finite):
                continue
            av = a[finite]
            bv = b[finite]
            diff = np.abs(av - bv)
            allowed = float(atol) + float(rtol) * np.abs(av)
            if np.any(diff > allowed):
                idx = int(np.argmax(diff - allowed))
                raise AssertionError(
                    "transport parity floating tolerance exceeded for "
                    f"{column}: reference={av[idx]!r}, reconstructed={bv[idx]!r}, "
                    f"abs_diff={diff[idx]!r}, allowed={allowed[idx]!r}, "
                    f"rtol={rtol}, atol={atol}"
                )
            floating_cells += int(diff.size)
            if diff.size:
                max_abs = max(max_abs, float(np.max(diff)))
                denom = np.maximum(np.abs(av), float(atol) if float(atol) > 0 else 1e-300)
                max_rel = max(max_rel, float(np.max(diff / denom)))
            continue

        # Do not let a tolerant numeric comparison hide count/flag changes.
        if is_integer_dtype(left.dtype) or is_integer_dtype(right.dtype):
            if not (is_integer_dtype(left.dtype) and is_integer_dtype(right.dtype)):
                raise AssertionError(
                    f"transport parity integer dtype class changed for column {column}"
                )
        if is_bool_dtype(left.dtype) or is_bool_dtype(right.dtype):
            if not (is_bool_dtype(left.dtype) and is_bool_dtype(right.dtype)):
                raise AssertionError(
                    f"transport parity boolean dtype class changed for column {column}"
                )
        pd.testing.assert_series_equal(
            left,
            right,
            check_dtype=False,
            check_names=True,
            check_exact=True,
        )

    return FrameParitySummary(
        rows=int(len(reference)),
        columns=int(len(reference.columns)),
        floating_cells_compared=int(floating_cells),
        max_absolute_difference=float(max_abs),
        max_relative_difference=float(max_rel),
    )
