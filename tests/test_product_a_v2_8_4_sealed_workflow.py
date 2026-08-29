import hashlib
import json
from pathlib import Path

import pytest

from sdmr.v2_8_4_sealed_authorization import (
    REQUIRED_IMPLEMENTATION_PATHS,
    verify_sealed_authorization,
)


WORKFLOW = Path('.github/workflows/product-a-v2-8-4-sealed-reusable.yml')
BOUNDARY = Path('configs/product_a_v2_8_4_sealed_boundary_contract.json')
RUNTIME = Path('src/sdmr/v2_8_4_sealed_runtime.py')
AUTH = Path('src/sdmr/v2_8_4_sealed_authorization.py')


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def _authorization(tmp_path: Path) -> tuple[Path, str, str]:
    boundary = json.loads(BOUNDARY.read_text())
    auth_root = tmp_path / 'authorization-root'
    caller = auth_root / '.github/workflows/product-a-v2-8-4-sealed-authorized.yml'
    caller.parent.mkdir(parents=True)
    caller.write_text('name: Product-A v2.8.4 sealed authorized\non:\n  workflow_dispatch:\n', encoding='utf-8')
    caller_sha = _file_sha(caller)
    workflow_sha = _file_sha(WORKFLOW)
    hashes = {relative: _file_sha(Path(relative)) for relative in REQUIRED_IMPLEMENTATION_PATHS}
    payload = {
        'purpose': 'product_a_v2_8_4_one_shot_sealed_execution_authorization',
        'tracks_issue': 170,
        'scientific_execution_id': 'product-a-v2-8-4-fresh-confirmation-v1',
        'one_shot': True,
        'implementation_identity': {
            'runtime_ref': 'implementation-ref-test',
            'sealed_reusable_workflow_sha256': workflow_sha,
            'newline_canonical_sha256': hashes,
        },
        'authorized_caller': {
            'path': '.github/workflows/product-a-v2-8-4-sealed-authorized.yml',
            'newline_canonical_sha256': caller_sha,
        },
        'presealed_receipts': boundary['presealed_receipts'],
        'scientific_invariants': {
            'sealed_fraction': 0.25,
            'split_seeds': [2026082201, 2026082202, 2026082203],
            'M_km': [150, 300, 500],
            'model_random_state': 0,
            'selection_process_numpy_seed': 0,
            'primary_denominator': 3,
            'prediction_guardrail_mean_presence_rank_delta_vs_auc_min': -0.01,
            'ecological_nondomination_minimum_parts': 2,
            'strict_ecological_improvement_minimum_parts': 2,
            'process_modal_status_fraction_min': 2.0 / 3.0,
            'candidate_predictor_universe_changed': False,
            'candidate_library_changed': False,
            'thresholds_changed': False,
            'taxa_changed': False,
            'M_changed': False,
            'seeds_changed': False,
            'fraction_changed': False,
            'denominator_changed': False,
            'decision_rule_changed': False,
            'scientific_promotion_allowed': False,
            'product_b_unblocked': False,
        },
        'execution_boundary': {
            'sealed_workflow_implemented_and_reviewed': True,
            'sealed_execution_authorization_exists': True,
            'sealed_execution_allowed': True,
            'workflow_dispatch_allowed': True,
            'sealed_ecological_outcomes_read': False,
            'scientific_promotion_allowed': False,
            'product_b_unblocked': False,
        },
        'retry_policy': {
            'pre_read_exact_retry_allowed_only_if_sealed_read_entered_false': True,
            'maximum_pre_read_attempts_per_part': 2,
            'retry_after_sealed_read_entered_allowed': False,
            'broad_rerun_of_successful_sealed_part_allowed': False,
            'scientific_null_negative_or_unavailable_outcome_retry_allowed': False,
        },
    }
    payload['authorization_receipt_digest'] = hashlib.sha256(_canonical(payload)).hexdigest()
    auth_path = auth_root / 'configs/product_a_v2_8_4_sealed_execution_authorization.json'
    auth_path.parent.mkdir(parents=True)
    auth_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return auth_path, workflow_sha, caller_sha


