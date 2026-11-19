import pytest

from sdmr.structural_known_truth_v1 import (
    WORLDS, generate_forest_world, score_forest_world
)
from sdmr.structural_process_benchmarks_v1 import (
    COMPARATORS, aggregate_comparators, comparator_candidate,
    synthetic_truth_positive
)


@pytest.fixture(scope="module")
def scored():
    return [
        score_forest_world(generate_forest_world(world, seed))
        for seed in (1201, 1202, 1203) for world in WORLDS
    ]


def test_comparators_are_complete_and_truth_is_separate_from_fit():
    assert len(COMPARATORS) == 4
    assert sum(synthetic_truth_positive(w) for w in WORLDS) == 3
    with pytest.raises(ValueError, match="unregistered"):
        synthetic_truth_positive("imaginary")


def test_shared_carriers_recover_when_individual_drop_misses(scored):
    shared = next(s for s in scored if s.world == "shared_carrier")
    assert not comparator_candidate(shared, "spatial_single_predictor")
    assert not comparator_candidate(shared, "space_and_time_single_predictor")
    assert comparator_candidate(shared, "all_carriers_without_observation_audit")
    assert comparator_candidate(shared, "all_carriers_with_observation_audit")


def test_selection_requires_source_audit_and_cannot_be_rescued_by_p(scored):
    selection = next(s for s in scored if s.world == "observation_selection")
    assert selection.observation_selection_known is False
    assert not comparator_candidate(selection, "all_carriers_with_observation_audit")


def test_naive_spatial_can_promote_a_noncausal_proxy(scored):
    s = next(s for s in scored if s.world == "spatial_only")
    assert not synthetic_truth_positive(s.world)
    assert comparator_candidate(s, "spatial_single_predictor")
    assert not comparator_candidate(s, "all_carriers_with_observation_audit")


def test_conditional_comparator_denominator_not_independent_organism_replicates(scored):
    summaries = aggregate_comparators(scored)
    assert len(summaries) == 4
    assert {s.comparator for s in summaries} == set(COMPARATORS)
    assert all(s.n_cases == 24 for s in summaries)
    assert all(s.true_positive_targets == 9 for s in summaries)
    assert all(s.null_targets == 15 for s in summaries)
    guarded = summaries[-1]
    assert guarded.true_positive_calls == 9
    assert guarded.false_positive_calls == 0
    assert summaries[0].false_positive_calls > 0


def test_unknown_and_duplicate_world_seed_refused(scored):
    with pytest.raises(ValueError, match="unknown"):
        comparator_candidate(scored[0], "secret_winner")
    with pytest.raises(ValueError, match="duplicate"):
        aggregate_comparators(scored + [scored[0]])
