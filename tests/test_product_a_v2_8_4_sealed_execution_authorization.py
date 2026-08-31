import hashlib
import json
from pathlib import Path

from sdmr.v2_8_4_sealed_authorization import (
    NO_VALUE_READ_RECOVERY_AUTHORIZED_REF,
    NO_VALUE_READ_RECOVERY_DESIGN_PATH,
    NO_VALUE_READ_RECOVERY_IMPLEMENTATION_PATHS,
    REQUIRED_IMPLEMENTATION_PATHS,
    verify_sealed_authorization,
)


AUTH = Path('configs/product_a_v2_8_4_sealed_execution_authorization.json')
BOUNDARY = Path('configs/product_a_v2_8_4_sealed_boundary_contract.json')
CALLER = Path('.github/workflows/product-a-v2-8-4-sealed-authorized.yml')
DESIGN = Path(NO_VALUE_READ_RECOVERY_DESIGN_PATH)
IMPLEMENTATION_REF = 'a12816a774f23e86ae52902cef6e2e47c61bd852'
AUTH_DIGEST = '23409c0f6cd015b8468bc2d99e626a7b0abe2b4ef0053c6e40bff072fa52e239'
CALLER_SHA = '9d36954aaed0ad700428fa6e78ff0cc39f76de75fdbb2f66fd6b6f60e3c494c6'
WORKFLOW_SHA = 'cdc2a662c41ef22b3079007a69f73dc9195592cf2f2a9c385a79c653d32341d8'
DESIGN_SHA = '682b610f8b426f3af1e31719124439511a8175618bbf7990f33085a920b92abf'
GEO_FREEZE_SHA = 'eb2b61f424d51b77f74d8e974748686405380c3c9a6885896e389c82b3c23370'


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_v284_final_recovery_authorization_is_self_consistent_and_exact(tmp_path):
    auth = json.loads(AUTH.read_text())
    embedded = auth['authorization_receipt_digest']
    body = dict(auth)
    body.pop('authorization_receipt_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert embedded == AUTH_DIGEST
    assert auth['purpose'] == 'product_a_v2_8_4_one_shot_sealed_execution_authorization'
    assert auth['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    assert auth['one_shot'] is True
    assert auth['operational_attempt'] == 3
    assert auth['authorized_ref'] == NO_VALUE_READ_RECOVERY_AUTHORIZED_REF
    assert auth['implementation_identity']['runtime_ref'] == IMPLEMENTATION_REF
    assert auth['implementation_identity']['sealed_reusable_workflow_sha256'] == WORKFLOW_SHA
    assert auth['authorized_caller']['newline_canonical_sha256'] == CALLER_SHA
    assert _sha(CALLER) == CALLER_SHA
    assert _sha(DESIGN) == DESIGN_SHA

    implementation_hashes = auth['implementation_identity']['newline_canonical_sha256']
    required = REQUIRED_IMPLEMENTATION_PATHS + NO_VALUE_READ_RECOVERY_IMPLEMENTATION_PATHS
    assert set(implementation_hashes) == set(required)
    for relative in required:
        assert _sha(Path(relative)) == implementation_hashes[relative]

    gate = verify_sealed_authorization(
        authorization_path=AUTH,
        boundary_path=BOUNDARY,
        implementation_root='.',
        authorization_root='.',
        implementation_ref=IMPLEMENTATION_REF,
        reusable_workflow_sha256=WORKFLOW_SHA,
        caller_workflow_sha256=CALLER_SHA,
        authorization_commit_sha='attempt-3-authorization-commit-test',
        current_sha='attempt-3-authorization-commit-test',
        current_ref=NO_VALUE_READ_RECOVERY_AUTHORIZED_REF,
        current_event='workflow_dispatch',
        output_path=tmp_path / 'authorization_gate.json',
    )
    assert gate['authorization_receipt_digest'] == AUTH_DIGEST
    assert gate['operational_attempt'] == 3
    assert gate['recovery_of_pre_read_run_id'] == 33311324330
    assert gate['one_shot_sealed_execution_authorized'] is True
    assert gate['pre_read_exact_retry_maximum_attempts_per_part'] is None
    assert gate['current_recovery_is_final_workflow_dispatch'] is True
    assert gate['retry_after_sealed_read_entered_allowed'] is False
    assert gate['sealed_ecological_outcomes_read'] is False
    assert gate['scientific_promotion_allowed'] is False
    assert gate['product_b_unblocked'] is False


def test_v284_final_recovery_pins_exact_no_value_read_failure_and_state_artifacts():
    auth = json.loads(AUTH.read_text())
    recovery = auth['post_entry_no_value_read_recovery']
    expected = {
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
        'prior_raster_dataset_opened': False,
        'prior_scientific_evidence_reused_or_reinterpreted': False,
        'additional_scientific_attempt_created': False,
        'recovery_change_scope': 'hash_locked_geo_extension_and_rasterio_import_gate_only',
        'recovery_design_contract_sha256': DESIGN_SHA,
        'recovery_design_contract_digest': (
            'a8ad67627b05c498e7b3c8569c33b23f664fb7cf2cfcbbdeaeb136abfae12877'
        ),
        'geo_runtime_freeze_sha256': GEO_FREEZE_SHA,
        'geo_calibration_artifact_id': 9746245575,
        'geo_calibration_artifact_digest': (
            'sha256:bfbee09b9424d6c87f68246b7b093c6223e2fd6f750e726997c27c45167dfcf5'
        ),
    }
    for key, value in expected.items():
        assert recovery[key] == value
    assert recovery['authorized'] is True
    assert recovery['prior_exact_input_artifact_count_per_part'] == 15
    assert recovery['prior_preflight_job_id'] == 99256808858
    assert recovery['prior_aggregate_decision_job_id'] == 99257003805
    states = recovery['prior_state_artifacts']
    assert {row['part_seed'] for row in states} == {2026082201, 2026082202, 2026082203}
    assert {row['job_id'] for row in states} == {99256889933, 99256889980, 99256889947}
    assert {row['artifact_id'] for row in states} == {9732079692, 9732079619, 9732081137}
    assert auth['authorization_basis']['prior_attempt_no_value_read_failure_verified'] is True
    assert auth['authorization_basis']['truth_blind_geo_runtime_freeze_verified'] is True
    assert auth['authorization_basis']['no_sealed_ecological_outcome_was_read_before_authorization'] is True


def test_v284_final_recovery_pins_both_prior_dispatches_and_forbids_more():
    auth = json.loads(AUTH.read_text())
    assert auth['prior_dispatches'] == [
        {
            'head_ref': 'refs/heads/frozen/product-a-v2-8-4-sealed-v1',
            'head_sha': 'ba12f96be48545819a72fc714f083cd5c00520ad',
            'interpretation': 'technical_pre_read_failure_not_scientific_negative',
            'operational_attempt': 1,
            'run_attempt': 1,
            'run_conclusion': 'failure',
            'run_id': 33309627503,
            'run_number': 1,
            'sealed_ecological_outcomes_read': False,
        },
        {
            'head_ref': 'refs/heads/frozen/product-a-v2-8-4-sealed-v1-pre-read-recovery-1',
            'head_sha': '586700d531fb815fa452e3a8ca31f4c97e070443',
            'interpretation': 'technical_post_entry_no_value_read_failure_not_scientific_negative',
            'operational_attempt': 2,
            'run_attempt': 1,
            'run_conclusion': 'failure',
            'run_id': 33311324330,
            'run_number': 2,
            'sealed_ecological_outcomes_read': False,
        },
    ]
    assert auth['one_shot_dispatch_policy'] == {
        'both_prior_failure_runs_are_exactly_pinned': True,
        'current_recovery_run_must_be_the_only_third_dispatch': True,
        'exact_workflow_dispatch_run_count_after_recovery_dispatch': 3,
        'failed_job_retry_within_recovery_run_allowed': False,
        'fourth_workflow_dispatch_run_forbidden': True,
    }
    assert auth['retry_policy'] == {
        'broad_rerun_of_successful_sealed_part_allowed': False,
        'current_recovery_is_final_workflow_dispatch': True,
        'fourth_workflow_dispatch_allowed': False,
        'new_explicit_contract_required_after_prior_sealed_read_entry': True,
        'same_run_job_retry_allowed': False,
        'scientific_null_negative_or_unavailable_outcome_retry_allowed': False,
    }


def test_v284_final_recovery_freezes_environment_timeout_checkpoint_and_receipt_barrier():
    auth = json.loads(AUTH.read_text())
    runtime = auth['runtime_environment']
    assert runtime['runner'] == 'ubuntu-24.04'
    assert runtime['python_patch'] == '3.12.11'
    assert runtime['core_environment_digest'] == (
        'a7f740e3bf8fd52d33be76384b04419012b59b7a1e190b29c4520113c9c468fb'
    )
    assert runtime['geo_lock_sha256'] == (
        '7171172058fbd73c99c1894b5931f59b6a012fd322901ee0a3f4c8e4b15121ef'
    )
    assert runtime['package_versions']['rasterio'] == '1.5.1'
    assert auth['timeout_policy'] == {
        'aggregate_decision_job_timeout_minutes': 30,
        'authorization_and_receipt_preflight_timeout_minutes': 30,
        'post_launch_timeout_extension_allowed': False,
        'post_outcome_timeout_retuning_allowed': False,
        'sealed_part_job_timeout_minutes': 180,
    }
    checkpoint = auth['checkpoint_and_retry_identity']
    assert checkpoint['attempt_3_is_final_workflow_dispatch'] is True
    assert checkpoint['same_run_job_retry_allowed'] is False
    assert checkpoint['fourth_workflow_dispatch_allowed'] is False
    barrier = auth['receipt_barrier']
    assert barrier['presealed_receipt_count'] == 3
    assert barrier['exact_input_artifact_count_per_part'] == 15
    assert barrier['rasterio_import_and_version_receipt_must_precede_any_input_artifact_download'] is True
    assert barrier['rasterio_import_receipt_must_open_no_raster'] is True


def test_v284_final_recovery_receipts_equal_reviewed_boundary():
    auth = json.loads(AUTH.read_text())
    boundary = json.loads(BOUNDARY.read_text())
    assert auth['presealed_receipts'] == boundary['presealed_receipts']
    assert [row['part_seed'] for row in auth['presealed_receipts']] == [
        2026082201, 2026082202, 2026082203
    ]
    assert [row['artifact_id'] for row in auth['presealed_receipts']] == [
        9711004502, 9686345424, 9686776074
    ]


def test_v284_final_recovery_science_and_promotion_boundaries_are_unchanged():
    auth = json.loads(AUTH.read_text())
    inv = auth['scientific_invariants']
    assert inv['sealed_fraction'] == 0.25
    assert inv['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert inv['M_km'] == [150, 300, 500]
    assert inv['model_random_state'] == 0
    assert inv['selection_process_numpy_seed'] == 0
    assert inv['primary_denominator'] == 3
    assert inv['prediction_guardrail_mean_presence_rank_delta_vs_auc_min'] == -0.01
    assert inv['ecological_nondomination_minimum_parts'] == 2
    assert inv['strict_ecological_improvement_minimum_parts'] == 2
    assert inv['process_modal_status_fraction_min'] == 2.0 / 3.0
    for key in (
        'candidate_predictor_universe_changed',
        'candidate_library_changed',
        'thresholds_changed',
        'taxa_changed',
        'M_changed',
        'seeds_changed',
        'fraction_changed',
        'denominator_changed',
        'decision_rule_changed',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    ):
        assert inv[key] is False
    assert auth['execution_boundary']['sealed_execution_allowed'] is True
    assert auth['execution_boundary']['sealed_ecological_outcomes_read'] is False
    assert auth['execution_boundary']['scientific_promotion_allowed'] is False
    assert auth['execution_boundary']['product_b_unblocked'] is False


def test_v284_final_recovery_caller_is_parameterless_and_live_checks_all_receipts():
    text = CALLER.read_text()
    assert 'on:\n  workflow_dispatch:' in text
    assert 'inputs:' not in text
    assert (
        "expected_ref='refs/heads/frozen/product-a-v2-8-4-sealed-v1-no-value-read-recovery-1'"
    ) in text
    assert f"implementation_ref='{IMPLEMENTATION_REF}'" in text
    for identity in (
        'first_run_id=33309627503',
        'second_run_id=33311324330',
        '99252233545',
        '99256808858',
        '99256889933',
        '99256889980',
        '99256889947',
        '99257003805',
        '9732069061',
        '9732079692',
        '9732079619',
        '9732081137',
        "'total_count',-1)) == 3",
        "'total_count',-1)) > 3",
        "CURRENT_RUN_ATTEMPT: ${{ github.run_attempt }}",
        "os.environ['CURRENT_RUN_ATTEMPT'] != '1'",
        'artifacts?per_page=100',
        'prior_sealed_environment_read',
        'prior_terminal_scientific_decision_exists',
    ):
        assert identity in text
    assert (
        'uses: zuizui0223/sdmr/.github/workflows/'
        f'product-a-v2-8-4-sealed-reusable.yml@{IMPLEMENTATION_REF}'
    ) in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text


def test_v284_final_recovery_design_remains_truth_blind_and_design_only():
    design = json.loads(DESIGN.read_text())
    embedded = design['contract_digest']
    body = dict(design)
    body.pop('contract_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert design['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    assert design['recovery_class'] == 'post_entry_marker_but_pre_environment_value_read'
    boundary = design['execution_boundary']
    assert boundary['design_only'] is True
    assert boundary['sealed_ecological_outcomes_read'] is False
    assert boundary['scientific_decision_exists'] is False
    assert boundary['scientific_promotion_allowed'] is False
    assert boundary['product_b_unblocked'] is False
