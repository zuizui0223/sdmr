import pandas as pd

from sdmr.known_truth_scenarios import simulate_known_truth_plant_niche
from sdmr.sealed_answer_separator_v25_development import (
    load_contract,
    unused_separator_background,
)


def _coords(frame):
    return set(zip(frame.longitude.round(12), frame.latitude.round(12), strict=True))


def test_contract_freezes_consumed_denominator_and_separator_safety():
    cfg = load_contract()
    assert cfg["consumed_seed_denominator"] == list(range(17001, 17011))
    assert len(cfg["families"]) == 6
    assert cfg["process_universe"] == ["temperature", "water", "seasonality", "noise"]
    sep = cfg["separator"]
    assert sep["density_noninferiority_margin_nats"] == 0.01
    assert sep["sem_multiplier"] == 1.0
    assert sep["minimum_complete_sealed_occurrences"] == 10
    assert sep["minimum_distinct_sealed_spatial_blocks"] == 2
    assert len(sep["required_model_specs"]) == 6
    screen = cfg["development_advancement_screen"]
    assert screen["n_removed_true_members_max"] == 0
    assert screen["n_removed_false_members_min"] == 1
    gov = cfg["governance"]
    assert gov["fresh_validation_authorized"] is False
    assert gov["fresh_seed_allocation_authorized"] is False
    assert gov["truth_may_be_opened_only_after_truth_blind_refinement_is_written"] is True


def test_unused_separator_background_is_row_disjoint_and_deterministic():
    cfg = load_contract()
    sim_cfg = cfg["simulation"]
    sim = simulate_known_truth_plant_niche(
        "gaussian",
        seed=17001,
        n_cells=sim_cfg["n_cells"],
        n_occurrences=sim_cfg["n_occurrences"],
        n_target_group=sim_cfg["n_target_group"],
    )
    a = unused_separator_background(
        sim,
        n_rows=sim_cfg["separator_background_rows"],
        random_state=sim_cfg["separator_background_seed_offset"] + 17001,
    )
    b = unused_separator_background(
        sim,
        n_rows=sim_cfg["separator_background_rows"],
        random_state=sim_cfg["separator_background_seed_offset"] + 17001,
    )
    assert len(a) == 1500
    pd.testing.assert_frame_equal(a, b)
    assert not (_coords(a) & _coords(sim.occurrences))
    assert not (_coords(a) & _coords(sim.target_group))
    for hidden in ("true_suitability", "sampling_effort", "focal_recording_multiplier", "scenario"):
        assert hidden not in a.columns
