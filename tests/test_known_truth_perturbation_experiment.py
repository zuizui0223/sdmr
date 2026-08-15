from sdmr.known_truth_perturbation import KnownTruthPerturbationSpec
from sdmr.known_truth_perturbation_experiment import (
    run_known_truth_perturbation_experiment,
)


def test_perturbation_experiment_opens_truth_only_after_three_selectors_choose():
    perturbations = (
        KnownTruthPerturbationSpec("sampling_standard", sampling_bias_strength=1.15, access_radius=0.35),
        KnownTruthPerturbationSpec("background_tight", sampling_bias_strength=1.15, access_radius=0.20),
        KnownTruthPerturbationSpec("background_broad", sampling_bias_strength=1.15, access_radius=0.80),
    )
    choices, truth, summary, metrics, failures = run_known_truth_perturbation_experiment(
        families=("gaussian",),
        seeds=(2,),
        perturbations=perturbations,
        n_cells=1600,
        n_occurrences=180,
        n_target_group=650,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
        # Test experiment plumbing independently of the production adequacy gate.
        chance_auc=0.0,
        minimum_auc_margin=0.0,
        auc_sem_multiplier=0.0,
    )
    assert set(choices["selector"]) == {
        "canonical_auc",
        "canonical_niche_recovery",
        "perturbation_robust_niche_recovery",
    }
    assert set(truth["selector"]) == set(choices["selector"])
    assert set(summary["selector"]) == set(choices["selector"])
    assert failures.empty

    # Selection evidence never contains generating-truth diagnostics.
    forbidden = {
        "true_suitability",
        "truth_surface_rank",
        "truth_surface_nrmse",
        "driver_process_f1",
    }
    assert forbidden.isdisjoint(metrics.columns)

    # The answer-check table does contain the direct ecological truth audit.
    assert {
        "niche_overlap_schoener_d_pc12",
        "truth_surface_rank",
        "truth_surface_nrmse",
        "response_curve_error",
        "optimum_error",
        "lower_limit_error",
        "upper_limit_error",
        "driver_process_f1",
        "truth_best_selectors",
    } <= set(truth.columns)


def test_production_gate_records_no_robust_candidate_instead_of_relaxing_thresholds():
    perturbations = (
        KnownTruthPerturbationSpec("sampling_standard", sampling_bias_strength=1.15, access_radius=0.35),
        KnownTruthPerturbationSpec("sampling_high", sampling_bias_strength=2.0, access_radius=0.35),
    )
    choices, truth, summary, metrics, failures = run_known_truth_perturbation_experiment(
        families=("observation_confounded",),
        seeds=(4,),
        perturbations=perturbations,
        n_cells=1500,
        n_occurrences=170,
        n_target_group=600,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
    )
    assert {"canonical_auc", "canonical_niche_recovery"} <= set(choices["selector"])
    robust_present = "perturbation_robust_niche_recovery" in set(choices["selector"])
    if robust_present:
        assert failures.empty
    else:
        assert len(failures) == 1
        assert failures.iloc[0]["selector"] == "perturbation_robust_niche_recovery"
    assert "true_suitability" not in metrics.columns
