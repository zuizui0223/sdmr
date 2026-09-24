import pandas as pd
import pytest


def test_summarize_8x_safety_tracks_specificity_abstention_and_fail_closed():
    from sdmr.process_id.known_truth.safety_audit import summarize_safety

    rows = pd.DataFrame([
        {"split_mode":"random_cell","odo_state":"replaceable","finite_state":"replaceable","structural_refusal_expected":False},
        {"split_mode":"random_cell","odo_state":"replaceable","finite_state":"contributory","structural_refusal_expected":False},
        {"split_mode":"random_cell","odo_state":"unresolved","finite_state":"unresolved","structural_refusal_expected":True},
        {"split_mode":"random_cell","odo_state":"unresolved","finite_state":"replaceable","structural_refusal_expected":True},
        {"split_mode":"random_cell","odo_state":"unavailable","finite_state":"unavailable","structural_refusal_expected":False},
        {"split_mode":"random_cell","odo_state":"unavailable","finite_state":"required","structural_refusal_expected":False},
        {"split_mode":"random_cell","odo_state":"contributory","finite_state":"contributory","structural_refusal_expected":False},
        {"split_mode":"random_cell","odo_state":"required","finite_state":"unresolved","structural_refusal_expected":False},
    ])
    out = summarize_safety(rows).set_index("split_mode")
    row = out.loc["random_cell"]
    assert row["false_positive_rate"] == 0.5
    assert row["overresolution_rate"] == 0.5
    assert row["unavailable_favorable_rate"] == 0.5
    assert row["structural_refusal_violation_rate"] == 0.5
    assert row["positive_recovery"] == 0.5


def test_8x_safety_audit_is_deterministic_and_uses_full_odo_state_space():
    from sdmr.process_id.known_truth.safety_audit import run_8x_safety_audit

    kwargs = dict(
        seeds=(1201,),
        worlds=("unique_process","shared_carrier","observation_confounded","omitted_driver"),
        split_modes=("spatial","random_cell"),
        sampling_replicates=(0,1),
        multiplier=2,
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        hgb_profile="shallow3",
        odo_approximation_tolerance=0.05,
        expected_odo_state_hash=None,
    )
    first = run_8x_safety_audit(**kwargs)
    second = run_8x_safety_audit(**kwargs)
    pd.testing.assert_frame_equal(first.states, second.states)
    pd.testing.assert_frame_equal(first.metrics, second.metrics)
    assert set(first.states["split_mode"]) == {"spatial","random_cell"}
    assert set(first.states["replicate"]) == {0,1}
    assert first.states["odo_state"].isin(
        {"replaceable","contributory","required","unresolved","unavailable"}
    ).all()
    assert first.states["hgb_profile"].eq("shallow3").all()


def test_structural_refusal_flags_are_explicit():
    from sdmr.process_id.known_truth.safety_audit import structural_refusal_expected

    assert structural_refusal_expected("observation_confounded","thermal")
    assert structural_refusal_expected("shared_carrier","thermal")
    assert structural_refusal_expected("shared_carrier","water")
    assert not structural_refusal_expected("unique_process","thermal")


def test_8x_safety_audit_fails_closed_on_odo_hash_drift():
    from sdmr.process_id.known_truth.safety_audit import run_8x_safety_audit

    with pytest.raises(ValueError, match="ODO state hash"):
        run_8x_safety_audit(
            seeds=(1202,),
            worlds=("unique_process",),
            split_modes=("random_cell",),
            sampling_replicates=(0,),
            multiplier=2,
            n_cells=700,
            n_occurrences=70,
            n_background=220,
            n_splits=2,
            odo_approximation_tolerance=0.05,
            expected_odo_state_hash="deadbeef",
        )
