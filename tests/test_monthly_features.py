import numpy as np
import pandas as pd
import pytest

from sdmr.data import aggregate_monthly_climatology_features, validate_monthly_feature_recipes


def _monthly(variable, values):
    return {f"{variable}_{month:02d}": [value] for month, value in enumerate(values, start=1)}


def test_monthly_recipes_make_explicit_annual_mean_max_and_sum():
    points = pd.DataFrame({
        **_monthly("vpd", range(1, 13)),
        **_monthly("pet", [2] * 12),
    })
    recipes = pd.DataFrame({
        "predictor": ["vpd_mean", "vpd_max", "pet_annual"],
        "source_variable": ["vpd", "vpd", "pet"],
        "feature_recipe": ["annual_mean", "annual_max", "annual_sum"],
    })
    out = aggregate_monthly_climatology_features(points, recipes)
    assert out.loc[0, "vpd_mean"] == pytest.approx(6.5)
    assert out.loc[0, "vpd_max"] == pytest.approx(12)
    assert out.loc[0, "pet_annual"] == pytest.approx(24)


def test_complete_year_is_required_by_default():
    points = pd.DataFrame(_monthly("vpd", range(1, 13)))
    points.loc[0, "vpd_07"] = np.nan
    recipes = pd.DataFrame({
        "predictor": ["vpd_mean"],
        "source_variable": ["vpd"],
        "feature_recipe": ["annual_mean"],
    })
    out = aggregate_monthly_climatology_features(points, recipes)
    assert np.isnan(out.loc[0, "vpd_mean"])
    relaxed = aggregate_monthly_climatology_features(points, recipes, require_complete_year=False)
    assert np.isfinite(relaxed.loc[0, "vpd_mean"])


def test_recipe_validation_rejects_implicit_or_unknown_transform():
    with pytest.raises(ValueError):
        validate_monthly_feature_recipes(pd.DataFrame({
            "predictor": ["x"], "source_variable": ["vpd"], "feature_recipe": ["magic"]
        }))
