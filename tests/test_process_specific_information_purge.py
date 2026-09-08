import numpy as np
import pandas as pd

from sdmr.process_information_purge import fit_process_information_purge
from sdmr.process_specific_information_purge import (
    COLLATERAL_LOSS,
    COLLATERAL_PRESERVED,
    cross_validated_collateral_information_audit,
    fit_process_specific_information_purge,
)


def _shared_climate_frame(seed=11, n=480):
    rng = np.random.default_rng(seed)
    temperature = rng.normal(size=n)
    water = rng.normal(size=n)
    seasonality_unique = rng.normal(scale=0.35, size=n)
    seasonality = 0.9 * temperature - 0.55 * water + seasonality_unique
    neutral_a = 0.8 * temperature + 0.5 * water + 0.7 * seasonality_unique + rng.normal(scale=0.20, size=n)
    neutral_b = -0.5 * temperature + 0.6 * water - 0.4 * seasonality_unique + rng.normal(scale=0.20, size=n)
    return pd.DataFrame(
        {
            "temperature": temperature,
            "water": water,
            "seasonality": seasonality,
            "neutral_a": neutral_a,
            "neutral_b": neutral_b,
        }
    )


def test_process_specific_purge_preserves_competing_process_better_than_full_purge():
    frame = _shared_climate_frame()
    train = frame.iloc[:320].reset_index(drop=True)
    test = frame.iloc[320:].reset_index(drop=True)
    retained = ("temperature", "water", "neutral_a", "neutral_b")

    full = fit_process_information_purge(
        train,
        process="seasonality",
        process_predictors=("seasonality",),
        retained_predictors=retained,
        degree=2,
        ridge_alpha=1.0,
    )
    specific = fit_process_specific_information_purge(
        train,
        process="seasonality",
        process_predictors=("seasonality",),
        competing_predictors=("temperature", "water"),
        retained_predictors=retained,
        degree=2,
        ridge_alpha=1.0,
    )
    full_test = full.transform(test)
    specific_test = specific.transform(test)

    full_temp = abs(test["temperature"].corr(full_test["temperature"], method="spearman"))
    specific_temp = abs(test["temperature"].corr(specific_test["temperature"], method="spearman"))
    full_water = abs(test["water"].corr(full_test["water"], method="spearman"))
    specific_water = abs(test["water"].corr(specific_test["water"], method="spearman"))
    assert specific_temp > full_temp + 0.20
    assert specific_water > full_water + 0.10
    assert specific_temp > 0.90
    assert specific_water > 0.90


def test_collateral_audit_is_truth_blind_and_reports_preservation_state():
    frame = _shared_climate_frame(n=540)
    audit = cross_validated_collateral_information_audit(
        frame,
        process="seasonality",
        process_predictors=("seasonality",),
        competing_process_predictors={
            "temperature": ("temperature",),
            "water": ("water",),
        },
        retained_predictors=("temperature", "water", "neutral_a", "neutral_b"),
        n_splits=3,
        degree=2,
        ridge_alpha=1.0,
        sem_multiplier=1.0,
    )
    collateral = audit.loc[audit["audit_role"].eq("collateral_preservation")]
    assert set(collateral["audited_process"]) == {"temperature", "water"}
    assert collateral["complete"].all()
    assert set(collateral["collateral_state"]).issubset(
        {COLLATERAL_PRESERVED, COLLATERAL_LOSS, "collateral_indeterminate"}
    )
    assert (collateral["mean_post_r2"] > 0.80).all()


def test_process_specific_purge_does_not_read_outcome_or_truth_columns():
    frame = _shared_climate_frame(n=180)
    augmented = frame.copy()
    augmented["presence"] = np.arange(len(frame)) % 2
    augmented["generating_truth"] = np.arange(len(frame)) % 3
    kwargs = dict(
        process="seasonality",
        process_predictors=("seasonality",),
        competing_predictors=("temperature", "water"),
        retained_predictors=("temperature", "water", "neutral_a", "neutral_b"),
        degree=2,
        ridge_alpha=1.0,
    )
    a = fit_process_specific_information_purge(frame, **kwargs)
    b = fit_process_specific_information_purge(augmented, **kwargs)
    ta = a.transform(frame)
    tb = b.transform(augmented)
    assert np.allclose(
        ta[["temperature", "water", "neutral_a", "neutral_b"]],
        tb[["temperature", "water", "neutral_a", "neutral_b"]],
    )
