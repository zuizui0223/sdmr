import pandas as pd

from sdmr.empirical_audit_space import select_empirical_audit_space


def _manifest():
    return pd.DataFrame(
        {
            "predictor": ["temp_a", "temp_b", "water_a", "water_b", "snow_a", "rad_a"],
            "process": ["temperature", "temperature", "water", "water", "snow", "radiation"],
        }
    )


def test_audit_space_uses_model_pool_coverage_and_one_axis_per_process():
    a = pd.DataFrame(
        {
            "temp_a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "temp_b": [1, 2, 3, 4, 5, 6, 7, 8, None, None],
            "water_a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "water_b": [1, 2, 3, 4, 5, 6, 7, None, None, None],
            "snow_a": [1, None, None, None, None, None, None, None, None, None],
            "rad_a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        }
    )
    b = a.copy()
    result = select_empirical_audit_space(
        _manifest(),
        [a, b],
        minimum_predictor_coverage=0.90,
        minimum_joint_coverage=0.80,
        minimum_processes=3,
    )
    assert set(result.predictors) == {"temp_a", "water_a", "rad_a"}
    assert set(result.processes) == {"temperature", "water", "radiation"}
    assert result.minimum_observed_joint_coverage == 1.0
    ledger = result.ledger.set_index("process")
    assert ledger.loc["snow", "decision"] == "below_marginal_coverage"
    assert ledger.loc["temperature", "representative_predictor"] == "temp_a"


def test_joint_complete_guard_can_reject_individually_adequate_axis():
    frame = pd.DataFrame(
        {
            "temp_a": [1, 2, 3, 4, 5, 6, 7, 8, 9, None],
            "temp_b": [1] * 10,
            "water_a": [None, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "water_b": [1] * 10,
            "snow_a": [1] * 10,
            "rad_a": [1] * 10,
        }
    )
    # Make the individually best representatives temp_b/water_b unavailable by
    # removing them from the manifest. temp_a and water_a each have 90% coverage,
    # but their joint complete fraction is 80%; a 90% joint guard permits only one.
    manifest = pd.DataFrame(
        {
            "predictor": ["temp_a", "water_a", "snow_a", "rad_a"],
            "process": ["temperature", "water", "snow", "radiation"],
        }
    )
    result = select_empirical_audit_space(
        manifest,
        [frame],
        minimum_predictor_coverage=0.90,
        minimum_joint_coverage=0.90,
        minimum_processes=3,
    )
    assert len(result.predictors) == 3
    assert not ({"temp_a", "water_a"} <= set(result.predictors))
    assert result.minimum_observed_joint_coverage >= 0.90


def test_sealed_rows_are_not_an_input_to_audit_selection():
    model = pd.DataFrame(
        {
            "temp_a": [1, 2, 3, 4, 5],
            "temp_b": [1, 2, 3, 4, None],
            "water_a": [1, 2, 3, 4, 5],
            "water_b": [1, 2, 3, None, None],
            "snow_a": [1, 2, 3, 4, 5],
            "rad_a": [1, 2, 3, 4, 5],
        }
    )
    first = select_empirical_audit_space(
        _manifest(), [model], minimum_predictor_coverage=0.80, minimum_joint_coverage=0.80
    )
    # A hypothetical sealed table can be arbitrarily changed; because the public
    # API accepts only explicitly supplied model-pool frames it cannot affect the
    # result unless a caller violates the information barrier and passes it in.
    sealed = model.copy()
    sealed.loc[:, :] = None
    second = select_empirical_audit_space(
        _manifest(), [model], minimum_predictor_coverage=0.80, minimum_joint_coverage=0.80
    )
    assert first.predictors == second.predictors
    assert sealed.isna().all().all()
