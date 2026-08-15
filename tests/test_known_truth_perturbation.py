from sdmr.known_truth_perturbation import (
    KnownTruthPerturbationSpec,
    evaluate_known_truth_perturbations,
)
from sdmr.known_truth_scenarios import standard_known_truth_candidates


def test_sampling_and_background_perturbations_use_model_pool_m_and_emit_candidate_metrics():
    specs = (
        KnownTruthPerturbationSpec("tight", sampling_bias_strength=1.15, access_radius=0.20),
        KnownTruthPerturbationSpec("broad", sampling_bias_strength=1.15, access_radius=0.80),
        KnownTruthPerturbationSpec("high_bias", sampling_bias_strength=2.0, access_radius=0.35),
    )
    result = evaluate_known_truth_perturbations(
        "gaussian",
        5,
        standard_known_truth_candidates(),
        perturbations=specs,
        n_cells=1600,
        n_occurrences=180,
        n_target_group=650,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
        # This test validates perturbation evidence construction rather than the
        # production adequacy threshold.
        chance_auc=0.0,
        minimum_auc_margin=0.0,
        auc_sem_multiplier=0.0,
    )
    metrics = result.fold_metrics
    assert set(metrics["perturbation"]) == {"tight", "broad", "high_bias"}
    assert metrics["candidate"].nunique() >= 5
    assert "true_suitability" not in metrics.columns
    assert "truth_surface_rank" not in metrics.columns
    assert metrics["n_outer_model_presence"].min() < 180

    counts = metrics.groupby("perturbation")["n_accessible_background"].first()
    assert counts["tight"] < counts["broad"]
    assert result.selection is not None
    assert result.selection_error is None
    assert set(result.selection.perturbations) == {"tight", "broad", "high_bias"}


def test_domain_transfer_is_a_fixed_exogenous_perturbation_not_hidden_truth_scoring():
    specs = (
        KnownTruthPerturbationSpec(
            "source_to_shifted",
            access_radius=None,
            domain_train="source",
            domain_test="shifted",
        ),
        KnownTruthPerturbationSpec(
            "shifted_to_source",
            access_radius=None,
            domain_train="shifted",
            domain_test="source",
        ),
    )
    result = evaluate_known_truth_perturbations(
        "interaction",
        7,
        standard_known_truth_candidates(),
        perturbations=specs,
        n_cells=1800,
        n_occurrences=220,
        n_target_group=700,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
        chance_auc=0.0,
        minimum_auc_margin=0.0,
        auc_sem_multiplier=0.0,
    )
    metrics = result.fold_metrics
    assert set(metrics["perturbation_type"]) == {"domain_transfer"}
    assert set(metrics["perturbation"]) == {"source_to_shifted", "shifted_to_source"}
    assert set(metrics["fold"]) == {0}
    assert metrics["presence_rank"].notna().all()
    assert metrics["niche_overlap_schoener_d_pc12"].notna().all()
    assert "true_suitability" not in metrics.columns


def test_default_prediction_adequacy_may_return_no_robust_candidate_without_relaxing_rule():
    specs = (
        KnownTruthPerturbationSpec("low", sampling_bias_strength=0.5, access_radius=0.35),
        KnownTruthPerturbationSpec("high", sampling_bias_strength=2.0, access_radius=0.35),
    )
    result = evaluate_known_truth_perturbations(
        "observation_confounded",
        3,
        standard_known_truth_candidates(),
        perturbations=specs,
        n_cells=1500,
        n_occurrences=170,
        n_target_group=600,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
    )
    # The development benchmark must keep the predeclared AUC adequacy rule.
    # Either a robust candidate exists or the failure is recorded; no threshold
    # is silently relaxed to manufacture a winner.
    if result.selection is None:
        assert result.selection_error
    else:
        adequacy = result.selection.adequacy_summary
        eligible = adequacy.loc[adequacy["eligible_all_perturbations"], "candidate"].unique()
        assert len(eligible) >= 1
        assert adequacy.loc[adequacy["candidate"].isin(eligible), "passes_prediction_adequacy"].all()
