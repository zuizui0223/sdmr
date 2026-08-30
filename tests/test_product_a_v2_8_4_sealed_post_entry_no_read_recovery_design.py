import hashlib
import json
from pathlib import Path


DESIGN = Path('configs/product_a_v2_8_4_sealed_post_entry_no_read_recovery_design.json')


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def test_v284_post_entry_recovery_design_is_self_consistent_and_truth_blind():
    payload = json.loads(DESIGN.read_text())
    embedded = payload['contract_digest']
    body = dict(payload)
    body.pop('contract_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert embedded == '734bb7b6b3ea2c9b52a7df0c0762d139939d517aaa3310c1f58df484f4b651bf'
    assert payload['purpose'] == (
        'product_a_v2_8_4_sealed_post_entry_no_value_read_recovery_design'
    )
    assert payload['scientific_execution_id'] == (
        'product-a-v2-8-4-fresh-confirmation-v1'
    )
    assert payload['recovery_class'] == (
        'post_entry_marker_but_pre_environment_value_read'
    )


def test_v284_post_entry_recovery_pins_exact_failed_attempt_and_all_three_states():
    payload = json.loads(DESIGN.read_text())
    prior = payload['prior_operational_attempt']
    assert prior['operational_attempt'] == 2
    assert prior['workflow_run_id'] == 33311324330
    assert prior['workflow_run_attempt'] == 1
    assert prior['workflow_run_number'] == 2
    assert prior['head_sha'] == '586700d531fb815fa452e3a8ca31f4c97e070443'
    assert prior['implementation_ref'] == '6c075e1ebc13713c15ceaffd94fd4c4e61eb75ad'
    assert prior['authorization_receipt_digest'] == (
        '6d60e52b6ffdd8e020d1a124248520759e03d5f1e939d27dd486f980270185b8'
    )
    assert prior['truth_blind_gate_digest'] == (
        '4119b4957fba408e680feb3461490e00716cbb83f4c0b0c3d7d6cb8ba6464133'
    )
    assert prior['preflight_job']['job_id'] == 99256808858
    assert prior['preflight_job']['conclusion'] == 'success'
    assert prior['aggregate_job'] == {
        'conclusion': 'skipped',
        'job_id': 99257003805,
    }
    parts = prior['part_failures']
    assert {row['part_seed'] for row in parts} == {
        2026082201, 2026082202, 2026082203
    }
    assert {row['job_id'] for row in parts} == {
        99256889933, 99256889980, 99256889947
    }
    assert {row['state_artifact_id'] for row in parts} == {
        9732079692, 9732079619, 9732081137
    }
    assert all(row['conclusion'] == 'failure' for row in parts)


def test_v284_post_entry_recovery_requires_no_value_read_proof_and_new_contract():
    payload = json.loads(DESIGN.read_text())
    state = payload['prior_operational_attempt']['common_state_proof']
    assert state['pre_read_validation_complete'] is True
    assert state['sealed_read_entered'] is True
    assert state['retry_without_new_explicit_contract_allowed'] is False
    assert state['sealed_environment_read'] is False
    assert state['sealed_audit_completed'] is False
    assert state['sealed_audit_contract_exists'] is False
    assert state['terminal_scientific_decision_exists'] is False
    fingerprint = payload['prior_operational_attempt']['failure_fingerprint']
    assert fingerprint['exception'] == "ModuleNotFoundError: No module named 'rasterio'"
    assert fingerprint['failure_before_raster_dataset_open'] is True
    assert fingerprint['failure_before_environmental_value_extraction'] is True
    assert fingerprint['same_fingerprint_all_three_parts'] is True
    interpretation = payload['recovery_interpretation']
    assert interpretation['same_run_retry_allowed'] is False
    assert interpretation['broad_rerun_allowed'] is False
    assert interpretation['new_explicit_contract_required'] is True
    assert interpretation['immutable_state_and_logs_prove_no_environmental_value_read'] is True
    assert interpretation['scientific_outcome_was_not_observed'] is True
    assert interpretation['recovery_is_not_post_outcome_retuning'] is True


def test_v284_post_entry_recovery_allows_only_locked_geo_preflight_before_entry():
    payload = json.loads(DESIGN.read_text())
    allowed = payload['allowed_recovery_change']
    assert allowed['add_hash_locked_geo_extension_only'] is True
    assert allowed['geo_extension_must_retain_core_versions'] is True
    assert allowed['geo_lock_calibration_must_be_truth_blind'] is True
    assert allowed['geo_lock_calibration_may_not_access_scientific_source_or_receipts'] is True
    assert allowed['rasterio_import_and_version_check_must_precede_source_artifact_download'] is True
    assert allowed['rasterio_import_and_version_check_must_precede_sealed_read_entry'] is True
    assert allowed['rasterio_import_check_may_not_open_any_raster'] is True
    assert allowed['new_operational_attempt_number'] == 3
    assert allowed['maximum_total_workflow_dispatch_runs_after_recovery'] == 3
    assert allowed['fourth_workflow_dispatch_forbidden'] is True
    boundary = payload['execution_boundary']
    assert boundary['design_only'] is True
    assert boundary['truth_blind_geo_lock_calibration_allowed'] is True
    assert boundary['geo_runtime_freeze_exists'] is False
    assert boundary['recovery_dispatch_allowed'] is False
    assert boundary['sealed_ecological_outcomes_read'] is False
    assert boundary['scientific_decision_exists'] is False
    assert boundary['scientific_promotion_allowed'] is False
    assert boundary['product_b_unblocked'] is False


def test_v284_post_entry_recovery_preserves_every_scientific_identity():
    payload = json.loads(DESIGN.read_text())
    assert all(value is False for value in payload['scientific_invariants'].values())
