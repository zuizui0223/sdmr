import numpy as np

from sdmr.known_truth_scenarios import simulate_known_truth_plant_niche
from sdmr.model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability
from sdmr.niche_recovery_cv import heldout_niche_recovery_profile
from sdmr.observation_corrected_recovery import (
    observation_corrected_heldout_niche_recovery_profile,
)


def test_uniform_occurrence_weights_reproduce_unweighted_heldout_profile():
    sim = simulate_known_truth_plant_niche(
        "gaussian",
        seed=13,
        n_cells=1400,
        n_occurrences=180,
        n_target_group=550,
    )
    p_train = sim.occurrences.iloc[:120].reset_index(drop=True)
    p_test = sim.occurrences.iloc[120:].reset_index(drop=True)
    b_train = sim.target_group.iloc[:350].reset_index(drop=True)
    b_test = sim.target_group.iloc[350:].reset_index(drop=True)
    predictors = ("temperature", "water")
    model = fit_relative_suitability_model(
        p_train,
        b_train,
        predictors,
        model_spec=ModelSpec(C=1.0, degree=2, penalty="l2"),
    )
    ecological = score_ecological_suitability(model, b_test, predictors)

    plain = heldout_niche_recovery_profile(
        b_train,
        b_test,
        p_test,
        ecological,
        sim.audit_predictors,
    )
    weighted = observation_corrected_heldout_niche_recovery_profile(
        b_train,
        b_test,
        p_test,
        ecological,
        np.ones(len(p_test)),
        sim.audit_predictors,
    )
    assert np.isclose(
        plain.niche_overlap_schoener_d_pc12,
        weighted.niche_overlap_schoener_d_pc12,
    )
    assert np.isclose(plain.centroid_distance, weighted.centroid_distance)
    assert np.isclose(plain.breadth_log_sd_error, weighted.breadth_log_sd_error)
    # Quantile implementations differ only by weighted-vs-unweighted interpolation
    # convention, so identity weights should remain very close rather than bitwise equal.
    assert abs(plain.quantile_profile_error - weighted.quantile_profile_error) < 0.03


def test_weighted_coverage_is_a_weighted_fraction():
    sim = simulate_known_truth_plant_niche(
        "gaussian",
        seed=23,
        n_cells=1000,
        n_occurrences=120,
        n_target_group=400,
    )
    p_test = sim.occurrences.iloc[:40].reset_index(drop=True)
    b_train = sim.target_group.iloc[:250].reset_index(drop=True)
    b_test = sim.target_group.iloc[250:].reset_index(drop=True)
    suitability = np.ones(len(b_test), dtype=float)
    weights = np.linspace(0.2, 2.0, len(p_test))
    profile = observation_corrected_heldout_niche_recovery_profile(
        b_train,
        b_test,
        p_test,
        suitability,
        weights,
        sim.audit_predictors,
    )
    assert 0.0 <= profile.sealed_pc12_envelope_coverage90 <= 1.0
    assert np.isfinite(profile.centroid_distance)
    assert np.isfinite(profile.quantile_profile_error)
