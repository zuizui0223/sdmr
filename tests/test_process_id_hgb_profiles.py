import pytest


def test_hgb_profile_registry_is_frozen_and_contains_screen_candidates():
    from sdmr.process_id.hgb_profiles import HGB_PROFILES

    assert tuple(HGB_PROFILES) == ("current", "shallow7", "shallow3", "early7")
    assert HGB_PROFILES["current"]["max_leaf_nodes"] == 31
    assert HGB_PROFILES["shallow3"]["max_leaf_nodes"] == 3
    assert HGB_PROFILES["shallow3"]["min_samples_leaf"] == 40
    assert HGB_PROFILES["shallow3"]["l2_regularization"] == 1.0


def test_hgb_profile_lookup_fails_closed():
    from sdmr.process_id.hgb_profiles import get_hgb_profile

    with pytest.raises(ValueError, match="unknown HGB profile"):
        get_hgb_profile("mystery")


def test_finite_hgb_accepts_named_profile_without_changing_default():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process",
        seed=913,
        n_cells=900,
        n_occurrences=90,
        n_background=300,
    )
    current_default = evaluate_occurrence_processes(
        world,
        n_splits=3,
        learner="hgb",
        adequacy_floor=-2.0,
    )
    current_named = evaluate_occurrence_processes(
        world,
        n_splits=3,
        learner="hgb",
        hgb_profile="current",
        adequacy_floor=-2.0,
    )
    assert current_default.evidence.equals(current_named.evidence)
    assert current_default.states.equals(current_named.states)

    shallow = evaluate_occurrence_processes(
        world,
        n_splits=3,
        learner="hgb",
        hgb_profile="shallow3",
        adequacy_floor=-2.0,
    )
    assert set(shallow.evidence["hgb_profile"]) == {"shallow3"}


def test_non_hgb_route_rejects_nondefault_hgb_profile():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process",
        seed=914,
        n_cells=900,
        n_occurrences=90,
        n_background=300,
    )
    with pytest.raises(ValueError, match="hgb_profile"):
        evaluate_occurrence_processes(
            world,
            n_splits=3,
            learner="linear",
            hgb_profile="shallow3",
        )
