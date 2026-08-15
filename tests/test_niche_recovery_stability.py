import numpy as np
import pandas as pd

from sdmr.niche_recovery_cv import ecological_surface_stability_profile
from sdmr.niche_recovery_stability import (
    select_generalization_gated_stable_niche_recovery_protocol,
    select_stable_niche_recovery_protocol,
)


def _row(
    candidate,
    fold,
    overlap,
    centroid,
    breadth,
    quantile,
    stability_rank_mean,
    stability_rank_min,
    stability_nrmse_mean,
    stability_nrmse_max,
    *,
    auc=0.7,
    n_predictors=4,
):
    return {
        "candidate": candidate,
        "fold": fold,
        "niche_overlap_schoener_d_pc12": overlap,
        "centroid_distance": centroid,
        "breadth_log_sd_error": breadth,
        "quantile_profile_error": quantile,
        "ecological_surface_stability_rank_mean": stability_rank_mean,
        "ecological_surface_stability_rank_min": stability_rank_min,
        "ecological_surface_stability_nrmse_mean": stability_nrmse_mean,
        "ecological_surface_stability_nrmse_max": stability_nrmse_max,
        "presence_rank": auc,
        "or10": 0.10,
        "n_predictors": n_predictors,
    }


def test_surface_stability_is_shape_based_not_raw_probability_scale():
    x = np.linspace(-2.0, 2.0, 101)
    base = 1.0 / (1.0 + np.exp(-x))
    affine_same_shape = 0.15 + 0.7 * base
    reversed_shape = affine_same_shape[::-1]

    same = ecological_surface_stability_profile([base, affine_same_shape])
    assert same["n_surface_stability_pairs"] == 1
    assert np.isclose(same["ecological_surface_stability_rank_mean"], 1.0)
    assert np.isclose(same["ecological_surface_stability_rank_min"], 1.0)
    assert np.isclose(same["ecological_surface_stability_nrmse_mean"], 0.0)
    assert np.isclose(same["ecological_surface_stability_nrmse_max"], 0.0)

    changed = ecological_surface_stability_profile([base, reversed_shape])
    assert changed["ecological_surface_stability_rank_mean"] < -0.99
    assert changed["ecological_surface_stability_nrmse_mean"] > 0.3


def test_stability_gate_cannot_rescue_mean_recovery_dominated_candidate():
    metrics = pd.DataFrame(
        [
            _row("good_recovery", 0, 0.84, 0.18, 0.18, 0.18, 0.90, 0.85, 0.08, 0.10),
            _row("good_recovery", 1, 0.83, 0.19, 0.19, 0.19, 0.90, 0.85, 0.08, 0.10),
            _row("stable_but_bad", 0, 0.60, 0.50, 0.50, 0.50, 0.999, 0.999, 0.001, 0.001),
            _row("stable_but_bad", 1, 0.61, 0.49, 0.49, 0.49, 0.999, 0.999, 0.001, 0.001),
        ]
    )
    result = select_stable_niche_recovery_protocol(metrics)
    assert result.candidate == "good_recovery"
    assert result.recovery_pareto_front == ("good_recovery",)
    assert result.stability_pareto_front == ("good_recovery",)


def test_surface_stability_breaks_recovery_pareto_tradeoff_without_super_score():
    metrics = pd.DataFrame(
        [
            # Stable is slightly worse on overlap but better on tail error.
            _row("stable", 0, 0.80, 0.20, 0.20, 0.17, 0.98, 0.96, 0.04, 0.06),
            _row("stable", 1, 0.80, 0.20, 0.20, 0.19, 0.98, 0.96, 0.04, 0.06),
            # Unstable has a mean-recovery tradeoff, so it remains on the first
            # Pareto front, but its inferred ecological surface changes by split.
            _row("unstable", 0, 0.84, 0.19, 0.19, 0.24, 0.55, 0.20, 0.24, 0.40),
            _row("unstable", 1, 0.84, 0.19, 0.19, 0.24, 0.55, 0.20, 0.24, 0.40),
        ]
    )
    result = select_stable_niche_recovery_protocol(metrics)
    assert set(result.recovery_pareto_front) == {"stable", "unstable"}
    assert result.stability_pareto_front == ("stable",)
    assert result.candidate == "stable"


def test_prediction_adequacy_precedes_surface_stability():
    metrics = pd.DataFrame(
        [
            _row("stable_nontransfer", 0, 0.95, 0.10, 0.10, 0.10, 0.999, 0.999, 0.001, 0.001, auc=0.49),
            _row("stable_nontransfer", 1, 0.95, 0.10, 0.10, 0.10, 0.999, 0.999, 0.001, 0.001, auc=0.49),
            _row("stable_transfer", 0, 0.80, 0.20, 0.20, 0.20, 0.98, 0.97, 0.04, 0.05, auc=0.62),
            _row("stable_transfer", 1, 0.81, 0.19, 0.19, 0.19, 0.98, 0.97, 0.04, 0.05, auc=0.62),
            _row("unstable_transfer", 0, 0.84, 0.18, 0.18, 0.25, 0.50, 0.10, 0.25, 0.42, auc=0.75),
            _row("unstable_transfer", 1, 0.84, 0.18, 0.18, 0.25, 0.50, 0.10, 0.25, 0.42, auc=0.75),
        ]
    )
    result = select_generalization_gated_stable_niche_recovery_protocol(
        metrics,
        chance_auc=0.50,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=0.0,
    )
    assert "stable_nontransfer" not in result.eligible_candidates
    assert set(result.eligible_candidates) == {"stable_transfer", "unstable_transfer"}
    assert result.candidate == "stable_transfer"
