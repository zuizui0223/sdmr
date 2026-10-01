import pandas as pd


def test_hgb_regularization_profiles_are_frozen():
    from sdmr.process_id.known_truth.hgb_regularization_screen import HGB_PROFILES

    assert tuple(HGB_PROFILES) == ("current", "shallow7", "shallow3", "early7")
    assert HGB_PROFILES["current"]["max_leaf_nodes"] == 31
    assert HGB_PROFILES["shallow3"]["max_leaf_nodes"] == 3
    assert HGB_PROFILES["shallow3"]["min_samples_leaf"] == 40
    assert HGB_PROFILES["shallow3"]["l2_regularization"] == 1.0


def test_hgb_profile_selection_uses_test_logscore_and_world_split_guardrail_only():
    from sdmr.process_id.known_truth.hgb_regularization_screen import select_hgb_profile

    rows = pd.DataFrame([
        {"profile": "current", "world": "w1", "split_mode": "spatial", "dataset": "test", "balanced_log_score": -1.1},
        {"profile": "current", "world": "w1", "split_mode": "random_cell", "dataset": "test", "balanced_log_score": -1.0},
        {"profile": "shallow7", "world": "w1", "split_mode": "spatial", "dataset": "test", "balanced_log_score": -0.70},
        {"profile": "shallow7", "world": "w1", "split_mode": "random_cell", "dataset": "test", "balanced_log_score": -0.69},
        {"profile": "shallow3", "world": "w1", "split_mode": "spatial", "dataset": "test", "balanced_log_score": -0.68},
        {"profile": "shallow3", "world": "w1", "split_mode": "random_cell", "dataset": "test", "balanced_log_score": -0.67},
        {"profile": "early7", "world": "w1", "split_mode": "spatial", "dataset": "test", "balanced_log_score": -0.82},
        {"profile": "early7", "world": "w1", "split_mode": "random_cell", "dataset": "test", "balanced_log_score": -0.65},
    ])
    decision = select_hgb_profile(rows, adequacy_floor=-0.75, tie_margin=0.005)
    assert decision["selected_profile"] == "shallow3"
    assert set(decision["eligible_profiles"]) == {"shallow7", "shallow3"}


def test_hgb_profile_tie_break_prefers_lower_complexity():
    from sdmr.process_id.known_truth.hgb_regularization_screen import select_hgb_profile

    rows = pd.DataFrame([
        {"profile": "shallow7", "world": "w1", "split_mode": "spatial", "dataset": "test", "balanced_log_score": -0.650},
        {"profile": "shallow7", "world": "w1", "split_mode": "random_cell", "dataset": "test", "balanced_log_score": -0.650},
        {"profile": "shallow3", "world": "w1", "split_mode": "spatial", "dataset": "test", "balanced_log_score": -0.653},
        {"profile": "shallow3", "world": "w1", "split_mode": "random_cell", "dataset": "test", "balanced_log_score": -0.653},
    ])
    decision = select_hgb_profile(rows, adequacy_floor=-0.75, tie_margin=0.005)
    assert decision["selected_profile"] == "shallow3"


def test_hgb_regularization_screen_is_deterministic():
    from sdmr.process_id.known_truth.hgb_regularization_screen import (
        run_hgb_regularization_screen,
    )

    kwargs = dict(
        seeds=(901,),
        worlds=("unique_process",),
        split_modes=("random_cell",),
        n_cells=700,
        n_occurrences=70,
        n_background=220,
        n_splits=2,
    )
    first = run_hgb_regularization_screen(**kwargs)
    second = run_hgb_regularization_screen(**kwargs)
    pd.testing.assert_frame_equal(first, second)
    assert set(first["profile"]) == {"current", "shallow7", "shallow3", "early7"}
    assert set(first["dataset"]) == {"train", "test"}
