import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / 'configs' / 'product_a_v2_8_4_geo_runtime_freeze.json'


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_successful_truth_blind_geo_receipt_is_immutable_and_self_consistent():
    freeze = _load(FREEZE)
    evidence = freeze['calibration_evidence']
    receipt = dict(evidence['receipt'])
    embedded = receipt.pop('receipt_digest')
    canonical = json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()

    assert evidence['workflow_run_id'] == receipt['github_run_id'] == 33359343821
    assert evidence['workflow_run_attempt'] == receipt['github_run_attempt'] == 1
    assert evidence['head_sha'] == receipt['github_sha'] == 'a66b87eff2106dc6ac431b596b23e7b6e680748f'
    assert evidence['workflow_run_conclusion'] == 'success'
    assert evidence['artifact_id'] == 9746173100
    assert evidence['artifact_digest'] == 'sha256:11333eeaf228b595d14cabd8e921234f11abafd801a4c3ec010ab647086241fe'
    assert hashlib.sha256(canonical).hexdigest() == embedded
    assert receipt['status'] == 'geo_lock_import_calibration_complete'
    assert receipt['rasterio_imported'] is True


def test_frozen_geo_runtime_files_and_versions_match_the_calibrated_identity():
    freeze = _load(FREEZE)
    identity = freeze['frozen_runtime_identity']
    receipt = freeze['calibration_evidence']['receipt']

    for key in ('calibration_workflow', 'calibration_contract', 'geo_requirements_input', 'geo_requirements_lock'):
        pin = identity[key]
        assert _digest(ROOT / pin['path']) == pin['newline_canonical_sha256']
    assert identity['runner'] == 'ubuntu-24.04'
    assert identity['python_patch'] == receipt['python_version'] == '3.12.11'
    assert identity['package_versions'] == receipt['package_versions']
    assert identity['package_versions']['rasterio'] == '1.5.1'


def test_geo_freeze_contains_no_scientific_observation_or_execution_authority():
    freeze = _load(FREEZE)
    receipt = freeze['calibration_evidence']['receipt']
    boundary = freeze['execution_boundary']

    for key in (
        'scientific_source_accessed',
        'presealed_receipts_accessed',
        'github_artifacts_accessed',
        'raster_dataset_opened',
        'environmental_values_read',
        'sealed_read_entered',
        'scientific_outcome_read',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    ):
        assert receipt[key] is False
    assert boundary['geo_runtime_freeze_complete'] is True
    for key in (
        'sealed_recovery_implementation_reviewed',
        'sealed_recovery_dispatch_authorized',
        'scientific_outcome_exists',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    ):
        assert boundary[key] is False
