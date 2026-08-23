import numpy as np
import pandas as pd
import pytest

from sdmr.model import ModelSpec, fit_relative_suitability_model, score_relative_suitability
from sdmr.v2_7_2_deterministic_procedure_library import deterministic_procedure_library


def _frames():
    presence = pd.DataFrame({
        "x": [-2.0, -1.5, -1.0, 0.8, 1.2, 1.8],
        "z": [0.2, 0.1, 0.4, 1.1, 1.3, 1.6],
    })
    background = pd.DataFrame({
        "x": [-3.0, -2.2, -0.4, 0.0, 0.3, 2.4, 2.8, 3.2],
        "z": [1.8, 1.5, 1.2, 0.9, 0.8, 0.4, 0.2, 0.1],
    })
    return presence, background


def test_historical_model_spec_identity_is_unchanged_when_seed_omitted():
    spec = ModelSpec(C=1.0, degree=2, penalty="l2")
    assert spec.random_state is None
    assert spec.label == "logit_l2_C1_degree2"


def test_seeded_successor_has_distinct_candidate_identity_and_estimator_seed():
    spec = ModelSpec(C=1.0, degree=2, penalty="l2", random_state=0)
    assert spec.label == "logit_l2_C1_degree2_rs0"
    presence, background = _frames()
    model = fit_relative_suitability_model(presence, background, ("x", "z"), model_spec=spec)
    assert model.named_steps["logisticregression"].random_state == 0


def test_seeded_fit_is_exactly_repeatable_for_same_rows():
    presence, background = _frames()
    spec = ModelSpec(C=1.0, degree=2, penalty="l2", random_state=271)
    m1 = fit_relative_suitability_model(presence, background, ("x", "z"), model_spec=spec)
    m2 = fit_relative_suitability_model(presence, background, ("x", "z"), model_spec=spec)
    s1 = score_relative_suitability(m1, background, ("x", "z"))
    s2 = score_relative_suitability(m2, background, ("x", "z"))
    np.testing.assert_array_equal(s1, s2)


def test_random_state_must_be_integer_or_none():
    with pytest.raises(TypeError, match="random_state"):
        ModelSpec(random_state=0.5)


def test_deterministic_library_requires_frozen_seed_and_emits_eight_seeded_candidates():
    contract = {
        "fixed_design": {
            "procedure_library": {
                "strategies": ["all", "vif", "predictive_forward", "niche_forward"],
                "model_specs": [
                    {"C": 0.1, "degree": 1, "penalty": "l2"},
                    {"C": 1.0, "degree": 2, "penalty": "l2"},
                ],
                "model_random_state": 0,
                "inner_folds": 3,
                "outer_folds": 4,
                "max_predictors": 8,
                "vif_threshold": 5.0,
                "predictive_min_gain": 0.0,
                "observation_predictors": [],
            }
        }
    }
    procedures = deterministic_procedure_library(contract)
    assert len(procedures) == 8
    assert len({p.label for p in procedures}) == 8
    assert all(p.model_spec.random_state == 0 for p in procedures)
    assert all(p.label.endswith("_rs0") for p in procedures)

    del contract["fixed_design"]["procedure_library"]["model_random_state"]
    with pytest.raises(ValueError, match="model_random_state"):
        deterministic_procedure_library(contract)
