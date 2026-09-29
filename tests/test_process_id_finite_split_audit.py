import pandas as pd


def test_split_geometry_summary_reports_positive_recovery_and_adequacy():
    from sdmr.process_id.known_truth.finite_split_audit import summarize_split_geometry

    rows = pd.DataFrame([
        {"split_mode":"spatial","finite_state":"unavailable","full_log_score":-1.2,"delta_mean":0.02,"delta_sem":0.03},
        {"split_mode":"spatial","finite_state":"unresolved","full_log_score":-0.70,"delta_mean":0.02,"delta_sem":0.02},
        {"split_mode":"random_cell","finite_state":"contributory","full_log_score":-0.68,"delta_mean":0.04,"delta_sem":0.01},
        {"split_mode":"random_cell","finite_state":"unresolved","full_log_score":-0.69,"delta_mean":0.02,"delta_sem":0.01},
    ])
    out=summarize_split_geometry(rows)
    spatial=out.loc[out["split_mode"].eq("spatial")].iloc[0]
    random=out.loc[out["split_mode"].eq("random_cell")].iloc[0]
    assert spatial["positive_recovery"] == 0.0
    assert spatial["unavailable_rate"] == 0.5
    assert random["positive_recovery"] == 0.5
    assert random["unavailable_rate"] == 0.0
    assert "mean_full_log_score" in out.columns


def test_split_geometry_audit_keeps_only_odo_positive_cells():
    from sdmr.process_id.known_truth.finite_split_audit import run_finite_split_geometry_audit

    result=run_finite_split_geometry_audit(
        seeds=(801,),
        worlds=("unique_process",),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
    )
    assert set(result.states["split_mode"]) == {"spatial","random_cell"}
    assert set(result.states["learner"]) == {"hgb"}
    assert result.states["odo_state"].isin({"contributory","required"}).all()
    assert result.states[["world","seed","process","split_mode"]].duplicated().sum() == 0
    assert set(result.metrics["split_mode"]) == {"spatial","random_cell"}


def test_split_geometry_audit_is_deterministic():
    from sdmr.process_id.known_truth.finite_split_audit import run_finite_split_geometry_audit

    kwargs=dict(
        seeds=(802,),
        worlds=("unique_process",),
        n_cells=700,
        n_occurrences=70,
        n_background=220,
        n_splits=2,
    )
    first=run_finite_split_geometry_audit(**kwargs)
    second=run_finite_split_geometry_audit(**kwargs)
    pd.testing.assert_frame_equal(first.states,second.states)
    pd.testing.assert_frame_equal(first.metrics,second.metrics)
