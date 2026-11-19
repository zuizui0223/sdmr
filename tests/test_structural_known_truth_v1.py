"""Development checks for eight synthetic SDMR × Structural forest worlds.

World-specific numerical thresholds are diagnostic sentinels on burned
development seeds, not prospective success/promotion criteria.
"""
import numpy as np
import pytest

from sdmr.structural_known_truth_v1 import (
    WORLDS, generate_forest_world, score_forest_world
)


@pytest.fixture(scope="module")
def results():
    return {w: score_forest_world(generate_forest_world(w, 1201)) for w in WORLDS}


def test_all_eight_named_worlds_and_fixed_seed_repeatability():
    assert len(WORLDS) == 8 and len(set(WORLDS)) == 8
    a = generate_forest_world("direct_structure", 1201)
    b = generate_forest_world("direct_structure", 1201)
    assert np.array_equal(a.b0, b.b0)
    assert np.array_equal(a.tree1, b.tree1)
    assert a.site_id.size == 8 * 64
    assert np.unique(a.region).size == 8
    assert score_forest_world(a) == score_forest_world(b)


def test_true_structural_world_has_within_change_information(results):
    r = results["direct_structure"]
    assert r.spatial_gain > 0.05
    assert r.temporal_gain > 0.05
    assert r.temporal_p <= 0.05
    assert r.within_effect == 0.8
    assert r.inference_ceiling == "development_known_truth_only"


def test_known_measured_site_quality_does_not_create_structural_gain(results):
    r = results["measured_site_proxy"]
    assert abs(r.temporal_gain) < 0.1
    assert abs(r.spatial_gain) < 0.10
    assert r.within_effect == 0.0


def test_shared_carrier_single_variable_drop_misses_process_information(results):
    r = results["shared_carrier"]
    assert abs(r.spatial_gain) < 0.02  # B was already available as Z
    assert r.closure_gain > 0.05     # remove BOTH B and Z
    assert abs(r.temporal_gain) < 0.02  # individual B is redundant with temporal Z
    assert r.temporal_closure_gain > 0.05  # whole temporal carrier set is not
    assert r.declared_carriers == ("b", "z")
    assert r.within_effect == 0.8


def test_spatial_gain_does_not_imply_temporal_effect(results):
    r = results["spatial_only"]
    assert r.spatial_gain > 0.02
    assert abs(r.temporal_gain) < 0.10
    assert r.within_effect == 0.0


def test_temporal_transfer_world_recovers_change_signal(results):
    r = results["temporal_transfer"]
    assert r.temporal_gain > 0.05
    assert r.temporal_p <= 0.05


def test_operator_mismatch_is_not_a_replication_of_growth(results):
    r = results["operator_mismatch"]
    assert r.beetle_gain > 0.05
    assert abs(r.temporal_gain) < 0.10
    assert r.within_effect == 0.0


def test_selection_bias_is_flagged_not_claimed_causal(results):
    r = results["observation_selection"]
    assert 0 < r.n_sites_observed < r.n_sites_source
    assert r.n_regions == 8
    assert r.observation_selection_known is False
    assert r.within_effect == 0.0


def test_unmeasured_driver_full_system_not_rescued_by_variable_hope(results):
    r = results["omitted_driver"]
    assert r.full_vs_null_gain < 0.1
    assert r.within_effect == 0.0


def test_impossible_world_and_sample_denominator_refusal():
    with pytest.raises(ValueError, match="unknown"):
        generate_forest_world("magic_forest", 1201)
    with pytest.raises(ValueError, match="insufficient"):
        generate_forest_world("direct_structure", 1201, n_regions=2)


def test_independent_development_seeds_keep_truth_and_status():
    for seed in (1202, 1203):
        for world in WORLDS:
            r = score_forest_world(generate_forest_world(world, seed))
            assert r.n_regions == 8
            assert r.n_sites_observed >= 8 * 8
            assert r.inference_ceiling == "development_known_truth_only"
