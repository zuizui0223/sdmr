from sdmr.known_truth import simulate_gaussian_plant_niche
from sdmr.known_truth_benchmark import benchmark_selectors_against_known_truth
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

    assert set(result.selector_choices["selector"]) == {"inner_auc", "inner_cbi", "niche_recovery"}
    assert set(result.truth_evaluation["selector"]) == {"inner_auc", "inner_cbi", "niche_recovery"}
    assert result.fold_metrics["candidate"].nunique() >= 2
    assert result.truth_evaluation["niche_overlap_schoener_d_pc12"].between(0, 1).all()
