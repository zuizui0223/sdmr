import math

import numpy as np
import pandas as pd
import pytest


def test_full_system_information_summary_uses_zero_gain_boundary():
    from sdmr.process_id.known_truth.full_system_gate import summarize_full_system_gain

    positive = summarize_full_system_gain(
        np.array([-0.650, -0.660, -0.655]),
        sem_multiplier=1.0,
        adequacy_floor=-0.75,
    )
    assert positive["mean_gain_over_null"] > 0
    assert positive["lower_gain_over_null"] > 0
    assert positive["information_adequate"] is True
    assert positive["absolute_adequate"] is True

    nullish = summarize_full_system_gain(
        np.array([-0.694, -0.696, -0.695]),
        sem_multiplier=1.0,
        adequacy_floor=-0.75,
    )
    assert nullish["mean_gain_over_null"] < 0
    assert nullish["information_adequate"] is False
    assert nullish["absolute_adequate"] is True


def test_full_system_information_summary_is_conservative_under_fold_uncertainty():
    from sdmr.process_id.known_truth.full_system_gate import summarize_full_system_gain

    result = summarize_full_system_gain(
        np.array([-0.650, -0.720, -0.670]),
        sem_multiplier=1.0,
        adequacy_floor=-0.75,
    )
    assert result["mean_gain_over_null"] > 0
    assert result["lower_gain_over_null"] <= 0
    assert result["information_adequate"] is False


def test_full_system_information_evaluation_is_deterministic():
    from sdmr.process_id.known_truth.full_system_gate import evaluate_full_system_information
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=1301, n_cells=800, n_occurrences=80, n_background=260
    )
    first = evaluate_full_system_information(
        world,
        n_splits=2,
        learner="hgb",
        hgb_profile="shallow3",
        split_mode="random_cell",
    )
    second = evaluate_full_system_information(
        world,
        n_splits=2,
        learner="hgb",
        hgb_profile="shallow3",
        split_mode="random_cell",
    )
    pd.testing.assert_frame_equal(first.fold_scores, second.fold_scores)
    assert first.summary == second.summary
    assert set(first.fold_scores["split_mode"]) == {"random_cell"}


def test_full_system_information_gate_rejects_unknown_split():
    from sdmr.process_id.known_truth.full_system_gate import evaluate_full_system_information
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=1302, n_cells=700, n_occurrences=70, n_background=220
    )
    with pytest.raises(ValueError, match="split_mode"):
        evaluate_full_system_information(
            world,
            n_splits=2,
            learner="hgb",
            hgb_profile="shallow3",
            split_mode="checkerboard",
        )
