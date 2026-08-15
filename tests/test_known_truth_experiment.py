import pandas as pd

from sdmr.known_truth_experiment import (
    _truth_ranks,
    run_structural_known_truth_experiment,
)


def test_truth_ranking_keeps_exact_selector_ties_as_co_winners():
    rows = []
    for selector, overlap, centroid, breadth, quantile in [
        ("alpha", 0.9, 0.1, 0.1, 0.1),
        ("beta", 0.9, 0.1, 0.1, 0.1),
        ("worse", 0.7, 0.3, 0.3, 0.3),
    ]:
        rows.append(
            {
                "scenario": "s",
                "seed": 1,
                "selector": selector,
                "niche_overlap_schoener_d_pc12": overlap,
                "centroid_distance": centroid,
                "breadth_log_sd_error": breadth,
                "quantile_profile_error": quantile,
            }
        )
    ranked = _truth_ranks(pd.DataFrame(rows))
    winners = set(ranked.loc[ranked["truth_selector_win"], "selector"])
    assert winners == {"alpha", "beta"}
    assert set(ranked["truth_best_selectors"]) == {"alpha,beta"}


def test_structural_experiment_emits_direct_ecological_truth_audit():
    choices, truth, summary = run_structural_known_truth_experiment(
        families=("gaussian", "asymmetric"),
        seeds=(1,),
        n_cells=1200,
        n_occurrences=120,
        n_target_group=450,
        n_spatial_blocks=4,
        inner_folds=2,
    )
    expected_selectors = {
        "inner_auc",
        "inner_cbi",
        "inner_or10",
        "niche_recovery",
        "gated_niche_recovery",
    }
    assert set(choices["selector"]) == expected_selectors
    assert set(truth["selector"]) == expected_selectors
    assert set(truth["scenario"]) == {"gaussian", "asymmetric"}
    assert {
        "truth_surface_rank",
        "truth_surface_nrmse",
        "response_curve_error",
        "optimum_error",
        "lower_limit_error",
        "upper_limit_error",
        "driver_process_precision",
        "driver_process_recall",
        "driver_process_f1",
        "truth_best_selectors",
    } <= set(truth.columns)
    assert set(summary["selector"]) == expected_selectors
    assert "truth_co_win_fraction" in summary.columns
    assert "mean_response_curve_error" in summary.columns
    assert "mean_driver_process_f1" in summary.columns
