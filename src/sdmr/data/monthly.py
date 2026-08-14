"""Derive season-invariant annual features from CHELSA monthly climatologies."""

from __future__ import annotations

import numpy as np
import pandas as pd


_ALLOWED_RECIPES = {"annual_mean", "annual_min", "annual_max", "annual_sum"}


def validate_monthly_feature_recipes(recipes: pd.DataFrame) -> pd.DataFrame:
    """Validate the explicit monthly-to-annual feature contract."""

    required = {"predictor", "source_variable", "feature_recipe"}
    missing = required - set(recipes.columns)
    if missing:
        raise KeyError(f"monthly feature recipes missing columns: {sorted(missing)}")
    out = recipes.copy()
    for col in ("predictor", "source_variable", "feature_recipe"):
        out[col] = out[col].astype(str).str.strip()
    if out[["predictor", "source_variable", "feature_recipe"]].eq("").any().any():
        raise ValueError("monthly feature recipes contain empty required values")
    duplicated = out.loc[out["predictor"].duplicated(keep=False), "predictor"].unique().tolist()
    if duplicated:
        raise ValueError(f"duplicate derived predictors: {sorted(duplicated)}")
    unknown = sorted(set(out["feature_recipe"]) - _ALLOWED_RECIPES)
    if unknown:
        raise ValueError(f"unsupported monthly feature recipes: {unknown}")
    return out.reset_index(drop=True)


def monthly_column_names(source_variable: str) -> list[str]:
    """Canonical in-memory column names after extracting the 12 monthly COGs."""

    return [f"{source_variable}_{month:02d}" for month in range(1, 13)]


def aggregate_monthly_climatology_features(
    points: pd.DataFrame,
    recipes: pd.DataFrame,
    *,
    require_complete_year: bool = True,
) -> pd.DataFrame:
    """Apply declared annual summaries to monthly climatology values.

    Calendar-month columns are intermediate only. Annual mean/min/max/sum
    summaries avoid treating a calendar month as the same season in both
    hemispheres. By default a derived feature is missing if any of its 12 monthly
    source values is missing.
    """

    spec = validate_monthly_feature_recipes(recipes)
    out = points.copy()
    for row in spec.itertuples(index=False):
        columns = monthly_column_names(row.source_variable)
        missing = [col for col in columns if col not in out]
        if missing:
            raise KeyError(
                f"missing monthly columns for {row.predictor}: {missing}"
            )
        values = out[columns].apply(pd.to_numeric, errors="coerce")
        complete = values.notna().all(axis=1)
        if row.feature_recipe == "annual_mean":
            derived = values.mean(axis=1, skipna=not require_complete_year)
        elif row.feature_recipe == "annual_min":
            derived = values.min(axis=1, skipna=not require_complete_year)
        elif row.feature_recipe == "annual_max":
            derived = values.max(axis=1, skipna=not require_complete_year)
        elif row.feature_recipe == "annual_sum":
            derived = values.sum(axis=1, skipna=not require_complete_year, min_count=12 if require_complete_year else 1)
        else:  # guarded by validation
            raise RuntimeError(row.feature_recipe)
        if require_complete_year:
            derived = derived.where(complete, np.nan)
        out[row.predictor] = derived.astype(float)
    return out
