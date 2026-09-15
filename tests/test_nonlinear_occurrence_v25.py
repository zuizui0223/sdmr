import numpy as np
import pandas as pd
import pytest

from sdmr.nonlinear_occurrence_v25 import NonlinearSpec, fit_occurrence_model


def samples():
    rng = np.random.default_rng(4)
    return (pd.DataFrame({"x": rng.normal(1, 1, 80)}),
            pd.DataFrame({"x": rng.normal(0, 1, 160)}))


def test_deterministic_occurrence_fit_ignores_unused_truth_columns():
    p, b = samples()
    first = fit_occurrence_model(p, b, ["x"], model_spec=NonlinearSpec())
    second = fit_occurrence_model(p.assign(true_suitability=0), b.assign(true_suitability=1),
                                  ["x"], model_spec=NonlinearSpec())
    np.testing.assert_array_equal(first.predict_proba(b.to_numpy()), second.predict_proba(b.to_numpy()))
    assert first.early_stopping is False
    assert first.class_weight == "balanced"


def test_hidden_truth_predictor_is_rejected():
    p, b = samples()
    with pytest.raises(ValueError, match="hidden truth"):
        fit_occurrence_model(p.assign(true_suitability=1), b.assign(true_suitability=0),
                             ["x", "true_suitability"], model_spec=NonlinearSpec())


def test_unfrozen_learner_is_rejected():
    p, b = samples()
    with pytest.raises(ValueError, match="unfrozen"):
        fit_occurrence_model(p, b, ["x"], model_spec=NonlinearSpec(label="changed"))
