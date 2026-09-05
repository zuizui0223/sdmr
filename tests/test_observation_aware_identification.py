import numpy as np
import pandas as pd

from sdmr.model import ModelSpec
from sdmr.observation_aware_identification import fit_observation_aware_identification


def _tables(seed: int = 19):
    rng = np.random.default_rng(seed)
    n = 192
    groups = np.tile(np.arange(8), n // 8)
    presence = pd.DataFrame(
        {
            "x_thermal": rng.normal(1.7, 0.40, n),
            "x_water": rng.normal(0.0, 1.0, n),
            "recording_bias": rng.normal(2.0, 0.45, n),
        }
    )
    background = pd.DataFrame(
        {
            "x_thermal": rng.normal(-1.7, 0.40, n),
            "x_water": rng.normal(0.0, 1.0, n),
            "recording_bias": rng.normal(0.0, 1.0, n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "x_thermal", "process": "thermal", "role": "direct"},
            {"predictor": "x_water", "process": "water", "role": "direct"},
        ]
    )
    return presence, background, groups.copy(), groups.copy(), registry


def test_observation_predictor_is_retained_but_not_an_ecological_process() -> None:
    p, b, pg, bg, registry = _tables()
    fit = fit_observation_aware_identification(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("x_thermal", "x_water"),
        observation_predictors=("recording_bias",),
        process_registry=registry,
        process_universe=("thermal", "water"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.03,
    )

    assert fit.observation_predictors == ("recording_bias",)
    assert set(fit.process_summary["process"]) == {"thermal", "water"}
    assert fit.knockout_summary["retained_ecological_predictors"].str.contains("recording_bias").sum() == 0
    assert fit.fold_evidence["observation_correction_active"].astype(bool).any()


def test_marginal_ecological_prediction_is_invariant_to_observation_column_values() -> None:
    p, b, pg, bg, registry = _tables()
    fit = fit_observation_aware_identification(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("x_thermal", "x_water"),
        observation_predictors=("recording_bias",),
        process_registry=registry,
        process_universe=("thermal", "water"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.03,
    )

    probe_a = p.iloc[:20].copy()
    probe_b = probe_a.copy()
    probe_b["recording_bias"] = 1000.0
    eco_a = fit.predict_ecological_suitability(probe_a)
    eco_b = fit.predict_ecological_suitability(probe_b)
    assert np.allclose(eco_a, eco_b, rtol=0.0, atol=1e-12)

    full_a = fit.predict_relative_suitability(probe_a)
    full_b = fit.predict_relative_suitability(probe_b)
    assert not np.allclose(full_a, full_b, rtol=0.0, atol=1e-8)


def test_process_certificate_uses_prediction_and_ecological_witness_adequacy() -> None:
    p, b, pg, bg, registry = _tables()
    fit = fit_observation_aware_identification(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("x_thermal", "x_water"),
        observation_predictors=("recording_bias",),
        process_registry=registry,
        process_universe=("thermal", "water"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.03,
    )
    status = fit.process_summary.set_index("process")["status"].to_dict()
    assert status["thermal"] == "required_by_evidence_contract"
    assert status["water"] == "refuted_as_necessary"
    assert (
        fit.knockout_summary["route_adequate"]
        == (
            fit.knockout_summary["prediction_adequate"]
            & fit.knockout_summary["ecological_adequate"]
        )
    ).all()
