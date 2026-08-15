import pandas as pd

from sdmr.niche_recovery_selection import select_niche_recovery_protocol


def _row(candidate, fold, d, centroid, breadth, quantile, n_predictors):
    return {
        "candidate": candidate,
        "fold": fold,
        "niche_overlap_schoener_d_pc12": d,
        "centroid_distance": centroid,
        "breadth_log_sd_error": breadth,
        "quantile_profile_error": quantile,
        "n_predictors": n_predictors,
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
