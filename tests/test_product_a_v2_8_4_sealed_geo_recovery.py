import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

import sdmr.v2_8_4_geo_runtime as geo_runtime
from sdmr.v2_8_4_geo_runtime import (
    GEO_RECEIPT_PURPOSE,
    validate_geo_environment_receipt,
    write_geo_environment_receipt,
)
from sdmr.v2_8_4_sealed_authorization import (
    NO_VALUE_READ_RECOVERY_AUTHORIZED_REF,
    _verify_operational_attempt,
)


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'configs' / 'product_a_v2_8_4_sealed_post_entry_no_value_read_recovery_design.json'
GEO_FREEZE = ROOT / 'configs' / 'product_a_v2_8_4_geo_runtime_freeze.json'
WORKFLOW = ROOT / '.github' / 'workflows' / 'product-a-v2-8-4-sealed-reusable.yml'
RUNTIME = ROOT / 'src' / 'sdmr' / 'v2_8_4_sealed_runtime.py'


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def _example_geo_receipt() -> dict:
    freeze = _load(GEO_FREEZE)
    receipt = {
        'purpose': GEO_RECEIPT_PURPOSE,
        'python_version': freeze['frozen_runtime_identity']['python_patch'],
        'runner_os': 'Linux',
        'package_versions': freeze['frozen_runtime_identity']['package_versions'],
        'geo_requirements_lock_sha256': freeze['frozen_runtime_identity']['geo_requirements_lock']['newline_canonical_sha256'],
        'rasterio_imported': True,
        'scientific_source_accessed': False,
        'presealed_receipts_accessed': False,
        'github_input_artifacts_accessed': False,
        'raster_dataset_opened': False,
        'environmental_values_read': False,
        'sealed_read_entered': False,
        'scientific_outcome_read': False,
        'scientific_promotion_allowed': False,
        'product_b_unblocked': False,
    }
    receipt['receipt_digest'] = hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def test_geo_runtime_receipt_validation_is_exact_and_fail_closed():
    freeze = _load(GEO_FREEZE)
    receipt = _example_geo_receipt()
    assert validate_geo_environment_receipt(receipt, freeze=freeze) == receipt

    for key, bad_value in (
        ('rasterio_imported', False),
        ('raster_dataset_opened', True),
        ('environmental_values_read', True),
        ('sealed_read_entered', True),
        ('scientific_promotion_allowed', True),
        ('product_b_unblocked', True),
    ):
        changed = dict(receipt)
        changed[key] = bad_value
        changed.pop('receipt_digest')
        changed['receipt_digest'] = hashlib.sha256(_canonical(changed)).hexdigest()
        with pytest.raises(ValueError):
            validate_geo_environment_receipt(changed, freeze=freeze)


def test_geo_runtime_import_receipt_matches_freeze_without_opening_raster(
    tmp_path, monkeypatch
):
    freeze = _load(GEO_FREEZE)
    expected = freeze['frozen_runtime_identity']['package_versions']
    monkeypatch.setattr(
        geo_runtime.importlib.metadata, 'version', lambda name: expected[name]
    )
    monkeypatch.setattr(
        geo_runtime.platform, 'python_version',
        lambda: freeze['frozen_runtime_identity']['python_patch'],
    )
    monkeypatch.setenv('RUNNER_OS', 'Linux')
    monkeypatch.setitem(
        sys.modules, 'rasterio', types.SimpleNamespace(__version__='1.5.1')
    )
    receipt = write_geo_environment_receipt(
        freeze_path=GEO_FREEZE, output_path=tmp_path / 'receipt.json'
    )
    assert receipt['rasterio_imported'] is True
    assert receipt['raster_dataset_opened'] is False
    assert receipt['environmental_values_read'] is False


def test_sealed_part_import_gate_precedes_every_input_download_and_sealed_entry():
    workflow = WORKFLOW.read_text(encoding='utf-8')
    install = workflow.index('Install exact scientific core plus frozen geo extension')
    gate = workflow.index(
        'Verify exact geo runtime without opening a raster before any input artifact download'
    )
    first_download = workflow.index(
        'name: product-a-v2-8-4-sealed-preflight', install
    )
    source_download = workflow.index(
        'name: v283-fresh-part-${{ matrix.seed }}', install
    )
    sealed_entry = workflow.index('Enter the one-shot sealed read and finalize this part')

    assert install < gate < first_download < source_download < sealed_entry
    assert workflow.count(
        '-r configs/product_a_v2_8_4_geo_requirements.lock'
    ) == 1
    assert '--geo-environment-receipt technical-state/geo_environment_receipt.json' in workflow
    assert '--geo-freeze "$GEO_FREEZE"' in workflow
    assert 'rasterio.open' not in workflow


