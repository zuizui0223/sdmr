from pathlib import Path

from sdmr.v2_6_contract import load_v2_6_contract
from sdmr.v2_6_refit_worker import v2_6_refit_seed
from sdmr.v2_4_refit_contract import GROUPS, FULL_FIT_CODE, SPATIAL_REFIT_CODES
from sdmr.v2_1_known_truth_gate_ablation import M_SPECS


def test_v26_freezes_six_soil_capable_taxa_per_panel_and_reserved_validation():
    contract = load_v2_6_contract(
        Path("configs/product_a_v2_6_calibration_redundancy.json")
    )
    assert contract.support_audit.minimum_support_per_key == 2
    assert len(contract.support_audit.required_validation_keys) == 9
    assert len(contract.panels) == 3
    assert all(len(panel.calibration) == 9 for panel in contract.panels)
    assert all(
        sum(spec.family == "omitted_driver" for spec in panel.calibration) == 6
        for panel in contract.panels
    )
    assert {
        spec.seed for panel in contract.panels for spec in panel.calibration
    } == set(range(446, 473))
    assert {
        spec.seed for panel in contract.panels for spec in panel.validation
    } == {501, 502, 503, 511, 512, 513, 521, 522, 523}


def test_v26_partition_seeds_are_unique_across_calibration_and_validation_roles():
    seeds = set()
    for panel in ("panel_D1", "panel_D2", "panel_D3"):
        for role, n_taxa in (("calibration", 9), ("validation", 3)):
            for taxon_index in range(n_taxa):
                for group in GROUPS:
                    for candidate_index in range(40):
                        for m_index in range(len(M_SPECS)):
                            for fit_code in (*SPATIAL_REFIT_CODES, FULL_FIT_CODE):
                                value = v2_6_refit_seed(
                                    panel=panel,
                                    role=role,
                                    taxon_index=taxon_index,
                                    group=group,
                                    candidate_index=candidate_index,
                                    m_index=m_index,
                                    fit_code=fit_code,
                                )
                                assert value not in seeds
                                seeds.add(value)