def test_v284_sealed_workflow_is_non_dispatchable_and_ordered_fail_closed():
    text = WORKFLOW.read_text()
    assert 'on:\n  workflow_call:' in text
    assert 'workflow_dispatch:' not in text
    for action in (
        'actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
        'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
        'actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093',
        'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
    ):
        assert action in text
    assert '@v4' not in text and '@v5' not in text
    assert text.index('Verify separate one-shot authorization before any sealed source access') < text.index('Fail closed on runner-environment drift before any sealed source access')
    assert text.index('Fail closed on this part runner before downloading sealed-source artifacts') < text.index('name: v283-fresh-part-${{ matrix.seed }}')
    assert text.index('Verify exactly 15 receipt-pinned input artifacts before any download') < text.index('name: v283-fresh-part-${{ matrix.seed }}')
    assert text.index('--state technical-state/sealed_read_state.json') < text.index('product-a-v2-8-4-sealed-state-${{ matrix.seed }}')
    assert 'if: always()' in text
    assert 'max-parallel: 3' in text
    for seed in ('2026082201', '2026082202', '2026082203'):
        assert seed in text
    assert 'aggregate-decision:\n    needs: sealed-part' in text
    assert 'product-a-v2-8-4-terminal-decision' in text


def test_v284_sealed_runtime_marks_no_retry_before_importing_inherited_sealed_core():
    text = RUNTIME.read_text()
    entered = text.index('state["sealed_read_entered"] = True')
    no_retry = text.index('state["retry_without_new_explicit_contract_allowed"] = False')
    inherited = text.index('from . import v2_8_3_fresh_runtime as v283_runtime')
    assert entered < no_retry < inherited
    assert 'candidate_or_threshold_retuning_after_sealed_read' in text
    assert 'random_seed_change_after_sealed_read' in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text


def test_v284_authorization_verifier_is_truth_blind_and_accepts_only_exact_contract(tmp_path):
    auth_text = AUTH.read_text()
    assert 'v2_8_3_fresh_runtime' not in auth_text
    assert 'fresh_sealed_audit' not in auth_text
    assert 'rasterio' not in auth_text
    auth_path, workflow_sha, caller_sha = _authorization(tmp_path)
    gate = verify_sealed_authorization(
        authorization_path=auth_path,
        boundary_path=BOUNDARY,
        implementation_root='.',
        authorization_root=auth_path.parents[1],
        implementation_ref='implementation-ref-test',
        reusable_workflow_sha256=workflow_sha,
        caller_workflow_sha256=caller_sha,
        authorization_commit_sha='authorization-commit-test',
        current_sha='authorization-commit-test',
        current_ref='refs/heads/main',
        current_event='workflow_dispatch',
        output_path=tmp_path / 'gate.json',
    )
    assert gate['one_shot_sealed_execution_authorized'] is True
    assert gate['retry_after_sealed_read_entered_allowed'] is False
    assert gate['sealed_ecological_outcomes_read'] is False
    assert gate['scientific_promotion_allowed'] is False
    assert gate['product_b_unblocked'] is False


def test_v284_authorization_verifier_rejects_promotion_or_commit_drift(tmp_path):
    auth_path, workflow_sha, caller_sha = _authorization(tmp_path)
    payload = json.loads(auth_path.read_text())
    payload['scientific_invariants']['scientific_promotion_allowed'] = True
    body = dict(payload)
    body.pop('authorization_receipt_digest')
    payload['authorization_receipt_digest'] = hashlib.sha256(_canonical(body)).hexdigest()
    auth_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    with pytest.raises(ValueError, match='scientific boundary'):
        verify_sealed_authorization(
            authorization_path=auth_path,
            boundary_path=BOUNDARY,
            implementation_root='.',
            authorization_root=auth_path.parents[1],
            implementation_ref='implementation-ref-test',
            reusable_workflow_sha256=workflow_sha,
            caller_workflow_sha256=caller_sha,
            authorization_commit_sha='authorization-commit-test',
            current_sha='authorization-commit-test',
            current_ref='refs/heads/main',
            current_event='workflow_dispatch',
            output_path=tmp_path / 'bad-gate.json',
        )

    auth_path, workflow_sha, caller_sha = _authorization(tmp_path / 'second')
    with pytest.raises(ValueError, match='exact merge commit'):
        verify_sealed_authorization(
            authorization_path=auth_path,
            boundary_path=BOUNDARY,
            implementation_root='.',
            authorization_root=auth_path.parents[1],
            implementation_ref='implementation-ref-test',
            reusable_workflow_sha256=workflow_sha,
            caller_workflow_sha256=caller_sha,
            authorization_commit_sha='authorization-commit-test',
            current_sha='different-commit',
            current_ref='refs/heads/main',
            current_event='workflow_dispatch',
            output_path=tmp_path / 'bad-commit-gate.json',
        )
