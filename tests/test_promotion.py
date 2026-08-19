import pandas as pd

from sdmr.promotion import ProductAPromotionCriteria, assess_product_a_promotion


M_SET = "all_predeclared_M_sensitivity_specs"


def _tables():
    runs = pd.DataFrame(
        {
            "run_id": [0, 1, 2, 3],
            "winning_data_specification": [M_SET] * 4,
            "winning_universe": ["active_all", "active_all", "active_all", "bioclim19"],
            "winning_strategy": ["predictive", "predictive", "predictive", "vif"],
            "winning_universe_sha256": ["u" * 64, "u" * 64, "u" * 64, "v" * 64],
            "winning_predictors": ["bio1,bio12,vpd"] * 3 + ["bio1,bio12"],
            "occurrence_sha256": ["o" * 64] * 4,
            "occurrence_feature_sha256": ["f" * 64] * 4,
            "m_spec_win_fraction": [1.0, 2 / 3, 1.0, 1 / 3],
        }
    )
    stability = pd.DataFrame(
        {
            "winning_data_specification": [M_SET, M_SET],
            "winning_universe": ["active_all", "bioclim19"],
            "winning_strategy": ["predictive", "vif"],
            "runs_selected": [3, 1],
            "n_runs": [4, 4],
            "selection_fraction": [0.75, 0.25],
            "mean_n_predictors": [3.0, 2.0],
        }
    )
    delta_rows = []
    for run_id in (0, 1, 2):
        for m_spec in ("M150", "M300", "M500"):
            for species in ("a", "b"):
                delta_rows.extend(
                    [
                        {
                            "run_id": run_id,
                            "winning_data_specification": M_SET,
                            "winning_universe": "active_all",
                            "winning_strategy": "predictive",
                            "data_specification": m_spec,
                            "comparator": "all",
                            "species": species,
                            "delta_presence_rank": 0.04,
                        },
                        {
                            "run_id": run_id,
                            "winning_data_specification": M_SET,
                            "winning_universe": "active_all",
                            "winning_strategy": "predictive",
                            "data_specification": m_spec,
                            "comparator": "vif",
                            "species": species,
                            "delta_presence_rank": 0.03,
                        },
                    ]
                )
    return runs, stability, pd.DataFrame(delta_rows)


def test_promotion_passes_only_when_stability_M_robustness_and_unseen_taxa_pass():
    runs, stability, deltas = _tables()
    criteria = ProductAPromotionCriteria(
        min_protocol_selection_fraction=0.70,
        min_runs_selected=3,
        min_mean_delta_presence_rank=0.02,
        min_positive_pair_fraction=0.80,
        min_pairs_per_comparator=12,
        required_comparators=("all", "vif"),
        min_m_spec_win_fraction=2 / 3,
    )
    assessment = assess_product_a_promotion(runs, stability, deltas, criteria)
    assert assessment.promoted is True
    assert assessment.failures == []
    assert assessment.promoted_choice["winning_data_specification"] == M_SET
    assert float(assessment.promoted_choice["min_m_spec_win_fraction_observed"]) == 2 / 3
    assert assessment.comparator_evidence["passes"].all()


def test_promotion_reports_null_result_instead_of_relaxing_thresholds():
    runs, stability, deltas = _tables()
    # Make one otherwise-selected run fail the predeclared M robustness gate.
    runs.loc[runs["run_id"].eq(1), "m_spec_win_fraction"] = 1 / 3
    criteria = ProductAPromotionCriteria(
        min_protocol_selection_fraction=0.90,
        min_runs_selected=4,
        min_mean_delta_presence_rank=0.05,
        min_positive_pair_fraction=1.0,
        min_pairs_per_comparator=24,
        required_comparators=("all", "vif"),
        min_m_spec_win_fraction=2 / 3,
    )
    assessment = assess_product_a_promotion(runs, stability, deltas, criteria)
    assert assessment.promoted is False
    assert any("selection_fraction" in failure for failure in assessment.failures)
    assert any("mean_delta" in failure for failure in assessment.failures)
    assert any("M-sensitivity" in failure for failure in assessment.failures)
