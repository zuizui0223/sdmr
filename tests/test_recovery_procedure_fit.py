import numpy as np

from sdmr.known_truth_scenarios import simulate_known_truth_plant_niche
from sdmr.model import ModelSpec, score_relative_suitability
from sdmr.niche_recovery_procedure import RecoveryProcedure
from sdmr.recovery_procedure_fit import fit_recovery_procedure


def _data(seed=81):
    sim = simulate_known_truth_plant_niche(
        "gaussian",
        seed=seed,
        n_cells=1200,
        n_occurrences=170,
        n_target_group=450,
    )
    cuts = [-1.0, 0.0, 1.0]
    p_groups = np.digitize(sim.occurrences["longitude"].to_numpy(float), cuts)
    b_groups = np.digitize(sim.target_group["longitude"].to_numpy(float), cuts)
    predictors = ("temperature", "water", "temp_proxy", "soil")
    return sim, p_groups, b_groups, predictors


def test_frozen_niche_forward_is_reapplied_to_complete_model_pool():
    sim, p_groups, b_groups, predictors = _data()
    procedure = RecoveryProcedure(
        "niche_forward",
        ModelSpec(C=1.0, degree=2, penalty="l2"),
        inner_folds=2,
        max_predictors=2,
    )
    fitted = fit_recovery_procedure(
        sim.occurrences,
        sim.target_group,
        p_groups,
        b_groups,
        predictors,
        predictors,
        procedure,
    )
    assert fitted.procedure == procedure
    assert 1 <= len(fitted.selected_ecological_predictors) <= 2
    assert set(fitted.selected_ecological_predictors) <= set(predictors)
    scores = score_relative_suitability(
        fitted.model,
        sim.target_group,
        fitted.selected_predictors,
    )
    assert len(scores) == len(sim.target_group)
    assert not fitted.selection_trace.empty


def test_observation_terms_are_fixed_but_not_reported_as_ecological_selection():
    sim = simulate_known_truth_plant_niche(
        "observation_confounded",
        seed=82,
        n_cells=1300,
        n_occurrences=180,
        n_target_group=480,
        focal_recording_bias_strength=5.0,
    )
    cuts = [-1.0, 0.0, 1.0]
    p_groups = np.digitize(sim.occurrences["longitude"].to_numpy(float), cuts)
    b_groups = np.digitize(sim.target_group["longitude"].to_numpy(float), cuts)
    procedure = RecoveryProcedure(
        "vif",
        ModelSpec(C=1.0, degree=1, penalty="l2"),
        inner_folds=2,
        observation_predictors=("recording_bias",),
    )
    fitted = fit_recovery_procedure(
        sim.occurrences,
        sim.target_group,
        p_groups,
        b_groups,
        ("temperature", "water", "temp_proxy"),
        ("temperature", "water", "temp_proxy"),
        procedure,
    )
    assert "recording_bias" in fitted.selected_predictors
    assert "recording_bias" not in fitted.selected_ecological_predictors
