import pandas as pd

from sdmr.process_promotion import (
    UniversalProcessPromotionCriteria,
    assess_universal_process_promotion,
)


def _criteria():
    return UniversalProcessPromotionCriteria(
        min_core_stability=0.7,
        min_splits_selected=3,
        min_mean_validation_process_drop=0.03,
        min_positive_validation_drop_fraction=0.7,
        min_validation_drop_pairs=6,
        min_validation_drop_splits=3,
        min_mean_core_minus_full=-0.03,
        min_core_validation_pairs=6,
        min_core_validation_splits=3,
        min_mean_core_minus_random=0.03,
        min_positive_core_vs_random_fraction=0.7,
        min_core_vs_random_pairs=12,
        min_core_vs_random_splits=3,
    )


def _core_tables(include_failed_water=False):
    rows = [
        {
            "process": "drought",
            "splits_selected": 4,
            "n_splits": 5,
            "core_stability": 0.8,
            "validation_drop_pairs": 8,
            "validation_drop_splits": 4,
            "mean_validation_process_drop": 0.08,
            "median_validation_process_drop": 0.07,
            "positive_validation_drop_fraction": 0.875,
        },
        {
            "process": "noise",
            "splits_selected": 1,
            "n_splits": 5,
            "core_stability": 0.2,
            "validation_drop_pairs": 2,
            "validation_drop_splits": 1,
            "mean_validation_process_drop": 0.0,
            "median_validation_process_drop": 0.0,
            "positive_validation_drop_fraction": 0.0,
        },
    ]
    if include_failed_water:
        rows.append(
            {
                "process": "water",
                "splits_selected": 4,
                "n_splits": 5,
                "core_stability": 0.8,
                "validation_drop_pairs": 8,
                "validation_drop_splits": 4,
                "mean_validation_process_drop": 0.0,
                "median_validation_process_drop": 0.0,
                "positive_validation_drop_fraction": 0.25,
            }
        )
    stability = pd.DataFrame(rows)
    comparison = pd.DataFrame(
        [
            {"species": f"s{i}", "split_id": i // 2, "core_minus_full_presence_rank": -0.01}
            for i in range(8)
        ]
    )
    random = pd.DataFrame(
        [
            {
                "species": f"s{i % 4}",
                "split_id": i % 4,
                "repeat": i // 4,
                "core_minus_random_presence_rank": 0.08,
            }
            for i in range(16)
        ]
    )
    return stability, comparison, random


def test_universal_core_promotes_only_when_discovery_stability_necessity_and_null_gates_pass():
    stability, comparison, random = _core_tables()
    assessment = assess_universal_process_promotion(stability, comparison, random, _criteria())
    assert assessment.promoted_core is True
    assert assessment.validated_process_candidates["process"].tolist() == ["drought"]
    assert bool(assessment.core_transfer_evidence.iloc[0]["passes"]) is True
    assert bool(assessment.core_random_evidence.iloc[0]["passes"]) is True


def test_validation_failure_does_not_prune_and_repromote_a_new_core():
    stability, comparison, random = _core_tables(include_failed_water=True)
    assessment = assess_universal_process_promotion(stability, comparison, random, _criteria())
    assert assessment.promoted_core is False
    assert set(assessment.process_evidence.loc[assessment.process_evidence["candidate_by_discovery"], "process"]) == {"drought", "water"}
    assert assessment.validated_process_candidates["process"].tolist() == ["drought"]
    assert any("process=water" in failure for failure in assessment.failures)
