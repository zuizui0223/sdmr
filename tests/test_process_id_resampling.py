from dataclasses import replace

import pandas as pd


def test_resample_world_observations_is_deterministic_and_preserves_ecology():
    from sdmr.process_id.known_truth.resampling import resample_world_observations
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=701, n_cells=900, n_occurrences=90, n_background=300
    )
    first = resample_world_observations(
        world, n_occurrences=180, n_background=600, sampling_seed=11
    )
    second = resample_world_observations(
        world, n_occurrences=180, n_background=600, sampling_seed=11
    )

    pd.testing.assert_frame_equal(first.environment, world.environment)
    pd.testing.assert_frame_equal(first.environment, second.environment)
    pd.testing.assert_frame_equal(first.occurrences, second.occurrences)
    pd.testing.assert_frame_equal(first.background, second.background)
    assert first.process_registry.equals(world.process_registry)
    assert first.process_universe == world.process_universe
    assert first.predictor_universe == world.predictor_universe
    assert len(first.occurrences) == 180
    assert len(first.background) == 600


def test_resampling_allows_repeated_cells_but_assigns_unique_sample_ids():
    from sdmr.process_id.known_truth.resampling import resample_world_observations
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=702, n_cells=600, n_occurrences=60, n_background=200
    )
    resampled = resample_world_observations(
        world, n_occurrences=720, n_background=2400, sampling_seed=12
    )
    assert resampled.occurrences["sample_id"].is_unique
    assert resampled.background["sample_id"].is_unique
    assert resampled.occurrences["cell_id"].duplicated().any()
    assert resampled.background["cell_id"].duplicated().any()


def test_resampling_uses_complete_distribution_not_existing_sample_rows():
    from sdmr.process_id.known_truth.resampling import resample_world_observations
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=703, n_cells=900, n_occurrences=90, n_background=300
    )
    altered = replace(
        world,
        occurrences=world.occurrences.iloc[:10].copy(),
        background=world.background.iloc[:10].copy(),
    )
    first = resample_world_observations(
        world, n_occurrences=180, n_background=600, sampling_seed=13
    )
    second = resample_world_observations(
        altered, n_occurrences=180, n_background=600, sampling_seed=13
    )
    pd.testing.assert_frame_equal(first.occurrences, second.occurrences)
    pd.testing.assert_frame_equal(first.background, second.background)
