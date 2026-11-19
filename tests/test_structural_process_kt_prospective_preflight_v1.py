"""Response-blind tests. NEVER generate/score prospective seeds here."""
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
import json

import pytest

# experiments/ is a deliberately non-package execution directory. Import the
# single script by file identity so Python 3.10–3.13 test collection is stable.
_SCRIPT = Path(__file__).resolve().parents[1] / "experiments" / "structural_known_truth_prospective_v1.py"
_SPEC = spec_from_file_location("structural_kt_preflight_script", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
SCHEMA = _MODULE.SCHEMA
EXPECTED_SEEDS = _MODULE.EXPECTED_SEEDS
verify_design = _MODULE.verify_design
verify_one_shot_source = _MODULE.verify_one_shot_source


CONTRACT = Path("configs/structural_process_kt_prospective_v1.json")


def test_unused_seed_contract_is_exact_and_not_executed():
    data = json.loads(CONTRACT.read_text())
    verify_design(data)
    assert data["schema"] == SCHEMA
    assert tuple(data["seeds"]) == EXPECTED_SEEDS
    assert data["n_cases"] == 80
    assert data["evidence_class"] == "synthetic_prospective_only"


@pytest.mark.parametrize("key,value", [
    ("seeds", [1201, 1202, 1203]),
    ("n_regions", 4),
    ("n_cases", 79),
    ("positive_worlds", ["shared_carrier"]),
    ("status", "completed"),
    ("primary_comparator", "spatial_single_predictor"),
])
def test_prospective_design_drift_is_rejected_without_opening_seed(key, value):
    d = json.loads(CONTRACT.read_text())
    d[key] = value
    with pytest.raises(ValueError, match="frozen prospective design mismatch"):
        verify_design(d)


def test_posthoc_promotion_threshold_edit_refused():
    d = json.loads(CONTRACT.read_text())
    d["gate"]["false_positive_max"] = 15
    with pytest.raises(ValueError, match="thresholds"):
        verify_design(d)


def test_required_observation_and_temporal_boundaries_frozen():
    d = json.loads(CONTRACT.read_text())
    d["methods"]["observation_flag"] = "estimated by the fitted outcome"
    with pytest.raises(ValueError, match="observation evidence"):
        verify_design(d)
    d = json.loads(CONTRACT.read_text())
    d["methods"]["time_axis"] = "prior to future proven"
    with pytest.raises(ValueError, match="temporal estimand"):
        verify_design(d)


def test_source_barrier_refuses_unfrozen_execution_before_git_or_rng_access():
    with pytest.raises(ValueError, match="prior full-source freeze"):
        verify_one_shot_source(
            {"status": "not_frozen"},
            "invalid lock",
            CONTRACT,
        )


def test_unopened_prospective_result_does_not_exist_on_design_line():
    assert not Path("results/structural_known_truth_prospective_v1_result.json").exists()
    # Activation may legitimately exist later; response data remain outside the branch.
