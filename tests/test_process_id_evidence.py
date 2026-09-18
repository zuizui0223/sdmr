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
    result = evaluate_occurrence_processes(world, n_splits=3, adequacy_floor=-2.0)
    pair = result.states.loc[result.states["process"].isin(["thermal", "water"])]
    assert set(pair["state"]) == {"unresolved"}
    assert set(pair["reason"]).issubset({"interval_process_challenge", "identical_shared_carrier_closure"})


def test_equal_prior_score_fit_is_calibrated_under_imbalanced_null_training_sample():
    import math
    import numpy as np
    import pandas as pd
    from sdmr.process_id.evidence import _fit_score

    train = pd.DataFrame({
        "x": np.zeros(780),
        "label": np.r_[np.ones(180, dtype=int), np.zeros(600, dtype=int)],
    })
    test = pd.DataFrame({
        "x": np.zeros(200),
        "label": np.r_[np.ones(100, dtype=int), np.zeros(100, dtype=int)],
    })
    score = _fit_score(train, test, ("x",), C=1.0)
    assert abs(score + math.log(2.0)) < 0.01
