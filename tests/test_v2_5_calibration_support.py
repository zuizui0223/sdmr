import copy
import json
from pathlib import Path

import pytest

from sdmr.v2_5_calibration_support import (
    audit_calibration_support,
    require_calibration_support,
    response_processes_for_family,
)
from sdmr.v2_5_contract import load_v2_5_contract


CONFIG_PATH = Path("configs/product_a_v2_5_calibration_support.json")


def test_omitted_driver_requires_soil_response_axis():
    assert response_processes_for_family("omitted_driver") == (
        "temperature",
        "water",
        "soil",
    )
    assert response_processes_for_family("gaussian") == ("temperature", "water")
    with pytest.raises(ValueError, match="unknown known-truth family"):
        response_processes_for_family("omited_driver")


def test_v24_discovery_family_pattern_fails_before_validation_opening():
    calibration = [
        {"family": "gaussian", "seed": 371},
        {"family": "asymmetric", "seed": 381},
        {"family": "interaction", "seed": 391},
    ]
    validation = [
        {"family": "soft_threshold", "seed": 401},
        {"family": "omitted_driver", "seed": 411},
        {"family": "observation_confounded", "seed": 421},
    ]

    audit = audit_calibration_support(
        calibration=calibration,
        validation=validation,
        minimum_support_per_key=1,
    )

    assert not audit.complete
    assert set(audit.missing_keys) == {
        ("soil", "optimum"),
        ("soil", "lower_limit"),
        ("soil", "upper_limit"),
    }


def test_v25_config_covers_every_validation_response_key_twice():
    config = json.loads(CONFIG_PATH.read_text())

    audit = require_calibration_support(config)
    support = {(p, q): n for p, q, n in audit.support_counts}

    assert audit.complete
    assert len(audit.required_validation_keys) == 9
    assert set(audit.required_validation_keys) == {
        (predictor, quantity)
        for predictor in ("temperature", "water", "soil")
        for quantity in ("optimum", "lower_limit", "upper_limit")
    }
    assert min(support.values()) >= 2
    assert support[("soil", "optimum")] == 2
    assert support[("soil", "lower_limit")] == 2
    assert support[("soil", "upper_limit")] == 2


def test_panel_failure_is_fail_closed_and_names_missing_key():
    config = {
        "calibration_support": {
            "quantities": ["optimum", "lower_limit", "upper_limit"],
            "minimum_calibration_taxa_per_key": 2,
        },
        "panels": [
            {
                "name": "D_bad",
                "calibration": [{"family": "omitted_driver", "seed": 1}],
                "validation": [{"family": "omitted_driver", "seed": 2}],
            }
        ],
    }

    with pytest.raises(ValueError, match="D_bad") as exc:
        require_calibration_support(config)
    assert "soil/optimum" in str(exc.value)


def test_v25_contract_freezes_disjoint_unopened_seed_roles():
    contract = load_v2_5_contract(CONFIG_PATH)
    calibration = {spec.seed for panel in contract.panels for spec in panel.calibration}
    validation = {spec.seed for panel in contract.panels for spec in panel.validation}

    assert contract.support_audit.complete
    assert len(contract.panels) == 3
    assert len(calibration) == 15
    assert len(validation) == 9
    assert calibration.isdisjoint(validation)
    assert min(calibration) > 423
    assert min(validation) > 423
    assert len(contract.sha256) == 64


def test_v25_contract_rejects_opened_or_overlapping_validation_seed(tmp_path):
    payload = json.loads(CONFIG_PATH.read_text())
    bad = copy.deepcopy(payload)
    bad["panels"][0]["validation"][0]["seed"] = 401
    path = tmp_path / "opened.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="reuses previously opened"):
        load_v2_5_contract(path)

    bad = copy.deepcopy(payload)
    bad["panels"][0]["validation"][0]["seed"] = bad["panels"][0]["calibration"][0]["seed"]
    path = tmp_path / "overlap.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="must be disjoint"):
        load_v2_5_contract(path)
