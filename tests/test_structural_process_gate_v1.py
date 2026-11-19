from dataclasses import replace

import pytest

from sdmr.structural_known_truth_v1 import (
    WORLDS, generate_forest_world, score_forest_world
)
from sdmr.structural_process_gate_v1 import (
    StructureProcessGate, assess_forest_development, observation_audit_ablation
)


@pytest.fixture(scope="module")
def pilot():
    return {
        world: score_forest_world(generate_forest_world(world, 1201))
        for world in WORLDS
    }


def test_true_represented_structure_can_retain_carrier_and_temporal_information(pilot):
    for world in ("direct_structure", "shared_carrier", "temporal_transfer"):
        result = assess_forest_development(pilot[world])
        assert result.state == "contributory_information_candidate"
        assert result.causal_process_identified is False
        assert result.empirical_promotion_authorized is False
        assert result.evidence_class == "synthetic_development"


def test_site_proxy_is_not_a_causal_structural_result(pilot):
    result = assess_forest_development(pilot["measured_site_proxy"])
    assert result.state == "unresolved"
    assert result.reason == "complete_carrier_knockout_not_informative"


def test_large_spatial_gain_does_not_rescue_missing_temporal_information(pilot):
    result = assess_forest_development(pilot["spatial_only"])
    assert pilot["spatial_only"].spatial_gain > 0.1
    assert result.state == "unresolved"
    assert result.reason == "within_site_change_information_not_supported"


def test_observation_selection_is_unresolved_even_if_both_gains_positive(pilot):
    r = pilot["observation_selection"]
    assert r.spatial_gain > 0
    assert r.temporal_gain > 0
    result = assess_forest_development(r)
    assert result.state == "unresolved"
    assert result.reason == "observation_or_survivor_selection_unverified"


def test_operator_mismatch_cannot_rescue_tree_process(pilot):
    r = pilot["operator_mismatch"]
    assert r.beetle_gain > 1.0
    assert assess_forest_development(r).state == "unresolved"


def test_missing_driver_means_adequacy_failure_not_no_effect(pilot):
    result = assess_forest_development(pilot["omitted_driver"])
    assert result.state == "unavailable"
    assert result.reason == "declared_full_system_not_demonstrably_informative"


def test_fewer_regions_are_unavailable_even_when_gain_large(pilot):
    r = replace(pilot["direct_structure"], n_regions=2)
    result = assess_forest_development(r)
    assert result.state == "unavailable"
    assert result.reason == "independent_block_support"


def test_unsafe_audit_override_is_not_silent(pilot):
    score = replace(pilot["observation_selection"],
                    spatial_gain=0.12, closure_gain=0.12,
                    temporal_gain=0.12, temporal_p=0.01,
                    temporal_closure_gain=0.12, temporal_closure_p=0.01,
                    full_vs_null_gain=0.13)
    guarded, unsafe = observation_audit_ablation(score)
    assert guarded.state == "unresolved"
    assert unsafe.state == "contributory_information_candidate"
    assert unsafe.empirical_promotion_authorized is False


def test_invalid_margins_and_world_class_rejected(pilot):
    with pytest.raises(ValueError, match="positive"):
        StructureProcessGate(temporal_margin=0)
    with pytest.raises(ValueError, match="field/empirical"):
        assess_forest_development(
            replace(pilot["direct_structure"], inference_ceiling="empirical")
        )


def test_development_denominators_are_retained_across_three_burned_seeds():
    counts = {"contributory_information_candidate": 0, "unresolved": 0,
              "unavailable": 0}
    for seed in (1201, 1202, 1203):
        for world in WORLDS:
            r = assess_forest_development(
                score_forest_world(generate_forest_world(world, seed))
            )
            assert not r.causal_process_identified
            assert not r.empirical_promotion_authorized
            counts[r.state] += 1
    assert sum(counts.values()) == 24
    assert counts["unresolved"] >= 1
    assert counts["unavailable"] >= 1
