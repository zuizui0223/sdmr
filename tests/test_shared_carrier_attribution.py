import pandas as pd

from sdmr.process_challenge_learner import CONTRIBUTORY, REPLACEABLE, REQUIRED
from sdmr.shared_carrier_attribution import (
    CONTESTED_SHARED,
    attribute_shared_carrier_process_summary,
)


def _summary():
    return pd.DataFrame(
        [
            {"process": "seasonality", "status": CONTRIBUTORY, "process_detected": True},
            {"process": "water", "status": CONTRIBUTORY, "process_detected": True},
            {"process": "thermal", "status": REPLACEABLE, "process_detected": False},
            {"process": "soil", "status": REQUIRED, "process_detected": True},
        ]
    )


def _registry():
    return pd.DataFrame(
        [
            {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
            {"predictor": "water", "process": "water", "role": "direct"},
            {"predictor": "temperature", "process": "thermal", "role": "direct"},
            {"predictor": "temp_proxy", "process": "thermal", "role": "proxy"},
            {"predictor": "soil", "process": "soil", "role": "direct"},
        ]
    )


def _proxy():
    return pd.DataFrame(
        [
            # Removing seasonality also removes a predictor that reconstructs water.
            {
                "target_process": "water",
                "candidate_predictor": "seasonality",
                "univariate_cv_r2": 0.31,
                "abs_spearman": 0.44,
            },
            # Water carries only weak information about seasonality here.
            {
                "target_process": "seasonality",
                "candidate_predictor": "water",
                "univariate_cv_r2": 0.07,
                "abs_spearman": 0.20,
            },
            # Soil challenge has no meaningful shared carrier.
            {
                "target_process": "water",
                "candidate_predictor": "soil",
                "univariate_cv_r2": 0.02,
                "abs_spearman": 0.10,
            },
            # Strong information carried by temperature does not change a replaceable
            # thermal status because no unique contribution claim is being made.
            {
                "target_process": "water",
                "candidate_predictor": "temperature",
                "univariate_cv_r2": 0.40,
                "abs_spearman": 0.61,
            },
        ]
    )


def test_shared_statistical_carrier_downgrades_contribution_only() -> None:
    result = attribute_shared_carrier_process_summary(
        _summary(),
        _registry(),
        process_universe=("seasonality", "water", "thermal", "soil"),
        predictor_universe=("seasonality", "water", "temperature", "temp_proxy", "soil"),
        proxy_candidate_summary=_proxy(),
        minimum_univariate_cv_r2=0.25,
        minimum_abs_spearman=0.50,
    )
    by_process = result.process_summary.set_index("process")

    assert by_process.loc["seasonality", "attribution_status"] == CONTESTED_SHARED
    assert bool(by_process.loc["seasonality", "challenge_signal_detected"])
    assert not bool(by_process.loc["seasonality", "unique_process_evidence"])
    assert by_process.loc["seasonality", "shared_with_processes"] == "water"

    assert by_process.loc["water", "attribution_status"] == CONTRIBUTORY
    assert bool(by_process.loc["water", "unique_process_evidence"])

    assert by_process.loc["soil", "attribution_status"] == REQUIRED
    assert bool(by_process.loc["soil", "unique_process_evidence"])

    assert by_process.loc["thermal", "attribution_status"] == REPLACEABLE
    assert not bool(by_process.loc["thermal", "unique_process_evidence"])


def test_declared_many_to_many_carrier_is_attribution_ambiguity_without_proxy_audit() -> None:
    summary = pd.DataFrame(
        [{"process": "water", "status": REQUIRED, "process_detected": True}]
    )
    registry = pd.DataFrame(
        [
            {"predictor": "pet", "process": "water", "role": "composite"},
            {"predictor": "pet", "process": "thermal", "role": "composite"},
        ]
    )
    result = attribute_shared_carrier_process_summary(
        summary,
        registry,
        process_universe=("water", "thermal"),
        predictor_universe=("pet",),
        proxy_candidate_summary=None,
    )
    row = result.process_summary.iloc[0]
    assert row["attribution_status"] == CONTESTED_SHARED
    assert row["shared_carrier_predictors"] == "pet"
    assert row["shared_with_processes"] == "thermal"
    assert not bool(row["unique_process_evidence"])


def test_attribution_layer_does_not_mutate_input_tables() -> None:
    summary = _summary()
    registry = _registry()
    proxy = _proxy()
    summary_before = summary.copy(deep=True)
    registry_before = registry.copy(deep=True)
    proxy_before = proxy.copy(deep=True)

    attribute_shared_carrier_process_summary(
        summary,
        registry,
        process_universe=("seasonality", "water", "thermal", "soil"),
        predictor_universe=("seasonality", "water", "temperature", "temp_proxy", "soil"),
        proxy_candidate_summary=proxy,
    )

    pd.testing.assert_frame_equal(summary, summary_before)
    pd.testing.assert_frame_equal(registry, registry_before)
    pd.testing.assert_frame_equal(proxy, proxy_before)


def test_weak_shared_signal_does_not_create_contested_status() -> None:
    summary = pd.DataFrame(
        [{"process": "water", "status": CONTRIBUTORY, "process_detected": True}]
    )
    registry = pd.DataFrame(
        [
            {"predictor": "water", "process": "water", "role": "direct"},
            {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
        ]
    )
    proxy = pd.DataFrame(
        [
            {
                "target_process": "seasonality",
                "candidate_predictor": "water",
                "univariate_cv_r2": 0.10,
                "abs_spearman": 0.30,
            }
        ]
    )
    result = attribute_shared_carrier_process_summary(
        summary,
        registry,
        process_universe=("water", "seasonality"),
        predictor_universe=("water", "seasonality"),
        proxy_candidate_summary=proxy,
        minimum_univariate_cv_r2=0.25,
        minimum_abs_spearman=0.50,
    )
    row = result.process_summary.iloc[0]
    assert row["attribution_status"] == CONTRIBUTORY
    assert bool(row["unique_process_evidence"])
    assert not bool(row["shared_information_contested"])