def test_sealed_runtime_validates_geo_receipt_before_writing_entry_marker():
    runtime = RUNTIME.read_text(encoding='utf-8')
    validation = runtime.index('geo_environment = _geo_environment(')
    initial_state = runtime.index('state = {', validation)
    entered = runtime.index('state["sealed_read_entered"] = True', initial_state)
    inherited = runtime.index(
        'from . import v2_8_3_fresh_runtime as v283_runtime', entered
    )

    assert validation < initial_state < entered < inherited
    assert '"geo_environment_receipt_digest": geo_environment["receipt_digest"]' in runtime


def test_recovery_implementation_changes_only_the_allowed_runtime_surface():
    design = _load(DESIGN)
    freeze = _load(GEO_FREEZE)
    allowed = design['allowed_recovery_change']

    assert allowed['add_hash_locked_geo_extension_only'] is True
    assert allowed['rasterio_import_and_version_check_must_precede_source_artifact_download'] is True
    assert allowed['rasterio_import_and_version_check_must_precede_sealed_read_entry'] is True
    assert allowed['rasterio_import_check_may_not_open_any_raster'] is True
    assert allowed['separate_implementation_merge_required'] is True
    assert freeze['execution_boundary']['geo_runtime_freeze_complete'] is True
    assert freeze['execution_boundary']['sealed_recovery_dispatch_authorized'] is False
    assert freeze['execution_boundary']['product_b_unblocked'] is False


def test_authorization_verifier_recognizes_only_the_exact_final_third_dispatch():
    design = _load(DESIGN)
    freeze = _load(GEO_FREEZE)
    recovery = {
        'authorized': True,
        'prior_workflow_run_id': 33311324330,
        'prior_workflow_run_attempt': 1,
        'prior_head_sha': '586700d531fb815fa452e3a8ca31f4c97e070443',
        'prior_head_ref': 'refs/heads/frozen/product-a-v2-8-4-sealed-v1-pre-read-recovery-1',
        'prior_run_conclusion': 'failure',
        'prior_failure_fingerprint': "ModuleNotFoundError: No module named 'rasterio'",
        'prior_sealed_read_entered': True,
        'prior_sealed_environment_read': False,
        'prior_sealed_audit_completed': False,
        'prior_terminal_scientific_decision_exists': False,
        'prior_scientific_evidence_reused_or_reinterpreted': False,
        'additional_scientific_attempt_created': False,
        'recovery_change_scope': 'hash_locked_geo_extension_and_rasterio_import_gate_only',
        'recovery_design_contract_sha256': '682b610f8b426f3af1e31719124439511a8175618bbf7990f33085a920b92abf',
        'recovery_design_contract_digest': design['contract_digest'],
        'geo_runtime_freeze_sha256': 'eb2b61f424d51b77f74d8e974748686405380c3c9a6885896e389c82b3c23370',
        'geo_calibration_artifact_id': freeze['calibration_evidence']['artifact_id'],
        'geo_calibration_artifact_digest': freeze['calibration_evidence']['artifact_digest'],
    }
    auth = {
        'operational_attempt': 3,
        'authorized_ref': NO_VALUE_READ_RECOVERY_AUTHORIZED_REF,
        'post_entry_no_value_read_recovery': recovery,
        'one_shot_dispatch_policy': {
            'exact_workflow_dispatch_run_count_after_recovery_dispatch': 3,
            'both_prior_failure_runs_are_exactly_pinned': True,
            'current_recovery_run_must_be_the_only_third_dispatch': True,
            'fourth_workflow_dispatch_run_forbidden': True,
            'failed_job_retry_within_recovery_run_allowed': False,
        },
    }

    assert _verify_operational_attempt(auth, implementation_root=ROOT) == (
        3, NO_VALUE_READ_RECOVERY_AUTHORIZED_REF, 33311324330
    )
    changed = json.loads(json.dumps(auth))
    changed['post_entry_no_value_read_recovery']['prior_sealed_environment_read'] = True
    with pytest.raises(ValueError, match='no-value-read recovery identity changed'):
        _verify_operational_attempt(changed, implementation_root=ROOT)

    fourth = json.loads(json.dumps(auth))
    fourth['one_shot_dispatch_policy']['exact_workflow_dispatch_run_count_after_recovery_dispatch'] = 4
    with pytest.raises(ValueError, match='one-shot policy changed'):
        _verify_operational_attempt(fourth, implementation_root=ROOT)
