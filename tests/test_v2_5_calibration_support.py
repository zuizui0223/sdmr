import json
from pathlib import Path

import pytest

from sdmr.v2_5_calibration_support import (
    audit_calibration_support,
    require_calibration_support,
    response_processes_for_family,
)


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
    path = Path("configs/product_a_v2_5_calibration_support.json")
    config = json.loads(path.read_text())

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
