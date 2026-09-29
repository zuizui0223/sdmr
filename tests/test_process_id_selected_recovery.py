import pandas as pd
import pytest


def test_selected_recovery_summary_separates_split_modes_and_safety():
    from sdmr.process_id.known_truth.selected_recovery import summarize_selected_recovery

    rows = pd.DataFrame([
        {"learner":"linear","split_mode":"spatial","odo_state":"contributory","finite_state":"contributory","full_log_score":-0.68,"delta_mean":0.02,"delta_sem":0.004},
        {"learner":"linear","split_mode":"spatial","odo_state":"contributory","finite_state":"unresolved","full_log_score":-0.69,"delta_mean":0.015,"delta_sem":0.010},
        {"learner":"linear","split_mode":"spatial","odo_state":"replaceable","finite_state":"replaceable","full_log_score":-0.68,"delta_mean":0.0,"delta_sem":0.002},
        {"learner":"linear","split_mode":"spatial","odo_state":"unresolved","finite_state":"unresolved","full_log_score":-0.68,"delta_mean":0.0,"delta_sem":0.002},
        {"learner":"hgb","split_mode":"random_cell","odo_state":"contributory","finite_state":"contributory","full_log_score":-0.65,"delta_mean":0.03,"delta_sem":0.005},
        {"learner":"hgb","split_mode":"random_cell","odo_state":"replaceable","finite_state":"contributory","full_log_score":-0.66,"delta_mean":0.02,"delta_sem":0.005},
        {"learner":"hgb","split_mode":"random_cell","odo_state":"unresolved","finite_state":"replaceable","full_log_score":-0.67,"delta_mean":0.0,"delta_sem":0.002},
    ])
    out = summarize_selected_recovery(rows).set_index(["learner","split_mode"])
    assert out.loc[("linear","spatial"),"positive_recovery"] == 0.5
    assert out.loc[("linear","spatial"),"false_positive_rate"] == 0.0
    assert out.loc[("linear","spatial"),"overresolution_rate"] == 0.0
    assert out.loc[("hgb","random_cell"),"positive_recovery"] == 1.0
    assert out.loc[("hgb","random_cell"),"false_positive_rate"] == 1.0
    assert out.loc[("hgb","random_cell"),"overresolution_rate"] == 1.0


def test_selected_recovery_retest_is_deterministic_and_uses_shallow3():
    from sdmr.process_id.known_truth.selected_recovery import run_selected_recovery_retest

    kwargs = dict(
        seeds=(1001,),
        worlds=("unique_process",),
        learners=("linear","hgb"),
        split_modes=("spatial","random_cell"),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        hgb_profile="shallow3",
        odo_approximation_tolerance=0.05,
        expected_odo_state_hash=None,
    )
    first = run_selected_recovery_retest(**kwargs)
    second = run_selected_recovery_retest(**kwargs)
    pd.testing.assert_frame_equal(first.states, second.states)
    pd.testing.assert_frame_equal(first.metrics, second.metrics)
    assert set(first.states["split_mode"]) == {"spatial","random_cell"}
    assert set(first.states["learner"]) == {"linear","hgb"}
    hgb = first.states.loc[first.states["learner"].eq("hgb")]
    assert set(hgb["hgb_profile"]) == {"shallow3"}


def test_selected_recovery_fails_closed_on_odo_state_hash_drift():
    from sdmr.process_id.known_truth.selected_recovery import run_selected_recovery_retest

    with pytest.raises(ValueError, match="ODO state hash"):
        run_selected_recovery_retest(
            seeds=(1002,),
            worlds=("unique_process",),
            learners=("linear",),
            split_modes=("spatial",),
            n_cells=700,
            n_occurrences=70,
            n_background=220,
            n_splits=2,
            odo_approximation_tolerance=0.05,
            expected_odo_state_hash="deadbeef",
        )
