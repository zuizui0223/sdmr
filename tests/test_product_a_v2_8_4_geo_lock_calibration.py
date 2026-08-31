import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'configs' / 'product_a_v2_8_4_geo_lock_calibration_contract.json'
WORKFLOW = ROOT / '.github' / 'workflows' / 'product-a-v2-8-4-geo-lock-calibration.yml'


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_geo_calibration_is_exactly_the_recovery_designs_truth_blind_next_gate():
    contract = _load(CONTRACT)
    predecessor = contract['predecessor_recovery_design']
    design = _load(ROOT / predecessor['path'])

    assert predecessor['main_merge_commit'] == '2591e9bf9871ba31e1dbad6c7c9369a31c133558'
    assert _digest(ROOT / predecessor['path']) == predecessor['newline_canonical_sha256']
    assert predecessor['contract_digest'] == design['contract_digest']
    assert design['allowed_recovery_change']['geo_lock_calibration_must_be_truth_blind'] is True
    assert design['allowed_recovery_change']['geo_lock_calibration_may_not_access_scientific_source_or_receipts'] is True
    assert design['allowed_recovery_change']['add_hash_locked_geo_extension_only'] is True
    assert design['allowed_recovery_change']['geo_extension_must_retain_core_versions'] is True
    assert design['allowed_recovery_change']['current_recovery_must_be_exactly_third_total_workflow_dispatch'] is True
    assert design['allowed_recovery_change']['fourth_workflow_dispatch_forbidden'] is True


def test_geo_lock_retains_every_frozen_core_pin_and_adds_only_rasterio_directly():
    contract = _load(CONTRACT)
    environment = contract['environment']
    core_input = ROOT / environment['scientific_requirements_input']['path']
    core_lock = ROOT / environment['scientific_requirements_lock']['path']
    geo_input = ROOT / environment['geo_requirements_input']['path']
    geo_lock = ROOT / environment['geo_requirements_lock']['path']

    assert _digest(core_input) == environment['scientific_requirements_input']['newline_canonical_sha256']
    assert _digest(core_lock) == environment['scientific_requirements_lock']['newline_canonical_sha256']
    assert _digest(geo_input) == environment['geo_requirements_input']['newline_canonical_sha256']
    assert _digest(geo_lock) == environment['geo_requirements_lock']['newline_canonical_sha256']
    assert geo_input.read_text(encoding='utf-8').splitlines() == [
        '-r product_a_v2_8_4_scientific_requirements.in',
        'rasterio==1.5.1',
    ]

    lock_text = geo_lock.read_text(encoding='utf-8')
    assert '--python-version 3.12' in lock_text
    assert '--hash=sha256:' in lock_text
    for name, version in environment['retained_core_versions'].items():
        assert f'{name}=={version}' in lock_text
    assert environment['added_geo_versions'] == {'rasterio': '1.5.1'}
    assert 'rasterio==1.5.1' in lock_text


def test_calibration_workflow_cannot_access_science_or_open_a_raster():
    contract = _load(CONTRACT)
    scope = contract['calibration_scope']
    workflow = WORKFLOW.read_text(encoding='utf-8')

    assert scope['truth_blind'] is True
    assert scope['package_metadata_and_wheels_only'] is True
    for key in (
        'scientific_source_access_allowed',
        'presealed_receipt_access_allowed',
        'github_artifact_access_allowed',
        'raster_dataset_open_allowed',
        'environmental_value_extraction_allowed',
        'sealed_read_entry_allowed',
        'scientific_outcome_read_allowed',
        'scientific_telemetry_allowed',
    ):
        assert scope[key] is False

    assert 'workflow_dispatch:' not in workflow
    assert 'actions/download-artifact@' not in workflow
    assert 'rasterio.open' not in workflow
    assert 'extract_raster_values' not in workflow
    assert 'product-a-v2-8-4-sealed-state-' not in workflow
    assert 'product-a-v2-8-4-presealed-receipt-' not in workflow
    assert "python-version: '3.12.11'" in workflow
    assert 'python -m pip install --disable-pip-version-check --require-hashes -r "$GEO_LOCK"' in workflow
    assert 'import rasterio' in workflow
    assert 'raster_dataset_opened' in workflow
    assert 'environmental_values_read' in workflow
    assert 'sealed_read_entered' in workflow


def test_calibration_cannot_authorize_recovery_or_product_b():
    contract = _load(CONTRACT)
    boundary = contract['execution_boundary']
    invariants = contract['scientific_invariants']

    assert boundary['geo_lock_calibration_authorized'] is True
    for key in (
        'sealed_recovery_implementation_authorized',
        'sealed_recovery_dispatch_authorized',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    ):
        assert boundary[key] is False
    for key, value in invariants.items():
        if key != 'product_b_unblocked':
            assert value is False
    assert invariants['product_b_unblocked'] is False
