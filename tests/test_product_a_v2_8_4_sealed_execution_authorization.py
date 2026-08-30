import hashlib
import json
from pathlib import Path


AUTH = Path('configs/product_a_v2_8_4_sealed_execution_authorization.json')
BOUNDARY = Path('configs/product_a_v2_8_4_sealed_boundary_contract.json')
CALLER = Path('.github/workflows/product-a-v2-8-4-sealed-authorized.yml')
WORKFLOW = Path('.github/workflows/product-a-v2-8-4-sealed-reusable.yml')
AUTH_VERIFIER = Path('src/sdmr/v2_8_4_sealed_authorization.py')
RECOVERY = Path('configs/product_a_v2_8_4_sealed_pre_read_recovery_contract.json')
IMPLEMENTATION_REF = '2690c169adc2d9261a13b4c801c8a02006fc7cca'
FROZEN_REF = 'refs/heads/frozen/product-a-v2-8-4-sealed-v1'


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_v284_initial_sealed_authorization_remains_historically_exact():
    auth = json.loads(AUTH.read_text())
    embedded = auth['authorization_receipt_digest']
    body = dict(auth)
    body.pop('authorization_receipt_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert embedded == '23ffd9e3991a1a7a77614c03c47b2edde8142ef34c40c9d0b03c011a803e63c5'
    assert auth['purpose'] == 'product_a_v2_8_4_one_shot_sealed_execution_authorization'
    assert auth['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    assert auth['one_shot'] is True
    assert int(auth.get('operational_attempt', 1)) == 1
    assert auth['authorized_ref'] == FROZEN_REF
    assert auth['implementation_identity']['runtime_ref'] == IMPLEMENTATION_REF
    assert _sha(CALLER) == auth['authorized_caller']['newline_canonical_sha256']
    assert auth['implementation_identity']['sealed_reusable_workflow_sha256'] == (
        '7972404f2f5bc23e7e6fc854c2a476fe05609665db8562b865e5680937da0acb'
    )

    # The recovery implementation must not be silently accepted by the old
    # authorization.  A new reviewed receipt has to pin both changed files.
    pins = auth['implementation_identity']['newline_canonical_sha256']
    assert _sha(WORKFLOW) != pins[str(WORKFLOW)]
    assert _sha(AUTH_VERIFIER) != pins[str(AUTH_VERIFIER)]


def test_v284_initial_sealed_authorization_receipts_equal_reviewed_boundary():
    auth = json.loads(AUTH.read_text())
    boundary = json.loads(BOUNDARY.read_text())
    assert auth['presealed_receipts'] == boundary['presealed_receipts']
    assert [row['part_seed'] for row in auth['presealed_receipts']] == [
        2026082201, 2026082202, 2026082203
    ]
    assert [row['artifact_id'] for row in auth['presealed_receipts']] == [
        9711004502, 9686345424, 9686776074
    ]


def test_v284_initial_sealed_authorization_science_boundaries_are_unchanged():
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


def test_v284_initial_sealed_authorized_caller_is_parameterless_frozen_ref_one_shot():
    text = CALLER.read_text()
    assert 'on:\n  workflow_dispatch:' in text
    assert 'inputs:' not in text
    assert "expected_ref='refs/heads/frozen/product-a-v2-8-4-sealed-v1'" in text
    assert "implementation_ref='2690c169adc2d9261a13b4c801c8a02006fc7cca'" in text
    assert 'total_count' in text and 'CURRENT_RUN_ID' in text
    assert "observed != [int(os.environ['CURRENT_RUN_ID'])]" in text
    assert (
        'uses: zuizui0223/sdmr/.github/workflows/'
        'product-a-v2-8-4-sealed-reusable.yml@'
        '2690c169adc2d9261a13b4c801c8a02006fc7cca'
    ) in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text


def test_v284_pre_read_recovery_design_is_truth_blind_and_exact():
    recovery = json.loads(RECOVERY.read_text())
    embedded = recovery['contract_digest']
    body = dict(recovery)
    body.pop('contract_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert recovery['purpose'] == 'product_a_v2_8_4_sealed_pre_read_recovery_design'
    assert recovery['scientific_execution_id'] == (
        'product-a-v2-8-4-fresh-confirmation-v1'
    )
    prior = recovery['prior_operational_attempt']
    assert prior['workflow_run_id'] == 33309627503
    assert prior['workflow_run_attempt'] == 1
    assert prior['caller_authorization_preflight_job_id'] == 99252220557
    assert prior['failed_reusable_preflight_job_id'] == 99252233545
    assert prior['sealed_part_job_id'] == 99252247454
    assert prior['aggregate_decision_job_id'] == 99252247966
    assert prior['failure_fingerprint'] == (
        "ModuleNotFoundError: No module named 'pandas'"
    )
    assert prior['presealed_receipt_downloaded'] is False
    assert prior['sealed_source_accessed'] is False
    assert prior['sealed_read_state_created'] is False
    assert prior['sealed_read_entered'] is False
    assert prior['sealed_ecological_outcomes_read'] is False
    assert prior['scientific_decision_exists'] is False
    assert prior['run_artifact_count'] == 0

    allowed = recovery['allowed_recovery_change']
    assert allowed['scope'] == (
        'stdlib_only_authorization_bootstrap_without_scientific_or_sealed_access_change'
    )
    assert allowed['authorization_remains_before_dependency_install'] is True
    assert allowed['authorization_remains_before_receipt_download'] is True
    assert allowed['authorization_remains_before_sealed_source_access'] is True
    assert allowed['maximum_total_workflow_dispatch_runs_for_this_recovery'] == 2
    assert allowed['new_operational_attempt_number'] == 2

    boundary = recovery['execution_boundary']
    assert boundary['design_only'] is True
    assert boundary['recovery_implementation_reviewed'] is False
    assert boundary['recovery_authorization_exists'] is False
    assert boundary['recovery_dispatch_allowed'] is False
    assert boundary['sealed_ecological_outcomes_read'] is False
    assert boundary['scientific_promotion_allowed'] is False
    assert boundary['product_b_unblocked'] is False

    for key, value in recovery['scientific_invariants'].items():
        assert value is False, key
