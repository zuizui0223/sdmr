from sdmr.factorial_process_recovery_experiment import (
    factorial_candidates,
    load_contract,
    process_set_label,
    simulate_factorial_process_niche,
)


def test_factorial_contract_and_candidate_library_are_frozen():
    contract = load_contract()
    assert contract["n_cases"] == 35
    assert len(contract["process_sets"]) == 7
    assert set(factorial_candidates()) == set(contract["candidate_library"])


def test_factorial_generator_marks_process_truth_and_varies_identity():
    sim = simulate_factorial_process_niche(
        ("temperature", "soil"),
        seed=4201,
        n_cells=400,
        n_occurrences=60,
        n_target_group=150,
        sampling_bias_strength=1.15,
    )
    env = sim.environment
    assert process_set_label(("temperature", "soil")) == "T+S"
    assert env["truth_process_temperature"].all()
    assert not env["truth_process_water"].any()
    assert env["truth_process_soil"].all()
    assert env["true_suitability"].max() <= 1.0 + 1e-12
    assert env["true_suitability"].min() >= 0.0
    assert len(sim.occurrences) == 60
    assert len(sim.target_group) == 150
