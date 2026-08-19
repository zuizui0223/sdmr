import numpy as np

from sdmr.known_truth import known_truth_niche_recovery_profile, simulate_gaussian_plant_niche


def test_known_truth_profile_prefers_truth_like_prediction():
    sim = simulate_gaussian_plant_niche(seed=12, n_cells=3000, n_occurrences=250, n_target_group=900)
    truth = sim.environment[sim.true_suitability_column].to_numpy(float)
    rng = np.random.default_rng(12)
    bad = rng.random(len(truth))

    good_profile = known_truth_niche_recovery_profile(
        sim.environment,
        truth,
        truth,
        sim.audit_predictors,
    )
    bad_profile = known_truth_niche_recovery_profile(
        sim.environment,
        bad,
        truth,
        sim.audit_predictors,
    )

    assert good_profile.niche_overlap_schoener_d_pc12 > 0.999
    assert good_profile.centroid_distance < 1e-10
    assert good_profile.breadth_log_sd_error < 1e-10
    assert good_profile.quantile_profile_error < 1e-10
    assert good_profile.niche_overlap_schoener_d_pc12 > bad_profile.niche_overlap_schoener_d_pc12
    assert good_profile.centroid_distance < bad_profile.centroid_distance
    assert good_profile.quantile_profile_error < bad_profile.quantile_profile_error


def test_simulation_contains_correlated_proxy_and_biased_sampling():
    sim = simulate_gaussian_plant_niche(seed=3, n_cells=2500, n_occurrences=200, n_target_group=800)
    corr = sim.environment[["temperature", "temp_proxy"]].corr().iloc[0, 1]
    assert corr > 0.8
    assert len(sim.occurrences) == 200
    assert len(sim.target_group) == 800
    assert sim.environment["true_suitability"].between(0, 1).all()
