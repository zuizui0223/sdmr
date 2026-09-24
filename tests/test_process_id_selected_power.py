import pandas as pd
import pytest


def test_selected_power_summary_tracks_recovery_and_sem_by_split_and_multiplier():
    from sdmr.process_id.known_truth.selected_power import summarize_selected_power

    rows = pd.DataFrame([
        {"split_mode":"spatial","multiplier":1,"finite_state":"contributory","delta_mean":0.020,"delta_sem":0.010,"full_log_score":-0.68},
        {"split_mode":"spatial","multiplier":1,"finite_state":"unresolved","delta_mean":0.018,"delta_sem":0.012,"full_log_score":-0.69},
        {"split_mode":"spatial","multiplier":2,"finite_state":"contributory","delta_mean":0.021,"delta_sem":0.006,"full_log_score":-0.67},
        {"split_mode":"spatial","multiplier":2,"finite_state":"contributory","delta_mean":0.020,"delta_sem":0.005,"full_log_score":-0.68},
        {"split_mode":"random_cell","multiplier":1,"finite_state":"unresolved","delta_mean":0.017,"delta_sem":0.011,"full_log_score":-0.66},
        {"split_mode":"random_cell","multiplier":1,"finite_state":"replaceable","delta_mean":0.007,"delta_sem":0.002,"full_log_score":-0.67},
    ])
    out = summarize_selected_power(rows).set_index(["split_mode","multiplier"])

    assert out.loc[("spatial",1),"positive_recovery"] == 0.5
    assert out.loc[("spatial",1),"unresolved_rate"] == 0.5
    assert out.loc[("spatial",2),"positive_recovery"] == 1.0
    assert out.loc[("spatial",2),"mean_delta_sem"] == pytest.approx(0.0055)
    assert out.loc[("random_cell",1),"replaceable_rate"] == 0.5


def test_selected_power_curve_is_deterministic_and_uses_only_odo_positive_processes():
    from sdmr.process_id.known_truth.selected_power import run_selected_power_curve

    kwargs = dict(
        seeds=(1101,),
        worlds=("unique_process",),
        split_modes=("spatial","random_cell"),
        sample_multipliers=(1,2),
        sampling_replicates=(0,1),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        hgb_profile="shallow3",
        odo_approximation_tolerance=0.05,
        expected_odo_state_hash=None,
    )
    first = run_selected_power_curve(**kwargs)
    second = run_selected_power_curve(**kwargs)

    pd.testing.assert_frame_equal(first.states, second.states)
    pd.testing.assert_frame_equal(first.metrics, second.metrics)
    assert set(first.states["split_mode"]) == {"spatial","random_cell"}
    assert set(first.states["multiplier"]) == {1,2}
    assert set(first.states["replicate"]) == {0,1}
    assert set(first.states["hgb_profile"]) == {"shallow3"}
    assert first.states["odo_state"].isin({"contributory","required"}).all()


def test_selected_power_curve_fails_closed_on_odo_hash_drift():
    from sdmr.process_id.known_truth.selected_power import run_selected_power_curve

    with pytest.raises(ValueError, match="ODO state hash"):
        run_selected_power_curve(
            seeds=(1102,),
            worlds=("unique_process",),
            split_modes=("spatial",),
            sample_multipliers=(1,),
            sampling_replicates=(0,),
            n_cells=700,
            n_occurrences=70,
            n_background=220,
            n_splits=2,
            odo_approximation_tolerance=0.05,
            expected_odo_state_hash="deadbeef",
        )
