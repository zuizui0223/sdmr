import numpy as np


def test_occurrence_distribution_components_are_exact_and_normalized():
    from sdmr.process_id.known_truth.occurrence_oracle import occurrence_distribution_components
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=601, n_cells=900, n_occurrences=90, n_background=300
    )
    dist = occurrence_distribution_components(world)
    assert np.isclose(dist.q_occurrence.sum(), 1.0)
    assert np.isclose(dist.q_background.sum(), 1.0)
    assert np.isclose(dist.mixture.sum(), 1.0)
    assert np.all((dist.posterior > 0.0) & (dist.posterior < 1.0))
    expected_q1 = world.environment["true_suitability"].to_numpy() * world.environment["sampling_effort"].to_numpy()
    expected_q1 = expected_q1 / expected_q1.sum()
    expected_q0 = world.environment["sampling_effort"].to_numpy()
    expected_q0 = expected_q0 / expected_q0.sum()
    np.testing.assert_allclose(dist.q_occurrence, expected_q1)
    np.testing.assert_allclose(dist.q_background, expected_q0)


def test_occurrence_oracle_returns_one_state_per_process_with_bayes_regret():
    from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=602, n_cells=900, n_occurrences=90, n_background=300
    )
    result = evaluate_occurrence_oracle_states(
        world, n_splits=3, approximation_tolerance=0.05
    )
    assert tuple(result.states["process"]) == world.process_universe
    assert len(result.evidence) == len(world.process_universe) * 3
    assert result.states["state"].isin(
        {"replaceable", "contributory", "required", "unresolved", "unavailable"}
    ).all()
    assert (result.states["mean_full_regret"] >= -1e-9).all()
    assert {
        "mean_bayes_score", "mean_full_score", "mean_process_free_score",
        "mean_delta", "delta_sem", "mean_full_regret",
        "full_numerically_adequate", "closure_predictors",
    }.issubset(result.states.columns)


def test_occurrence_oracle_abstains_for_identical_shared_carrier_closures():
    from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "shared_carrier", seed=603, n_cells=900, n_occurrences=90, n_background=300
    )
    result = evaluate_occurrence_oracle_states(
        world, n_splits=3, approximation_tolerance=0.05
    )
    pair = result.states.loc[result.states["process"].isin(["thermal", "water"])]
    assert set(pair["state"]) == {"unresolved"}
    assert set(pair["reason"]).issubset(
        {"occurrence_distribution_oracle", "identical_shared_carrier_closure"}
    )


def test_occurrence_oracle_marks_hidden_driver_world_unavailable_when_full_representation_cannot_approximate_bayes():
    from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "omitted_driver", seed=604, n_cells=1000, n_occurrences=100, n_background=320
    )
    result = evaluate_occurrence_oracle_states(
        world, n_splits=3, approximation_tolerance=0.01
    )
    assert set(result.states["state"]) == {"unavailable"}
    assert (~result.states["full_numerically_adequate"]).all()


def test_occurrence_oracle_preserves_declared_observation_nonseparability():
    from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "observation_confounded", seed=605, n_cells=900, n_occurrences=90, n_background=300
    )
    result = evaluate_occurrence_oracle_states(
        world, n_splits=3, approximation_tolerance=0.05
    )
    thermal = result.states.loc[result.states["process"].eq("thermal")].iloc[0]
    assert thermal["state"] == "unresolved"
    assert thermal["reason"] == "observation_process_not_separable"
