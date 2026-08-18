import json
from pathlib import Path

import pytest

from sdmr.v2_4_exclusion_certificate_experiment import (
    CANDIDATE_SET_ORDER,
    DECISION_STATES,
    PRODUCTS,
    build_preoutcome_contract,
    load_exclusion_certificate_config,
)


CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "product_a_v2_4_exclusion_certificate_panels.json"
)


def test_predeclared_v2_4_config_freezes_unseen_panels_and_40_knockouts():
    payload, panels, registry = load_exclusion_certificate_config(CONFIG)
    seeds = [
        spec.seed
        for panel in panels
        for spec in (*panel.discovery, *panel.validation)
    ]

    assert tuple(payload["products"]) == PRODUCTS
    assert tuple(payload["candidate_set_order"]) == CANDIDATE_SET_ORDER
    assert tuple(payload["decision_states"]) == DECISION_STATES
    assert tuple(panel.name for panel in panels) == (
        "panel_D1",
        "panel_D2",
        "panel_D3",
    )
    assert len(seeds) == len(set(seeds)) == 18
    assert min(seeds) > 323
    assert registry["base_candidate"].nunique() == 8
    assert registry["excluded_process"].nunique() == 5
    assert len(registry) == 40
    assert not registry["excluded_predictors"].str.contains("recording_bias").any()
    assert registry["observation_predictors"].eq("recording_bias").all()


def test_preoutcome_contract_reads_no_truth_and_records_exact_denominator():
    contract, registry = build_preoutcome_contract(CONFIG)

    assert contract["scientific_promotion_run"] is False
    assert contract["scientific_promotion_allowed"] is False
    assert contract["real_empirical_data_read"] is False
    assert contract["validation_truth_read"] is False
    assert contract["old_external_sealed_outcomes_read"] is False
    assert contract["n_base_procedures"] == 8
    assert contract["n_processes"] == 5
    assert contract["n_knockout_routes"] == len(registry) == 40
    assert contract["spatial_refits_per_member"] == 5
    assert contract["calibration_source"] == "discovery_taxa_only"
    assert contract["missing_or_failed_knockout_means_required"] is False


def _mutated_config(tmp_path: Path, mutate):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_previously_opened_seed_is_rejected(tmp_path):
    path = _mutated_config(
        tmp_path,
        lambda payload: payload["panels"][0]["validation"][0].update(
            {"seed": 323}
        ),
    )
    with pytest.raises(ValueError, match="previously opened"):
        load_exclusion_certificate_config(path)


def test_process_alias_change_is_rejected_before_execution(tmp_path):
    def mutate(payload):
        payload["process_predictor_aliases"]["temp_proxy"] = "water"

    path = _mutated_config(tmp_path, mutate)
    with pytest.raises(ValueError, match="knockout registry|base procedure|process"):
        load_exclusion_certificate_config(path)


def test_validation_truth_calibration_and_width_priority_are_rejected(tmp_path):
    def mutate_truth(payload):
        payload["boundary_semantics"]["validation_truth_used_for_calibration"] = True

    with pytest.raises(ValueError, match="validation-truth calibration"):
        load_exclusion_certificate_config(_mutated_config(tmp_path, mutate_truth))

    def mutate_width(payload):
        payload["boundary_semantics"]["width_can_override_coverage"] = True

    with pytest.raises(ValueError, match="width cannot override coverage"):
        load_exclusion_certificate_config(_mutated_config(tmp_path, mutate_width))


def test_missing_knockout_can_never_be_relabelled_as_requirement(tmp_path):
    def mutate(payload):
        payload["knockout_semantics"][
            "missing_or_failed_knockout_means_required"
        ] = True

    path = _mutated_config(tmp_path, mutate)
    with pytest.raises(ValueError, match="cannot convert missing knockout"):
        load_exclusion_certificate_config(path)
