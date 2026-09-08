import numpy as np
import pandas as pd
import pytest

from sdmr.process_information_purge import (
    cross_validated_process_reconstruction,
    fit_process_information_purge,
)


def _proxy_frame(seed=7, n=360):
    rng = np.random.default_rng(seed)
    water = rng.normal(size=n)
    temp = rng.normal(size=n)
    neutral_a = 1.8 * water + 0.25 * temp + rng.normal(scale=0.25, size=n)
    neutral_b = -0.9 * water + 0.15 * water**2 + rng.normal(scale=0.30, size=n)
    return pd.DataFrame(
        {
            "water": water,
            "temp": temp,
            "neutral_a": neutral_a,
            "neutral_b": neutral_b,
        }
    )


def test_purge_removes_background_predictable_process_component():
    frame = _proxy_frame()
    purge = fit_process_information_purge(
        frame.iloc[:240],
        process="water",
        process_predictors=("water",),
        retained_predictors=("neutral_a", "neutral_b"),
        degree=2,
        ridge_alpha=1.0,
    )
    test = frame.iloc[240:].reset_index(drop=True)
    purged = purge.transform(test)
    before = abs(test["water"].corr(test["neutral_a"], method="spearman"))
    after = abs(test["water"].corr(purged["neutral_a"], method="spearman"))
    assert before > 0.8
    assert after < 0.25
    assert list(purged.columns) == list(test.columns)
    assert np.allclose(purged["water"], test["water"])


def test_cross_validated_reconstruction_reports_information_reduction():
    frame = _proxy_frame(n=420)
    diagnostic = cross_validated_process_reconstruction(
        frame,
        process="water",
        process_predictors=("water",),
        retained_predictors=("neutral_a", "neutral_b", "temp"),
        n_splits=3,
        degree=2,
        ridge_alpha=1.0,
    )
    row = diagnostic.iloc[0]
    assert row["process"] == "water"
    assert row["pre_purge_r2"] > 0.8
    assert row["post_purge_r2"] < 0.15
    assert abs(row["post_purge_rank_correlation"]) < abs(row["pre_purge_rank_correlation"])


def test_purge_is_independent_of_occurrence_or_truth_columns():
    frame = _proxy_frame(n=120)
    augmented = frame.copy()
    augmented["presence"] = np.arange(len(frame)) % 2
    augmented["external_truth"] = np.arange(len(frame)) % 3
    a = fit_process_information_purge(
        frame,
        process="water",
        process_predictors=("water",),
        retained_predictors=("neutral_a", "neutral_b"),
    )
    b = fit_process_information_purge(
        augmented,
        process="water",
        process_predictors=("water",),
        retained_predictors=("neutral_a", "neutral_b"),
    )
    ta = a.transform(frame)
    tb = b.transform(augmented)
    assert np.allclose(ta[["neutral_a", "neutral_b"]], tb[["neutral_a", "neutral_b"]])


def test_missing_values_fail_closed_in_transformed_rows():
    frame = _proxy_frame(n=80)
    purge = fit_process_information_purge(
        frame,
        process="water",
        process_predictors=("water",),
        retained_predictors=("neutral_a",),
    )
    test = frame.iloc[:8].copy()
    test.loc[test.index[2], "water"] = np.nan
    transformed = purge.transform(test)
    assert np.isnan(transformed.loc[test.index[2], "neutral_a"])
    assert np.isfinite(transformed.loc[test.index[0], "neutral_a"])


def test_invalid_purge_contracts_are_rejected():
    frame = _proxy_frame(n=30)
    with pytest.raises(ValueError):
        fit_process_information_purge(
            frame,
            process="water",
            process_predictors=("water",),
            retained_predictors=("water", "neutral_a"),
        )
    with pytest.raises(KeyError):
        fit_process_information_purge(
            frame,
            process="water",
            process_predictors=("missing",),
            retained_predictors=("neutral_a",),
        )
    with pytest.raises(ValueError):
        fit_process_information_purge(
            frame.iloc[:4],
            process="water",
            process_predictors=("water",),
            retained_predictors=("neutral_a",),
        )
