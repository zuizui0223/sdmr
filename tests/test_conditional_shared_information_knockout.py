import numpy as np
import pandas as pd
import pytest

from sdmr.conditional_shared_information_knockout import (
    fit_conditional_shared_information_knockout,
    verify_retained_predictors_unchanged,
)


def _frame(seed=13, n=400):
    rng = np.random.default_rng(seed)
    water = rng.normal(size=n)
    soil = rng.normal(size=n)
    shared = 0.8 * water + 0.4 * soil
    temperature = 0.9 * shared + rng.normal(scale=0.25, size=n)
    temp_proxy = 1.2 * temperature + rng.normal(scale=0.15, size=n)
    seasonality = 0.7 * water - 0.2 * soil + rng.normal(scale=0.20, size=n)
    return pd.DataFrame(
        {
            "temperature": temperature,
            "temp_proxy": temp_proxy,
            "water": water,
            "soil": soil,
            "seasonality": seasonality,
        }
    )


def test_conditional_knockout_replaces_only_target_columns():
    frame = _frame()
    fit = fit_conditional_shared_information_knockout(
        frame.iloc[:280],
        process="temperature",
        process_predictors=("temperature", "temp_proxy"),
        conditioning_predictors=("water", "soil", "seasonality"),
        degree=2,
    )
    test = frame.iloc[280:].reset_index(drop=True)
    out = fit.transform(test)
    assert verify_retained_predictors_unchanged(
        test,
        out,
        retained_predictors=("water", "soil", "seasonality"),
    )
    assert not np.allclose(out["temperature"], test["temperature"])
    assert not np.allclose(out["temp_proxy"], test["temp_proxy"])


def test_conditional_knockout_preserves_shared_component_but_removes_target_residual():
    frame = _frame(n=600)
    train = frame.iloc[:400].reset_index(drop=True)
    test = frame.iloc[400:].reset_index(drop=True)
    fit = fit_conditional_shared_information_knockout(
        train,
        process="temperature",
        process_predictors=("temperature",),
        conditioning_predictors=("water", "soil", "seasonality"),
        degree=2,
    )
    out = fit.transform(test)
    before_resid = test["temperature"] - out["temperature"]
    # replacement remains strongly associated with the shared environmental space
    assert abs(out["temperature"].corr(test["water"])) > 0.5
    # while the removed residual is not copied into the replacement
    assert abs(before_resid.corr(out["temperature"])) < 0.25


def test_conditional_knockout_rejects_structural_overlap():
    frame = _frame(n=80)
    with pytest.raises(ValueError):
        fit_conditional_shared_information_knockout(
            frame,
            process="temperature",
            process_predictors=("temperature",),
            conditioning_predictors=("temperature", "water"),
        )
