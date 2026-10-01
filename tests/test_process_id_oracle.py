import pandas as pd

from sdmr.oracle_process_identifiability import (
    ORACLE_CONTESTED,
    ORACLE_CONTRIBUTORY,
    ORACLE_REPLACEABLE,
    ORACLE_REQUIRED,
    ORACLE_UNAVAILABLE,
)


def test_old_oracle_states_map_to_new_process_states():
    from sdmr.process_id.known_truth.oracle import map_oracle_state

    assert map_oracle_state(ORACLE_REPLACEABLE) == "replaceable"
    assert map_oracle_state(ORACLE_CONTRIBUTORY) == "contributory"
    assert map_oracle_state(ORACLE_REQUIRED) == "required"
    assert map_oracle_state(ORACLE_CONTESTED) == "unresolved"
    assert map_oracle_state(ORACLE_UNAVAILABLE) == "unavailable"


def test_identical_positive_shared_carrier_closures_abstain():
    from sdmr.process_id.known_truth.oracle import apply_shared_carrier_abstention

    states = pd.DataFrame([
        {"process": "thermal", "state": "contributory", "oracle_raw_state": ORACLE_CONTRIBUTORY, "closure_predictors": "pet_shared", "reason": "oracle_contributory"},
        {"process": "water", "state": "required", "oracle_raw_state": ORACLE_REQUIRED, "closure_predictors": "pet_shared", "reason": "oracle_required"},
        {"process": "seasonality", "state": "replaceable", "oracle_raw_state": ORACLE_REPLACEABLE, "closure_predictors": "seasonality", "reason": "oracle_replaceable"},
    ])
    out = apply_shared_carrier_abstention(states)
    thermal = out.loc[out["process"].eq("thermal")].iloc[0]
    water = out.loc[out["process"].eq("water")].iloc[0]
    assert thermal["state"] == "unresolved"
    assert water["state"] == "unresolved"
    assert thermal["reason"] == "identical_shared_carrier_closure"
    assert water["reason"] == "identical_shared_carrier_closure"


def test_w1_thermal_oracle_is_not_replaceable():
    from sdmr.process_id.known_truth.oracle import evaluate_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("unique_process", seed=101, n_cells=900, n_occurrences=90, n_background=300)
    result = evaluate_oracle_states(world, n_splits=3, baseline_r2_floor=0.70)
    thermal = result.loc[result["process"].eq("thermal"), "state"].iloc[0]
    assert thermal in {"contributory", "required"}


def test_w4_seasonality_oracle_is_replaceable():
    from sdmr.process_id.known_truth.oracle import evaluate_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("null_correlated", seed=102, n_cells=900, n_occurrences=90, n_background=300)
    result = evaluate_oracle_states(world, n_splits=3, baseline_r2_floor=0.70)
    state = result.loc[result["process"].eq("seasonality"), "state"].iloc[0]
    assert state == "replaceable"


def test_w7_oracle_is_unavailable_when_declared_predictors_cannot_reconstruct_truth():
    from sdmr.process_id.known_truth.oracle import evaluate_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("omitted_driver", seed=103, n_cells=900, n_occurrences=90, n_background=300)
    result = evaluate_oracle_states(world, n_splits=3, baseline_r2_floor=0.70)
    assert set(result["state"]) == {"unavailable"}
