import pandas as pd


def test_occurrence_evidence_is_paired_by_process_and_fold():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("unique_process", seed=201, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    expected = len(world.process_universe) * 3
    assert len(result.evidence) == expected
    assert result.evidence[["process", "fold"]].drop_duplicates().shape[0] == expected
    assert set(result.evidence["route"]) == {"logistic"}
    assert result.evidence["complete"].dtype == bool
    assert {"full_log_score", "knockout_log_score", "delta"}.issubset(result.evidence.columns)


def test_occurrence_evidence_uses_declared_process_closure():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("unique_process", seed=202, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    thermal = result.evidence.loc[result.evidence["process"].eq("thermal")]
    assert thermal["excluded_predictors"].nunique() == 1
    excluded = set(thermal["excluded_predictors"].iloc[0].split(","))
    assert {"temperature", "elevation_proxy", "pet_shared"}.issubset(excluded)
    assert "sampling_effort" not in excluded


def test_observation_confounded_process_is_forced_unresolved():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("observation_confounded", seed=203, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    row = result.states.loc[result.states["process"].eq("thermal")].iloc[0]
    assert row["state"] == "unresolved"
    assert row["reason"] == "observation_process_not_separable"


def test_occurrence_state_table_has_one_row_per_process():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("null_correlated", seed=204, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    assert tuple(result.states["process"]) == world.process_universe
    assert result.states["state"].isin({"replaceable", "contributory", "required", "unresolved", "unavailable"}).all()


def test_identical_shared_carrier_closure_abstains_in_occurrence_states():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "shared_carrier",
        seed=205,
        n_cells=1400,
        n_occurrences=160,
        n_background=520,
    )
    result = evaluate_occurrence_processes(world, n_splits=3)
    pair = result.states.loc[result.states["process"].isin(["thermal", "water"])]
    assert set(pair["state"]) == {"unresolved"}
    assert set(pair["reason"]) == {"identical_shared_carrier_closure"}
