from sdmr.known_truth import simulate_gaussian_plant_niche
from sdmr.known_truth_benchmark import (
    benchmark_selectors_against_known_truth,
    summarize_selector_disagreement,
)
from sdmr.known_truth_scenarios import (
    KNOWN_TRUTH_FAMILIES,
    simulate_known_truth_plant_niche,
    standard_known_truth_candidates,
)
from sdmr.model import ModelSpec
from sdmr.niche_recovery_cv import RecoveryCandidate


def test_known_truth_selector_benchmark_returns_prediction_and_recovery_selectors():
    sim = simulate_gaussian_plant_niche(
        seed=9,
        n_cells=2400,
        n_occurrences=240,
        n_target_group=850,
    )
    candidates = {
        "true_quadratic": RecoveryCandidate(
            "true_quadratic",
            ("temperature", "water"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
        ),
        "proxy_quadratic": RecoveryCandidate(
            "proxy_quadratic",
            ("temp_proxy", "water"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
        ),
        "noise_linear": RecoveryCandidate(
            "noise_linear",
            ("noise", "seasonality"),
            ModelSpec(C=1.0, degree=1, penalty="l2"),
        ),
    }
    result = benchmark_selectors_against_known_truth(
        sim,
        candidates,
        n_spatial_blocks=6,
        inner_folds=3,
        random_state=9,
    )

    expected = {
        "inner_auc",
        "inner_cbi",
        "inner_or10",
        "niche_recovery",
        "gated_niche_recovery",
    }
    assert set(result.selector_choices["selector"]) == expected
    assert set(result.truth_evaluation["selector"]) == expected
    assert result.fold_metrics["candidate"].nunique() >= 2
    assert result.truth_evaluation["niche_overlap_schoener_d_pc12"].between(0, 1).all()
    gated = result.selector_choices.loc[result.selector_choices["selector"].eq("gated_niche_recovery")].iloc[0]
    assert gated["gated_eligible_candidates"]
    assert float(gated["gated_auc_floor"]) == 0.51
    assert float(gated["gated_chance_auc"]) == 0.50


def test_known_truth_families_generate_distinct_valid_surfaces():
    signatures = []
    for family in KNOWN_TRUTH_FAMILIES:
        sim = simulate_known_truth_plant_niche(
            family,
            seed=17,
            n_cells=1200,
            n_occurrences=120,
            n_target_group=450,
        )
        truth = sim.environment[sim.true_suitability_column]
        assert truth.between(0, 1).all()
        assert len(sim.occurrences) == 120
        assert len(sim.target_group) == 450
        assert "recording_bias" not in sim.audit_predictors
        signatures.append(round(float(truth.mean()), 6))
    assert len(set(signatures)) >= 4


def test_observation_confounded_scenario_keeps_prediction_and_ecological_outputs_separate():
    sim = simulate_known_truth_plant_niche(
        "observation_confounded",
        seed=23,
        n_cells=4200,
        n_occurrences=420,
        n_target_group=1500,
        focal_recording_bias_strength=4.0,
    )
    candidates = standard_known_truth_candidates()
    assert candidates["niche_plus_observer"].observation_predictors == ("recording_bias",)
    assert candidates["observer_only"].observation_predictors == ("recording_bias",)

    result = benchmark_selectors_against_known_truth(
        sim,
        candidates,
        n_spatial_blocks=6,
        inner_folds=3,
        random_state=23,
    )

    # Full prediction criteria remain available even when the selected model uses
    # an observation-process covariate; hidden ecological truth is scored from the
    # marginalized ecological product and must remain finite.
    assert result.selector_choices["mean_inner_auc"].notna().all()
    assert result.selector_choices["n_observation_predictors"].isin([0, 1]).all()
    assert result.truth_evaluation[[
        "truth_surface_rank",
        "truth_surface_nrmse",
        "response_curve_error",
        "optimum_error",
        "lower_limit_error",
        "upper_limit_error",
        "driver_process_f1",
    ]].notna().all().all()

    gated = summarize_selector_disagreement(result, reference_selector="gated_niche_recovery")
    assert set(gated["selector"]) == {"inner_auc", "inner_cbi", "inner_or10", "niche_recovery"}
    assert gated[[
        "truth_overlap_gain",
        "truth_centroid_error_reduction",
        "truth_breadth_error_reduction",
        "truth_quantile_error_reduction",
        "truth_surface_rank_gain",
        "truth_response_curve_error_reduction",
        "truth_process_f1_gain",
    ]].notna().all().all()


def test_disagreement_summary_does_not_require_a_weighted_super_score():
    sim = simulate_known_truth_plant_niche(
        "asymmetric",
        seed=7,
        n_cells=2200,
        n_occurrences=220,
        n_target_group=800,
    )
    result = benchmark_selectors_against_known_truth(
        sim,
        standard_known_truth_candidates(),
        n_spatial_blocks=6,
        inner_folds=3,
        random_state=7,
    )
    out = summarize_selector_disagreement(result)
    assert set(out["selector"]) == {"inner_auc", "inner_cbi", "inner_or10", "niche_recovery"}
    assert "truth_overlap_gain" in out
    assert "truth_centroid_error_reduction" in out
    assert "truth_response_curve_error_reduction" in out
    assert "truth_process_f1_gain" in out
    assert "reference_truth_pareto_better" in out
