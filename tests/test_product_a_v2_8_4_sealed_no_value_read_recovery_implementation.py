import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ROOT / 'configs' / 'product_a_v2_8_4_sealed_no_value_read_recovery_implementation.json'


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_recovery_implementation_pins_the_exact_reviewed_runtime_surface():
    implementation = _load(IMPLEMENTATION)
    assert implementation['implementation_commit'] == 'd255b61e727e6a54842f07b5fa35d79a5372ca09'
    assert implementation['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    for relative, identity in implementation['implementation_identity']['files'].items():
        assert _digest(ROOT / relative) == identity['newline_canonical_sha256']

    design = implementation['recovery_design']
    assert _digest(ROOT / design['path']) == design['newline_canonical_sha256']
    assert _load(ROOT / design['path'])['contract_digest'] == design['contract_digest']
    freeze = implementation['geo_runtime_freeze']
    assert _digest(ROOT / freeze['path']) == freeze['newline_canonical_sha256']
    assert freeze['calibration_workflow_run_id'] == 33359562108
    assert freeze['calibration_artifact_id'] == 9746245575


def test_recovery_implementation_is_non_dispatchable_and_non_scientific():
    implementation = _load(IMPLEMENTATION)
    guards = implementation['implemented_guards']
    boundary = implementation['execution_boundary']

    assert all(value is True for value in guards.values())
    assert boundary['implementation_complete_for_review'] is True
    for key in (
        'recovery_authorization_exists',
        'recovery_dispatch_allowed',
        'scientific_outcome_exists',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    ):
        assert boundary[key] is False
    assert all(
        value is False for value in implementation['scientific_invariants'].values()
    )
