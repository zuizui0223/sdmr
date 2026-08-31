import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from sdmr.v2_8_4_sealed_authorization import (
    INITIAL_AUTHORIZED_REF,
    PRIOR_PRE_READ_FAILURE,
    RECOVERY_AUTHORIZED_REF,
    RECOVERY_DESIGN_PATH,
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


def _authorization(
    tmp_path: Path, *, operational_attempt: int = 1
) -> tuple[Path, str, str]:
    boundary = json.loads(BOUNDARY.read_text())
    auth_root = tmp_path / 'authorization-root'
    caller = auth_root / '.github/workflows/product-a-v2-8-4-sealed-authorized.yml'
    caller.parent.mkdir(parents=True)
    caller.write_text(
        'name: Product-A v2.8.4 sealed authorized\non:\n  workflow_dispatch:\n',
        encoding='utf-8',
    )
    caller_sha = _file_sha(caller)
    workflow_sha = _file_sha(WORKFLOW)
    hashes = {
        relative: _file_sha(Path(relative))
        for relative in REQUIRED_IMPLEMENTATION_PATHS
    }
    recovery = None
    basis = {
        'no_sealed_ecological_outcome_was_read_before_authorization': True,
    }
    if operational_attempt == 1:
        authorized_ref = INITIAL_AUTHORIZED_REF
        dispatch_policy = {
            'exactly_one_workflow_dispatch_run_allowed': True,
            'failed_job_retry_within_same_run_retains_run_identity': True,
            'second_workflow_dispatch_run_must_fail_before_reusable_call': True,
        }
    else:
        authorized_ref = RECOVERY_AUTHORIZED_REF
        basis['prior_attempt_pre_read_failure_verified'] = True
        dispatch_policy = {
            'exact_workflow_dispatch_run_count_after_recovery_dispatch': 2,
            'prior_pre_read_failure_run_is_exactly_pinned': True,
            'current_recovery_run_must_be_the_only_second_dispatch': True,
            'no_third_workflow_dispatch_run_allowed': True,
            'failed_job_retry_within_recovery_run_retains_run_identity': True,
        }
        recovery = {
            **PRIOR_PRE_READ_FAILURE,
            'authorized': True,
            'recovery_change_scope': (
                'stdlib_only_authorization_bootstrap_without_scientific_or_sealed_access_change'
            ),
            'only_prior_pre_read_failure_is_superseded': True,
            'prior_scientific_evidence_reused_or_reinterpreted': False,
            'additional_scientific_attempt_created': False,
            'recovery_design_contract_sha256': _file_sha(Path(RECOVERY_DESIGN_PATH)),
        }

    payload = {
        'purpose': 'product_a_v2_8_4_one_shot_sealed_execution_authorization',
        'tracks_issue': 170,
        'scientific_execution_id': 'product-a-v2-8-4-fresh-confirmation-v1',
        'one_shot': True,
        'operational_attempt': operational_attempt,
        'authorized_ref': authorized_ref,
        'authorization_basis': basis,
        'one_shot_dispatch_policy': dispatch_policy,
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
    if recovery is not None:
        payload['pre_read_recovery'] = recovery
    payload['authorization_receipt_digest'] = hashlib.sha256(
        _canonical(payload)
    ).hexdigest()
    auth_path = (
        auth_root / 'configs/product_a_v2_8_4_sealed_execution_authorization.json'
    )
    auth_path.parent.mkdir(parents=True)
    auth_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    return auth_path, workflow_sha, caller_sha


def _verify(
    auth_path: Path,
    workflow_sha: str,
    caller_sha: str,
    *,
    current_ref: str,
    output_path: Path,
):
    return verify_sealed_authorization(
        authorization_path=auth_path,
        boundary_path=BOUNDARY,
        implementation_root='.',
        authorization_root=auth_path.parents[1],
        implementation_ref='implementation-ref-test',
        reusable_workflow_sha256=workflow_sha,
        caller_workflow_sha256=caller_sha,
        authorization_commit_sha='authorization-commit-test',
        current_sha='authorization-commit-test',
        current_ref=current_ref,
        current_event='workflow_dispatch',
        output_path=output_path,
    )


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
    assert 'python3 src/sdmr/v2_8_4_sealed_authorization.py' in text
    assert 'python3 -m sdmr.v2_8_4_sealed_authorization' not in text
    authorization = text.index(
        'Verify separate one-shot authorization before any sealed source access'
    )
    dependency_install = text.index('Install exact scientific environment')
    environment_gate = text.index(
        'Fail closed on runner-environment drift before any sealed source access'
    )
    first_receipt = text.index(
        'name: product-a-v2-8-4-presealed-receipt-2026082201'
    )
    assert authorization < dependency_install < environment_gate < first_receipt
    assert text.index(
        'Fail closed on this part runner before downloading sealed-source artifacts'
    ) < text.index('name: v283-fresh-part-${{ matrix.seed }}')
    assert text.index(
        'Verify exactly 15 receipt-pinned input artifacts before any download'
    ) < text.index('name: v283-fresh-part-${{ matrix.seed }}')
    assert text.index('--state technical-state/sealed_read_state.json') < text.index(
        'product-a-v2-8-4-sealed-state-${{ matrix.seed }}'
    )
    assert 'if: always()' in text
    assert 'max-parallel: 3' in text
    for seed in ('2026082201', '2026082202', '2026082203'):
        assert seed in text
    assert (
        'aggregate-decision:\n'
        '    if: ${{ github.run_attempt == 1 }}\n'
        '    needs: sealed-part'
    ) in text
    assert 'product-a-v2-8-4-terminal-decision' in text


def test_v284_authorization_script_bootstraps_without_site_packages():
    completed = subprocess.run(
        [sys.executable, '-S', str(AUTH), '--help'],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert '--authorization' in completed.stdout


def test_v284_sealed_runtime_marks_no_retry_before_importing_inherited_sealed_core():
    text = RUNTIME.read_text()
    entered = text.index('state["sealed_read_entered"] = True')
    no_retry = text.index(
        'state["retry_without_new_explicit_contract_allowed"] = False'
    )
    inherited = text.index('from . import v2_8_3_fresh_runtime as v283_runtime')
    assert entered < no_retry < inherited
    assert 'candidate_or_threshold_retuning_after_sealed_read' in text
    assert 'random_seed_change_after_sealed_read' in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text


def test_v284_authorization_verifier_is_truth_blind_and_accepts_initial_contract(
    tmp_path,
):
    auth_text = AUTH.read_text()
    tree = ast.parse(auth_text)
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or '')
    forbidden_imports = (
        'v2_8_3_fresh_runtime',
        'v2_8_3_fresh_aggregate',
        'v2_7_2_fresh_sealed_audit',
        'rasterio',
        'pandas',
    )
    assert not any(
        forbidden in module
        for module in imported_modules
        for forbidden in forbidden_imports
    )
    auth_path, workflow_sha, caller_sha = _authorization(tmp_path)
    gate = _verify(
        auth_path,
        workflow_sha,
        caller_sha,
        current_ref=INITIAL_AUTHORIZED_REF,
        output_path=tmp_path / 'gate.json',
    )
    assert gate['operational_attempt'] == 1
    assert gate['recovery_of_pre_read_run_id'] is None
    assert gate['authorized_ref'] == INITIAL_AUTHORIZED_REF
    assert gate['one_shot_sealed_execution_authorized'] is True
    assert gate['retry_after_sealed_read_entered_allowed'] is False
    assert gate['sealed_ecological_outcomes_read'] is False
    assert gate['scientific_promotion_allowed'] is False
    assert gate['product_b_unblocked'] is False


def test_v284_authorization_verifier_accepts_only_exact_pre_read_recovery(tmp_path):
    auth_path, workflow_sha, caller_sha = _authorization(
        tmp_path, operational_attempt=2
    )
    gate = _verify(
        auth_path,
        workflow_sha,
        caller_sha,
        current_ref=RECOVERY_AUTHORIZED_REF,
        output_path=tmp_path / 'recovery-gate.json',
    )
    assert gate['operational_attempt'] == 2
    assert gate['recovery_of_pre_read_run_id'] == 33309627503
    assert gate['authorized_ref'] == RECOVERY_AUTHORIZED_REF
    assert gate['sealed_ecological_outcomes_read'] is False
    assert gate['scientific_promotion_allowed'] is False
    assert gate['product_b_unblocked'] is False

    payload = json.loads(auth_path.read_text())
    payload['pre_read_recovery']['prior_workflow_run_id'] = 1
    body = dict(payload)
    body.pop('authorization_receipt_digest')
    payload['authorization_receipt_digest'] = hashlib.sha256(
        _canonical(body)
    ).hexdigest()
    auth_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    with pytest.raises(ValueError, match='recovery identity changed'):
        _verify(
            auth_path,
            workflow_sha,
            caller_sha,
            current_ref=RECOVERY_AUTHORIZED_REF,
            output_path=tmp_path / 'wrong-prior-run.json',
        )

    auth_path, workflow_sha, caller_sha = _authorization(
        tmp_path / 'entered', operational_attempt=2
    )
    payload = json.loads(auth_path.read_text())
    payload['pre_read_recovery']['prior_sealed_read_entered'] = True
    body = dict(payload)
    body.pop('authorization_receipt_digest')
    payload['authorization_receipt_digest'] = hashlib.sha256(
        _canonical(body)
    ).hexdigest()
    auth_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    with pytest.raises(ValueError, match='recovery identity changed'):
        _verify(
            auth_path,
            workflow_sha,
            caller_sha,
            current_ref=RECOVERY_AUTHORIZED_REF,
            output_path=tmp_path / 'entered.json',
        )


def test_v284_authorization_verifier_rejects_promotion_commit_or_ref_drift(
    tmp_path,
):
    auth_path, workflow_sha, caller_sha = _authorization(tmp_path)
    payload = json.loads(auth_path.read_text())
    payload['scientific_invariants']['scientific_promotion_allowed'] = True
    body = dict(payload)
    body.pop('authorization_receipt_digest')
    payload['authorization_receipt_digest'] = hashlib.sha256(
        _canonical(body)
    ).hexdigest()
    auth_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    with pytest.raises(ValueError, match='scientific boundary'):
        _verify(
            auth_path,
            workflow_sha,
            caller_sha,
            current_ref=INITIAL_AUTHORIZED_REF,
            output_path=tmp_path / 'bad-gate.json',
        )

    auth_path, workflow_sha, caller_sha = _authorization(tmp_path / 'second')
    with pytest.raises(ValueError, match='exact authorization commit'):
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
            current_ref=INITIAL_AUTHORIZED_REF,
            current_event='workflow_dispatch',
            output_path=tmp_path / 'bad-commit-gate.json',
        )

    auth_path, workflow_sha, caller_sha = _authorization(tmp_path / 'third')
    with pytest.raises(ValueError, match='exact authorized frozen'):
        _verify(
            auth_path,
            workflow_sha,
            caller_sha,
            current_ref='refs/heads/main',
            output_path=tmp_path / 'bad-ref-gate.json',
        )
