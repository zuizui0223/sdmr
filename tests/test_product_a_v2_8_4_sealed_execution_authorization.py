import hashlib
import json
from pathlib import Path

from sdmr.v2_8_4_sealed_authorization import verify_sealed_authorization


AUTH = Path('configs/product_a_v2_8_4_sealed_execution_authorization.json')
BOUNDARY = Path('configs/product_a_v2_8_4_sealed_boundary_contract.json')
CALLER = Path('.github/workflows/product-a-v2-8-4-sealed-authorized.yml')
IMPLEMENTATION_REF = '2690c169adc2d9261a13b4c801c8a02006fc7cca'
FROZEN_REF = 'refs/heads/frozen/product-a-v2-8-4-sealed-v1'


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_v284_sealed_authorization_receipt_is_self_consistent_and_exact(tmp_path):
    auth = json.loads(AUTH.read_text())
    embedded = auth['authorization_receipt_digest']
    body = dict(auth)
    body.pop('authorization_receipt_digest')
    assert hashlib.sha256(_canonical(body)).hexdigest() == embedded
    assert embedded == '23ffd9e3991a1a7a77614c03c47b2edde8142ef34c40c9d0b03c011a803e63c5'
    assert auth['purpose'] == 'product_a_v2_8_4_one_shot_sealed_execution_authorization'
    assert auth['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    assert auth['one_shot'] is True
    assert auth['authorized_ref'] == FROZEN_REF
    assert auth['implementation_identity']['runtime_ref'] == IMPLEMENTATION_REF
    assert _sha(CALLER) == auth['authorized_caller']['newline_canonical_sha256']

    gate = verify_sealed_authorization(
        authorization_path=AUTH,
        boundary_path=BOUNDARY,
        implementation_root='.',
        authorization_root='.',
        implementation_ref=IMPLEMENTATION_REF,
        reusable_workflow_sha256=auth['implementation_identity']['sealed_reusable_workflow_sha256'],
        caller_workflow_sha256=auth['authorized_caller']['newline_canonical_sha256'],
        authorization_commit_sha='authorization-commit-test',
        current_sha='authorization-commit-test',
        current_ref=FROZEN_REF,
        current_event='workflow_dispatch',
        output_path=tmp_path / 'authorization_gate.json',
    )
    assert gate['authorization_receipt_digest'] == embedded
    assert gate['one_shot_sealed_execution_authorized'] is True
    assert gate['pre_read_exact_retry_maximum_attempts_per_part'] == 2
    assert gate['retry_after_sealed_read_entered_allowed'] is False
    assert gate['sealed_ecological_outcomes_read'] is False
    assert gate['scientific_promotion_allowed'] is False
    assert gate['product_b_unblocked'] is False


def test_v284_sealed_authorization_receipts_exactly_equal_reviewed_boundary():
    auth = json.loads(AUTH.read_text())
    boundary = json.loads(BOUNDARY.read_text())
    assert auth['presealed_receipts'] == boundary['presealed_receipts']
    assert [row['part_seed'] for row in auth['presealed_receipts']] == [
        2026082201, 2026082202, 2026082203
    ]
    assert [row['artifact_id'] for row in auth['presealed_receipts']] == [
        9711004502, 9686345424, 9686776074
    ]


def test_v284_sealed_authorization_science_and_promotion_boundaries_are_unchanged():
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
        'candidate_predictor_universe_changed', 'candidate_library_changed',
        'thresholds_changed', 'taxa_changed', 'M_changed', 'seeds_changed',
        'fraction_changed', 'denominator_changed', 'decision_rule_changed',
        'scientific_promotion_allowed', 'product_b_unblocked',
    ):
        assert inv[key] is False
    assert auth['execution_boundary']['sealed_execution_allowed'] is True
    assert auth['execution_boundary']['sealed_ecological_outcomes_read'] is False
    assert auth['execution_boundary']['scientific_promotion_allowed'] is False
    assert auth['execution_boundary']['product_b_unblocked'] is False


def test_v284_sealed_authorized_caller_is_parameterless_frozen_ref_one_shot():
    text = CALLER.read_text()
    assert 'on:\n  workflow_dispatch:' in text
    assert 'inputs:' not in text
    assert "expected_ref='refs/heads/frozen/product-a-v2-8-4-sealed-v1'" in text
    assert "implementation_ref='2690c169adc2d9261a13b4c801c8a02006fc7cca'" in text
    assert 'total_count' in text and 'CURRENT_RUN_ID' in text
    assert "observed != [int(os.environ['CURRENT_RUN_ID'])]" in text
    assert 'uses: zuizui0223/sdmr/.github/workflows/product-a-v2-8-4-sealed-reusable.yml@2690c169adc2d9261a13b4c801c8a02006fc7cca' in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text
