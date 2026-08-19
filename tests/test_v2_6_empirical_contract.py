from pathlib import Path

from sdmr.v2_6_empirical_contract import load_v2_6_empirical_contract

CONFIG = Path("configs/product_a_v2_6_empirical_confirmation_contract.json")


def test_v26_empirical_contract_is_source_only_and_sealed_before_m():
    c = load_v2_6_empirical_contract(CONFIG)
    assert c["known_truth_source"]["decision"] == "v2_6_supported"
    assert c["source_evidence_reuse_only"] is True
    assert c["old_real_model_outputs_reused"] is False
    assert c["old_real_background_outputs_reused"] is False
    assert c["old_real_sealed_outcomes_read"] is False
    assert c["information_barrier"]["outer_sealed_before_M"] is True
    assert c["information_barrier"]["sealed_occurrences_used_for_selection"] is False
    assert c["information_barrier"]["sealed_occurrences_used_for_M"] is False


def test_v26_empirical_design_denominator_is_frozen():
    c = load_v2_6_empirical_contract(CONFIG)
    assert c["fixed_design"]["split_seeds"] == [2026081901, 2026081902, 2026081903]
    assert c["fixed_design"]["sealed_fractions"] == [0.20, 0.30]
    assert c["fixed_design"]["M_km"] == [150, 300, 500]
    assert c["fixed_design"]["n_confirmation_parts"] == 6
    assert c["fixed_design"]["require_all_12_taxa"] is True
