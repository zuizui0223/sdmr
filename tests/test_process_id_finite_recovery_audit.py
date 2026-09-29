import pandas as pd


def test_summarize_baseline_against_odo_separates_recovery_and_safety():
    from sdmr.process_id.known_truth.finite_recovery_audit import (
        summarize_baseline_against_odo,
    )

    rows = pd.DataFrame([
        {"learner": "linear", "odo_state": "contributory", "finite_state": "contributory"},
        {"learner": "linear", "odo_state": "contributory", "finite_state": "unresolved"},
        {"learner": "linear", "odo_state": "replaceable", "finite_state": "replaceable"},
        {"learner": "linear", "odo_state": "replaceable", "finite_state": "contributory"},
        {"learner": "linear", "odo_state": "unresolved", "finite_state": "unresolved"},
        {"learner": "quadratic", "odo_state": "contributory", "finite_state": "replaceable"},
        {"learner": "quadratic", "odo_state": "replaceable", "finite_state": "replaceable"},
        {"learner": "quadratic", "odo_state": "unresolved", "finite_state": "replaceable"},
    ])
    out = summarize_baseline_against_odo(rows).set_index("learner")
    assert out.loc["linear", "positive_recovery"] == 0.5
    assert out.loc["linear", "false_positive_rate"] == 0.5
    assert out.loc["linear", "overresolution_rate"] == 0.0
    assert out.loc["quadratic", "positive_recovery"] == 0.0
    assert out.loc["quadratic", "false_positive_rate"] == 0.0
    assert out.loc["quadratic", "overresolution_rate"] == 1.0


def test_summarize_hgb_power_curve_tracks_state_rates_and_delta():
    from sdmr.process_id.known_truth.finite_recovery_audit import (
        summarize_hgb_power_curve,
    )

    rows = pd.DataFrame([
        {"multiplier": 1, "finite_state": "contributory", "delta_mean": 0.02},
        {"multiplier": 1, "finite_state": "unresolved", "delta_mean": 0.01},
        {"multiplier": 2, "finite_state": "contributory", "delta_mean": 0.03},
        {"multiplier": 2, "finite_state": "contributory", "delta_mean": 0.04},
    ])
    out = summarize_hgb_power_curve(rows).set_index("multiplier")
    assert out.loc[1, "positive_recovery"] == 0.5
    assert out.loc[1, "unresolved_rate"] == 0.5
    assert out.loc[2, "positive_recovery"] == 1.0
    assert out.loc[2, "mean_delta"] == 0.035


def test_small_finite_recovery_audit_is_deterministic_and_uses_odo_positive_denominator():
    from sdmr.process_id.known_truth.finite_recovery_audit import (
        run_finite_recovery_audit,
    )

    kwargs = dict(
        seeds=(801,),
        worlds=("unique_process",),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        baseline_learners=("linear", "quadratic", "hgb"),
        sample_multipliers=(1, 2),
        sampling_replicates=(0, 1),
        odo_approximation_tolerance=0.05,
    )
    first = run_finite_recovery_audit(**kwargs)
    second = run_finite_recovery_audit(**kwargs)

    pd.testing.assert_frame_equal(first.baseline_states, second.baseline_states)
    pd.testing.assert_frame_equal(first.power_states, second.power_states)
    pd.testing.assert_frame_equal(first.baseline_metrics, second.baseline_metrics)
    pd.testing.assert_frame_equal(first.power_metrics, second.power_metrics)

    assert set(first.baseline_states["learner"]) == {"linear", "quadratic", "hgb"}
    assert set(first.power_states["learner"]) == {"hgb"}
    assert set(first.power_states["multiplier"]) == {1, 2}
    assert first.power_states["odo_state"].isin({"contributory", "required"}).all()
    assert first.power_states[["world", "seed", "process", "multiplier", "replicate"]].duplicated().sum() == 0


def test_finite_recovery_audit_propagates_named_hgb_profile():
    from sdmr.process_id.known_truth.finite_recovery_audit import (
        run_finite_recovery_audit,
    )

    result = run_finite_recovery_audit(
        seeds=(802,),
        worlds=("unique_process",),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        baseline_learners=("hgb",),
        sample_multipliers=(1,),
        sampling_replicates=(0,),
        odo_approximation_tolerance=0.05,
        hgb_profile="shallow3",
    )
    assert set(result.baseline_states["hgb_profile"]) == {"shallow3"}
    if not result.power_states.empty:
        assert set(result.power_states["hgb_profile"]) == {"shallow3"}
