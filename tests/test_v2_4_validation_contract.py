import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_4_validation_contract import (
    CALIBRATION_ARTIFACT_DIGEST,
    CALIBRATION_ARTIFACT_ID,
    CALIBRATION_HEAD_SHA,
    CALIBRATION_RUN_ID,
    DECISION_STATES,
    PANELS,
    PRODUCTS,
    VALIDATION_SPECS,
    exclusion_certificate_decision,
    load_validation_contract,
)


CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "product_a_v2_4_validation_contract.json"
)


def _summary(**overrides):
    rows = []
    for panel in PANELS:
        row = {
            "panel": panel,
            "n_validation_taxa": 3,
            "n_complete_process_certificates": 3,
            "n_complete_boundary_certificates": 3,
            "total_false_required_processes": 0,
            "minimum_possible_process_recall": 1.0,
            "complete_adequate_boundary_coverage": 0.50,
            "v2_4_calibrated_boundary_coverage": 0.60,
        }
        row.update(overrides)
        rows.append(row)
    return pd.DataFrame(rows)


def test_validation_contract_freezes_sources_taxa_products_and_order():
    payload = load_validation_contract(CONFIG)

    assert payload["source_discovery_calibration"]["run_id"] == CALIBRATION_RUN_ID
    assert payload["source_discovery_calibration"]["head_sha"] == CALIBRATION_HEAD_SHA
    assert payload["source_discovery_calibration"]["artifact_id"] == CALIBRATION_ARTIFACT_ID
    assert payload["source_discovery_calibration"]["artifact_digest"] == CALIBRATION_ARTIFACT_DIGEST
    assert tuple(payload["products"]) == PRODUCTS
    assert tuple(payload["decision_states"]) == DECISION_STATES
    observed = {
        panel: tuple(
            (row["family"], row["seed"])
            for row in payload["panels"][panel]["validation"]
        )
        for panel in PANELS
    }
    assert observed == VALIDATION_SPECS
    assert payload["validation_truth_read_before_all_fits_and_certificates_frozen"] is False
    assert payload["process_certificate"]["missing_or_failed_transfer_means_required"] is False
    assert payload["boundary_certificate"]["validation_truth_used_for_calibration"] is False


def _mutate(tmp_path: Path, mutate):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_validation_contract_rejects_source_seed_and_truth_mutations(tmp_path):
    with pytest.raises(ValueError, match="calibration source changed"):
        load_validation_contract(
            _mutate(
                tmp_path,
                lambda payload: payload["source_discovery_calibration"].update(
                    {"artifact_id": "other"}
                ),
            )
        )

    with pytest.raises(ValueError, match="validation taxa changed"):
        load_validation_contract(
            _mutate(
                tmp_path,
                lambda payload: payload["panels"]["panel_D1"]["validation"][0].update(
                    {"seed": 323}
                ),
            )
        )

    with pytest.raises(ValueError, match="validation truth cannot calibrate"):
        load_validation_contract(
            _mutate(
                tmp_path,
                lambda payload: payload["boundary_certificate"].update(
                    {"validation_truth_used_for_calibration": True}
                ),
            )
        )

    with pytest.raises(ValueError, match="missing validation transfer"):
        load_validation_contract(
            _mutate(
                tmp_path,
                lambda payload: payload["process_certificate"].update(
                    {"missing_or_failed_transfer_means_required": True}
                ),
            )
        )


def test_validation_decision_supported_and_partial_states():
    supported = exclusion_certificate_decision(_summary()).iloc[0]
    assert supported["decision"] == "exclusion_certificate_supported"
    assert bool(supported["process_support"])
    assert bool(supported["boundary_support"])
    assert not bool(supported["scientific_promotion_allowed"])

    process_only = exclusion_certificate_decision(
        _summary(v2_4_calibrated_boundary_coverage=0.40)
    ).iloc[0]
    assert process_only["decision"] == "exclusion_certificate_process_only"

    boundary_only = exclusion_certificate_decision(
        _summary(minimum_possible_process_recall=0.80)
    ).iloc[0]
    assert boundary_only["decision"] == "exclusion_certificate_boundary_only"

    unsupported = exclusion_certificate_decision(
        _summary(
            minimum_possible_process_recall=0.80,
            v2_4_calibrated_boundary_coverage=0.40,
        )
    ).iloc[0]
    assert unsupported["decision"] == "exclusion_certificate_not_supported"


def test_validation_decision_unavailable_on_missing_or_incomplete_panel():
    missing = exclusion_certificate_decision(
        _summary().loc[lambda frame: ~frame["panel"].eq("panel_D3")]
    ).iloc[0]
    assert missing["decision"] == "exclusion_certificate_unavailable"

    incomplete = exclusion_certificate_decision(
        _summary(n_complete_boundary_certificates=2)
    ).iloc[0]
    assert incomplete["decision"] == "exclusion_certificate_unavailable"
