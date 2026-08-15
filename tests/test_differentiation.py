import pandas as pd

from sdmr.differentiation import DifferentiationCriteria, assess_differentiation


def _criteria():
    return DifferentiationCriteria(
        required_comparators=("canonical_m_auc", "canonical_m_boyce", "local_nested_auc"),
        min_runs=15,
        min_pairs_per_comparator=135,
        min_mean_delta_presence_rank=0.01,
        min_positive_pair_fraction=2 / 3,
        min_positive_run_fraction=2 / 3,
    )


def test_differentiation_requires_every_predeclared_comparator():
    summary = pd.DataFrame(
        [
            {"comparator": "canonical_m_auc", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.02, "positive_pair_fraction": 0.8, "positive_run_fraction": 0.8},
            {"comparator": "canonical_m_boyce", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.02, "positive_pair_fraction": 0.8, "positive_run_fraction": 0.8},
        ]
    )
    detail, passed = assess_differentiation(summary, _criteria())
    assert passed is False
    assert detail.loc[detail["comparator"] == "local_nested_auc", "failure_reason"].iloc[0] == "missing_or_duplicate_comparator"


def test_differentiation_passes_only_when_all_thresholds_hold():
    summary = pd.DataFrame(
        [
            {"comparator": "canonical_m_auc", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.02, "positive_pair_fraction": 0.8, "positive_run_fraction": 0.8},
            {"comparator": "canonical_m_boyce", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.015, "positive_pair_fraction": 0.7, "positive_run_fraction": 0.75},
            {"comparator": "local_nested_auc", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.011, "positive_pair_fraction": 0.67, "positive_run_fraction": 0.67},
        ]
    )
    detail, passed = assess_differentiation(summary, _criteria())
    assert passed is True
    assert detail["passes"].all()


def test_differentiation_reports_which_dimension_failed():
    summary = pd.DataFrame(
        [
            {"comparator": "canonical_m_auc", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.02, "positive_pair_fraction": 0.8, "positive_run_fraction": 0.8},
            {"comparator": "canonical_m_boyce", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.02, "positive_pair_fraction": 0.8, "positive_run_fraction": 0.8},
            {"comparator": "local_nested_auc", "n_runs": 15, "n_pairs": 135, "mean_delta_presence_rank": 0.005, "positive_pair_fraction": 0.8, "positive_run_fraction": 0.8},
        ]
    )
    detail, passed = assess_differentiation(summary, _criteria())
    assert passed is False
    local = detail.loc[detail["comparator"] == "local_nested_auc"].iloc[0]
    assert local["failure_reason"] == "mean_delta"
