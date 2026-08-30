import hashlib
import json
from pathlib import Path

from sdmr.v2_8_4_sealed_authorization import (
    RECOVERY_AUTHORIZED_REF,
    RECOVERY_DESIGN_PATH,
    REQUIRED_IMPLEMENTATION_PATHS,
    verify_sealed_authorization,
)


AUTH = Path('configs/product_a_v2_8_4_sealed_execution_authorization.json')
BOUNDARY = Path('configs/product_a_v2_8_4_sealed_boundary_contract.json')
CALLER = Path('.github/workflows/product-a-v2-8-4-sealed-authorized.yml')
RECOVERY = Path(RECOVERY_DESIGN_PATH)
IMPLEMENTATION_REF = '6c075e1ebc13713c15ceaffd94fd4c4e61eb75ad'
AUTH_DIGEST = '6d60e52b6ffdd8e020d1a124248520759e03d5f1e939d27dd486f980270185b8'
CALLER_SHA = '308f49bc23027bb1fcb4bd4d5fab3f1deb2b9f52ada509737ca81f853799be95'
WORKFLOW_SHA = '70a41190cba4af74264e6eabbe33f8c643b4af208bc7270d4ef42c86e1a7b88b'
RECOVERY_DESIGN_SHA = 'eea13cebc7bc9c3d6199522cd8de435a1c814625e92feda51496499e4ebeff9f'


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_v284_recovery_authorization_receipt_is_self_consistent_and_exact(tmp_path):
    auth = json.loads(AUTH.read_text())
    embedded = auth['authorization_receipt_digest']
    body = dict(auth)
    body.pop('authorization_receipt_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert embedded == AUTH_DIGEST
    assert auth['purpose'] == 'product_a_v2_8_4_one_shot_sealed_execution_authorization'
    assert auth['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    assert auth['one_shot'] is True
    assert auth['operational_attempt'] == 2
    assert auth['authorized_ref'] == RECOVERY_AUTHORIZED_REF
    assert auth['implementation_identity']['runtime_ref'] == IMPLEMENTATION_REF
    assert auth['implementation_identity']['sealed_reusable_workflow_sha256'] == WORKFLOW_SHA
    assert auth['authorized_caller']['newline_canonical_sha256'] == CALLER_SHA
    assert _sha(CALLER) == CALLER_SHA
    assert _sha(RECOVERY) == RECOVERY_DESIGN_SHA

    implementation_hashes = auth['implementation_identity']['newline_canonical_sha256']
    assert set(implementation_hashes) == set(REQUIRED_IMPLEMENTATION_PATHS)
    for relative in REQUIRED_IMPLEMENTATION_PATHS:
        assert _sha(Path(relative)) == implementation_hashes[relative]

    gate = verify_sealed_authorization(
        authorization_path=AUTH,
        boundary_path=BOUNDARY,
        implementation_root='.',
        authorization_root='.',
        implementation_ref=IMPLEMENTATION_REF,
        reusable_workflow_sha256=WORKFLOW_SHA,
        caller_workflow_sha256=CALLER_SHA,
        authorization_commit_sha='recovery-authorization-commit-test',
        current_sha='recovery-authorization-commit-test',
        current_ref=RECOVERY_AUTHORIZED_REF,
        current_event='workflow_dispatch',
        output_path=tmp_path / 'authorization_gate.json',
    )
    assert gate['authorization_receipt_digest'] == AUTH_DIGEST
    assert gate['operational_attempt'] == 2
    assert gate['recovery_of_pre_read_run_id'] == 33309627503
    assert gate['one_shot_sealed_execution_authorized'] is True
    assert gate['pre_read_exact_retry_maximum_attempts_per_part'] == 2
    assert gate['retry_after_sealed_read_entered_allowed'] is False
    assert gate['sealed_ecological_outcomes_read'] is False
    assert gate['scientific_promotion_allowed'] is False
    assert gate['product_b_unblocked'] is False


def test_v284_recovery_authorization_pins_exact_prior_pre_read_failure():
    auth = json.loads(AUTH.read_text())
    recovery = auth['pre_read_recovery']
    expected = {
        'prior_workflow_run_id': 33309627503,
        'prior_workflow_run_attempt': 1,
        'prior_head_sha': 'ba12f96be48545819a72fc714f083cd5c00520ad',
        'prior_head_ref': 'refs/heads/frozen/product-a-v2-8-4-sealed-v1',
        'prior_caller_preflight_job_id': 99252220557,
        'prior_failed_reusable_preflight_job_id': 99252233545,
        'prior_sealed_part_job_id': 99252247454,
        'prior_aggregate_decision_job_id': 99252247966,
        'prior_run_conclusion': 'failure',
        'prior_failure_stage': 'authorization-and-receipt-preflight',
        'prior_failure_fingerprint': "ModuleNotFoundError: No module named 'pandas'",
        'prior_failure_before_environment_setup': True,
        'prior_presealed_receipt_downloaded': False,
        'prior_sealed_source_accessed': False,
        'prior_sealed_read_entered': False,
        'prior_sealed_ecological_outcomes_read': False,
        'prior_scientific_decision_exists': False,
    }
    for key, value in expected.items():
        assert recovery[key] == value
    assert recovery['authorized'] is True
    assert recovery['only_prior_pre_read_failure_is_superseded'] is True
    assert recovery['prior_scientific_evidence_reused_or_reinterpreted'] is False
    assert recovery['additional_scientific_attempt_created'] is False
    assert recovery['recovery_change_scope'] == (
        'stdlib_only_authorization_bootstrap_without_scientific_or_sealed_access_change'
    )
    assert recovery['recovery_design_contract_sha256'] == RECOVERY_DESIGN_SHA
    assert auth['authorization_basis']['prior_attempt_pre_read_failure_verified'] is True
    assert auth['authorization_basis'][
        'no_sealed_ecological_outcome_was_read_before_authorization'
    ] is True


def test_v284_recovery_authorization_receipts_equal_reviewed_boundary():
    auth = json.loads(AUTH.read_text())
    boundary = json.loads(BOUNDARY.read_text())
    assert auth['presealed_receipts'] == boundary['presealed_receipts']
    assert [row['part_seed'] for row in auth['presealed_receipts']] == [
        2026082201, 2026082202, 2026082203
    ]
    assert [row['artifact_id'] for row in auth['presealed_receipts']] == [
        9711004502, 9686345424, 9686776074
    ]


def test_v284_recovery_science_and_promotion_boundaries_are_unchanged():
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


def test_v284_recovery_dispatch_policy_is_exactly_second_and_terminal():
    auth = json.loads(AUTH.read_text())
    assert auth['one_shot_dispatch_policy'] == {
        'current_recovery_run_must_be_the_only_second_dispatch': True,
        'exact_workflow_dispatch_run_count_after_recovery_dispatch': 2,
        'failed_job_retry_within_recovery_run_retains_run_identity': True,
        'no_third_workflow_dispatch_run_allowed': True,
        'prior_pre_read_failure_run_is_exactly_pinned': True,
    }


def test_v284_recovery_caller_is_parameterless_and_live_checks_prior_failure():
    text = CALLER.read_text()
    assert 'on:\n  workflow_dispatch:' in text
    assert 'inputs:' not in text
    assert (
        "expected_ref='refs/heads/frozen/product-a-v2-8-4-sealed-v1-pre-read-recovery-1'"
    ) in text
    assert "implementation_ref='6c075e1ebc13713c15ceaffd94fd4c4e61eb75ad'" in text
    for identity in (
        'prior_run_id=33309627503',
        '99252220557',
        '99252233545',
        '99252247454',
        '99252247966',
        "'total_count',-1)) == 2",
        "'total_count',-1)) > 2",
        'artifacts?per_page=100',
        'prior_sealed_read_entered',
        'prior_sealed_ecological_outcomes_read',
    ):
        assert identity in text
    assert (
        'uses: zuizui0223/sdmr/.github/workflows/'
        'product-a-v2-8-4-sealed-reusable.yml@'
        '6c075e1ebc13713c15ceaffd94fd4c4e61eb75ad'
    ) in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text


def test_v284_recovery_design_remains_truth_blind_and_design_only():
    recovery = json.loads(RECOVERY.read_text())
    embedded = recovery['contract_digest']
    body = dict(recovery)
    body.pop('contract_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert recovery['scientific_execution_id'] == (
        'product-a-v2-8-4-fresh-confirmation-v1'
    )
    boundary = recovery['execution_boundary']
    assert boundary['design_only'] is True
    assert boundary['sealed_ecological_outcomes_read'] is False
    assert boundary['scientific_promotion_allowed'] is False
    assert boundary['product_b_unblocked'] is False
