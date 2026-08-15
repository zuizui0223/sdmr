import pandas as pd

from sdmr.niche_recovery_selection import (
    select_generalization_gated_niche_recovery_protocol,
    select_generalization_gated_robust_niche_recovery_protocol,
    select_niche_recovery_protocol,
    select_robust_niche_recovery_protocol,
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


def test_robustness_gate_rejects_mean_attractive_candidate_with_bad_worst_fold():
    metrics = pd.DataFrame(
        [
            _row("stable", 0, 0.79, 0.21, 0.21, 0.21, 4),
            _row("stable", 1, 0.81, 0.19, 0.19, 0.19, 4),
            _row("unstable", 0, 0.99, 0.01, 0.01, 0.05, 4),
            _row("unstable", 1, 0.65, 0.37, 0.37, 0.45, 4),
        ]
    )

    # Mean recovery likes the unstable candidate: it wins overlap, centroid and
    # breadth on average, while stable wins quantile recovery.
    pure = select_niche_recovery_protocol(metrics)
    assert pure.candidate == "unstable"

    # Robustness is a separate stage. Both candidates survive the mean-recovery
    # Pareto gate, but stable dominates the ecological worst fold on all axes.
    robust = select_robust_niche_recovery_protocol(metrics)
    assert set(robust.recovery_pareto_front) == {"stable", "unstable"}
    assert robust.robustness_pareto_front == ("stable",)
    assert robust.candidate == "stable"
    stable = robust.summary.loc[robust.summary["candidate"].eq("stable")].iloc[0]
    assert float(stable["worst_fold__niche_overlap_schoener_d_pc12"]) == 0.79
    assert float(stable["worst_fold__quantile_profile_error"]) == 0.21


def test_generalization_gate_rejects_ecologically_attractive_but_nontransferring_candidate():
    metrics = pd.DataFrame(
        [
            _row("ecology_only", 0, 0.94, 0.10, 0.10, 0.10, 3, auc=0.49, or10=0.42),
            _row("ecology_only", 1, 0.93, 0.11, 0.11, 0.11, 3, auc=0.50, or10=0.40),
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
        chance_auc=0.50,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=0.0,
        max_mean_or10=0.20,
    )
    assert "ecology_only" not in gated.eligible_candidates
    assert set(gated.eligible_candidates) == {"credible_a", "credible_b"}
    assert gated.candidate == "credible_b"
    assert gated.auc_gate_floor == 0.51


def test_generalization_then_robustness_preserves_stage_order():
    metrics = pd.DataFrame(
        [
            _row("nontransfer", 0, 0.99, 0.01, 0.01, 0.01, 3, auc=0.49),
            _row("nontransfer", 1, 0.99, 0.01, 0.01, 0.01, 3, auc=0.49),
            _row("stable", 0, 0.79, 0.21, 0.21, 0.21, 4, auc=0.62),
            _row("stable", 1, 0.81, 0.19, 0.19, 0.19, 4, auc=0.62),
            _row("unstable", 0, 0.99, 0.01, 0.01, 0.05, 4, auc=0.72),
            _row("unstable", 1, 0.65, 0.37, 0.37, 0.45, 4, auc=0.72),
        ]
    )
    result = select_generalization_gated_robust_niche_recovery_protocol(
        metrics,
        chance_auc=0.50,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=0.0,
    )
    assert "nontransfer" not in result.eligible_candidates
    assert set(result.eligible_candidates) == {"stable", "unstable"}
    assert result.robust_selection.candidate == "stable"
    assert result.candidate == "stable"


def test_auc_gate_is_adequacy_not_auc_maximization():
    metrics = pd.DataFrame(
        [
            _row("best_auc", 0, 0.76, 0.30, 0.30, 0.30, 3, auc=0.830),
            _row("best_auc", 1, 0.75, 0.31, 0.31, 0.31, 3, auc=0.830),
            _row("lower_auc_better_ecology", 0, 0.86, 0.18, 0.18, 0.18, 4, auc=0.620),
            _row("lower_auc_better_ecology", 1, 0.85, 0.19, 0.19, 0.19, 4, auc=0.620),
        ]
    )
    gated = select_generalization_gated_niche_recovery_protocol(
        metrics,
        chance_auc=0.50,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=0.0,
    )
    assert set(gated.eligible_candidates) == {"best_auc", "lower_auc_better_ecology"}
    assert gated.candidate == "lower_auc_better_ecology"


def test_auc_lower_evidence_bound_can_fail_uncertain_candidate():
    metrics = pd.DataFrame(
        [
            _row("stable", 0, 0.80, 0.20, 0.20, 0.20, 3, auc=0.62),
            _row("stable", 1, 0.79, 0.21, 0.21, 0.21, 3, auc=0.62),
            _row("uncertain", 0, 0.90, 0.10, 0.10, 0.10, 4, auc=0.90),
            _row("uncertain", 1, 0.89, 0.11, 0.11, 0.11, 4, auc=0.14),
        ]
    )
    gated = select_generalization_gated_niche_recovery_protocol(
        metrics,
        chance_auc=0.50,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=1.0,
    )
    assert gated.eligible_candidates == ("stable",)
    assert gated.candidate == "stable"
