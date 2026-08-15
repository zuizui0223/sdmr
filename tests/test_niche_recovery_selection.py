import pandas as pd

from sdmr.niche_recovery_selection import (
    select_generalization_gated_niche_recovery_protocol,
    select_niche_recovery_protocol,
)


def _row(candidate, fold, d, centroid, breadth, quantile, n_predictors, auc=0.8, or10=0.1):
    return {
        "candidate": candidate,
        "fold": fold,
        "niche_overlap_schoener_d_pc12": d,
        "centroid_distance": centroid,
        "breadth_log_sd_error": breadth,
        "quantile_profile_error": quantile,
        "n_predictors": n_predictors,
        "presence_rank": auc,
        "or10": or10,
    }


def test_dominated_candidate_cannot_win():
    metrics = pd.DataFrame(
        [
            _row("good", 0, 0.80, 0.20, 0.20, 0.20, 4),
            _row("good", 1, 0.78, 0.22, 0.21, 0.23, 4),
            _row("bad", 0, 0.50, 0.60, 0.60, 0.70, 3),
            _row("bad", 1, 0.52, 0.62, 0.58, 0.68, 3),
        ]
    )
    result = select_niche_recovery_protocol(metrics)
    assert result.candidate == "good"
    good = result.summary.loc[result.summary["candidate"] == "good"].iloc[0]
    bad = result.summary.loc[result.summary["candidate"] == "bad"].iloc[0]
    assert bool(good["pareto_front"])
    assert not bool(bad["pareto_front"])


def test_minimax_prefers_balanced_pareto_candidate():
    metrics = pd.DataFrame(
        [
            _row("overlap_specialist", 0, 0.95, 0.55, 0.55, 0.55, 6),
            _row("overlap_specialist", 1, 0.94, 0.54, 0.54, 0.54, 6),
            _row("balanced", 0, 0.82, 0.28, 0.28, 0.28, 5),
            _row("balanced", 1, 0.81, 0.29, 0.29, 0.29, 5),
            _row("centroid_specialist", 0, 0.70, 0.10, 0.35, 0.35, 4),
            _row("centroid_specialist", 1, 0.71, 0.11, 0.34, 0.34, 4),
        ]
    )
    result = select_niche_recovery_protocol(metrics)
    assert result.candidate == "balanced"
    assert set(result.pareto_front) == {"balanced", "centroid_specialist", "overlap_specialist"}


def test_generalization_gate_rejects_ecologically_attractive_but_nontransferring_candidate():
    metrics = pd.DataFrame(
        [
            _row("ecology_only", 0, 0.94, 0.10, 0.10, 0.10, 3, auc=0.61, or10=0.42),
            _row("ecology_only", 1, 0.93, 0.11, 0.11, 0.11, 3, auc=0.62, or10=0.40),
            _row("credible_a", 0, 0.82, 0.24, 0.25, 0.24, 4, auc=0.82, or10=0.13),
            _row("credible_a", 1, 0.81, 0.25, 0.24, 0.25, 4, auc=0.81, or10=0.14),
            _row("credible_b", 0, 0.84, 0.22, 0.22, 0.22, 5, auc=0.815, or10=0.12),
            _row("credible_b", 1, 0.83, 0.23, 0.23, 0.23, 5, auc=0.81, or10=0.13),
        ]
    )
    pure = select_niche_recovery_protocol(metrics)
    assert pure.candidate == "ecology_only"

    gated = select_generalization_gated_niche_recovery_protocol(
        metrics,
        minimum_auc_tolerance=0.02,
        auc_sem_multiplier=0.0,
        max_mean_or10=0.20,
    )
    assert "ecology_only" not in gated.eligible_candidates
    assert set(gated.eligible_candidates) == {"credible_a", "credible_b"}
    assert gated.candidate == "credible_b"


def test_auc_gate_is_tolerance_not_auc_maximization():
    metrics = pd.DataFrame(
        [
            _row("best_auc", 0, 0.76, 0.30, 0.30, 0.30, 3, auc=0.830),
            _row("best_auc", 1, 0.75, 0.31, 0.31, 0.31, 3, auc=0.830),
            _row("near_auc_better_ecology", 0, 0.86, 0.18, 0.18, 0.18, 4, auc=0.821),
            _row("near_auc_better_ecology", 1, 0.85, 0.19, 0.19, 0.19, 4, auc=0.821),
        ]
    )
    gated = select_generalization_gated_niche_recovery_protocol(
        metrics,
        minimum_auc_tolerance=0.01,
        auc_sem_multiplier=0.0,
    )
    assert set(gated.eligible_candidates) == {"best_auc", "near_auc_better_ecology"}
    assert gated.candidate == "near_auc_better_ecology"
