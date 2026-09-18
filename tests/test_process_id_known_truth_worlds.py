import numpy as np
import pandas as pd

from sdmr.process_information_closure import process_information_closure


def test_known_truth_world_names_are_frozen():
    from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS

    assert KNOWN_TRUTH_WORLDS == (
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "observation_confounded",
        "omitted_driver",
        "geographic_shift",
    )


def test_world_simulation_is_deterministic():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    a = simulate_process_world("unique_process", seed=71, n_cells=1200, n_occurrences=120, n_background=420)
    b = simulate_process_world("unique_process", seed=71, n_cells=1200, n_occurrences=120, n_background=420)
    pd.testing.assert_frame_equal(a.environment, b.environment)
    np.testing.assert_allclose(a.true_suitability, b.true_suitability)
    pd.testing.assert_frame_equal(a.occurrences, b.occurrences)
    pd.testing.assert_frame_equal(a.background, b.background)


def test_w1_has_nonredundant_generating_thermal_signal():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("unique_process", seed=4, n_cells=1800, n_occurrences=180, n_background=600)
    assert world.generating_processes == ("thermal",)
    corr = np.corrcoef(world.environment["temperature"], world.true_suitability)[0, 1]
    assert corr > 0.70


def test_w2_generating_thermal_is_deliberately_redundant_with_water():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("redundant_representation", seed=5, n_cells=1800, n_occurrences=180, n_background=600)
    assert world.generating_processes == ("thermal",)
    corr = np.corrcoef(world.environment["temperature"], world.environment["water"])[0, 1]
    assert corr > 0.97


def test_w3_thermal_and_water_have_identical_shared_carrier_closure():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("shared_carrier", seed=6, n_cells=1600, n_occurrences=160, n_background=550)
    thermal = process_information_closure(world.process_registry, "thermal")
    water = process_information_closure(world.process_registry, "water")
    assert thermal == ("pet_shared",)
    assert water == ("pet_shared",)


def test_w4_nongenerating_seasonality_is_strongly_correlated_with_thermal():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("null_correlated", seed=7, n_cells=1800, n_occurrences=180, n_background=600)
    assert "seasonality" not in world.generating_processes
    corr = np.corrcoef(world.environment["temperature"], world.environment["seasonality"])[0, 1]
    assert corr > 0.95


def test_w5_declares_joint_thermal_water_generation():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("interaction", seed=8, n_cells=1800, n_occurrences=180, n_background=600)
    assert world.generating_processes == ("thermal", "water")
    interaction = world.environment["temperature"].to_numpy() * world.environment["water"].to_numpy()
    assert abs(np.corrcoef(interaction, world.true_suitability)[0, 1]) > 0.20


def test_w6_marks_observation_confounded_thermal_as_unresolved_by_design():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("observation_confounded", seed=9, n_cells=1800, n_occurrences=180, n_background=600)
    assert world.observation_unresolved_processes == ("thermal",)


def test_w7_hidden_driver_is_outside_declared_predictor_universe():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("omitted_driver", seed=10, n_cells=1800, n_occurrences=180, n_background=600)
    assert "hidden_driver" in world.environment.columns
    assert "hidden_driver" not in world.predictor_universe
    corr = np.corrcoef(world.environment["hidden_driver"], world.true_suitability)[0, 1]
    assert corr > 0.70


def test_w8_proxy_relationship_flips_in_heldout_geography():
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("geographic_shift", seed=11, n_cells=2400, n_occurrences=200, n_background=700)
    train = world.model_pool_mask
    heldout = ~world.model_pool_mask
    train_corr = np.corrcoef(
        world.environment.loc[train, "temperature"],
        world.environment.loc[train, "elevation_proxy"],
    )[0, 1]
    heldout_corr = np.corrcoef(
        world.environment.loc[heldout, "temperature"],
        world.environment.loc[heldout, "elevation_proxy"],
    )[0, 1]
    assert train_corr > 0.85
    assert heldout_corr < -0.85
