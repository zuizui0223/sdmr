import pandas as pd

from sdmr.niche_recovery_perturbation import (
    select_perturbation_robust_niche_recovery_protocol,
)


def _row(candidate, perturbation, fold, overlap, centroid, breadth, quantile, *, auc=0.7, complexity=4):
    return {
        "candidate": candidate,
        "perturbation": perturbation,
        "fold": fold,
        "niche_overlap_schoener_d_pc12": overlap,
        "centroid_distance": centroid,
        "breadth_log_sd_error": breadth,
        "quantile_profile_error": quantile,
        "presence_rank": auc,
        "n_predictors": complexity,
    }


def test_perturbation_selector_prefers_consistent_second_place_over_one_case_specialist():
    rows = []
    for fold in (0, 1):
        # Specialist wins p1 but collapses in p2.
        rows += [
            _row("specialist", "p1", fold, 0.95, 0.10, 0.10, 0.10, auc=0.8),
            _row("specialist", "p2", fold, 0.60, 0.50, 0.50, 0.50, auc=0.8),
            _row("consistent", "p1", fold, 0.86, 0.18, 0.18, 0.18, auc=0.7),
            _row("consistent", "p2", fold, 0.84, 0.20, 0.20, 0.20, auc=0.7),
            _row("third", "p1", fold, 0.75, 0.30, 0.30, 0.30, auc=0.7),
            _row("third", "p2", fold, 0.76, 0.29, 0.29, 0.29, auc=0.7),
        ]
    result = select_perturbation_robust_niche_recovery_protocol(
        pd.DataFrame(rows), auc_sem_multiplier=0.0
    )
    assert result.candidate == "consistent"
    consistent = result.candidate_summary.loc[
        result.candidate_summary["candidate"].eq("consistent")
    ].iloc[0]
    specialist = result.candidate_summary.loc[
        result.candidate_summary["candidate"].eq("specialist")
    ].iloc[0]
    assert consistent["worst_perturbation_rank__niche_overlap_schoener_d_pc12"] < specialist[
        "worst_perturbation_rank__niche_overlap_schoener_d_pc12"
    ]


def test_raw_metric_scale_changes_between_perturbations_do_not_change_rank_logic():
    frame = pd.DataFrame(
        [
            _row("a", "wide", 0, 0.90, 0.10, 0.10, 0.10),
            _row("b", "wide", 0, 0.80, 0.20, 0.20, 0.20),
            # Numerically compressed environment: same candidate ordering.
            _row("a", "narrow", 0, 0.59, 0.010, 0.012, 0.011),
            _row("b", "narrow", 0, 0.58, 0.020, 0.022, 0.021),
        ]
    )
    result = select_perturbation_robust_niche_recovery_protocol(
        frame, auc_sem_multiplier=0.0
    )
    assert result.candidate == "a"
    ranks = result.perturbation_ranks
    a = ranks.loc[ranks["candidate"].eq("a")]
    assert set(a["rank__niche_overlap_schoener_d_pc12"]) == {1.0}
    assert set(a["rank__centroid_distance"]) == {1.0}


def test_prediction_adequacy_must_hold_in_every_perturbation():
    frame = pd.DataFrame(
        [
            _row("ecology_star", "p1", 0, 0.95, 0.10, 0.10, 0.10, auc=0.80),
            _row("ecology_star", "p2", 0, 0.95, 0.10, 0.10, 0.10, auc=0.49),
            _row("robust", "p1", 0, 0.82, 0.20, 0.20, 0.20, auc=0.62),
            _row("robust", "p2", 0, 0.82, 0.20, 0.20, 0.20, auc=0.62),
        ]
    )
    result = select_perturbation_robust_niche_recovery_protocol(
        frame, auc_sem_multiplier=0.0
    )
    assert result.eligible_candidates == ("robust",)
    assert result.candidate == "robust"
    bad = result.adequacy_summary.loc[
        result.adequacy_summary["candidate"].eq("ecology_star")
    ]
    assert not bool(bad["eligible_all_perturbations"].iloc[0])


def test_missing_perturbation_disqualifies_candidate():
    frame = pd.DataFrame(
        [
            _row("partial", "p1", 0, 0.95, 0.10, 0.10, 0.10),
            _row("complete", "p1", 0, 0.82, 0.20, 0.20, 0.20),
            _row("complete", "p2", 0, 0.82, 0.20, 0.20, 0.20),
        ]
    )
    result = select_perturbation_robust_niche_recovery_protocol(
        frame, auc_sem_multiplier=0.0
    )
    assert result.eligible_candidates == ("complete",)
    assert result.candidate == "complete"


def test_perturbation_selector_keeps_ecological_axes_separate():
    frame = pd.DataFrame(
        [
            _row("overlap", "p1", 0, 0.95, 0.30, 0.30, 0.30),
            _row("balanced", "p1", 0, 0.85, 0.20, 0.20, 0.20),
            _row("overlap", "p2", 0, 0.94, 0.31, 0.31, 0.31),
            _row("balanced", "p2", 0, 0.84, 0.21, 0.21, 0.21),
        ]
    )
    result = select_perturbation_robust_niche_recovery_protocol(
        frame, auc_sem_multiplier=0.0
    )
    # Both remain on the worst-rank Pareto front: overlap is consistently first
    # on one dimension, balanced is consistently first on the other three.
    assert set(result.worst_rank_pareto_front) == {"overlap", "balanced"}
    assert result.candidate == "balanced"
    assert "weighted_score" not in result.candidate_summary.columns
