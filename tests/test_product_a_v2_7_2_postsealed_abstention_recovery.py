import json
from pathlib import Path

import pandas as pd

import sdmr.v2_7_2_fresh_sealed_audit_recovery as recovery_module


RECOVERY_CONTRACT = Path('configs/product_a_v2_7_2_postsealed_abstention_recovery_contract.json')
EXTERNAL_RECOVERY = Path('configs/product_a_v2_7_2_postsealed_external_authorization_recovery_contract.json')
EXECUTION = Path('configs/product_a_v2_7_2_postsealed_abstention_recovery_execution.json')
FINAL_RECEIPT = Path('configs/product_a_v2_7_2_fresh_rank2_confirmation_final_receipt.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-2-postsealed-abstention-recovery.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-7-2-postsealed-recovery-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_2_postsealed_recovery_pr_trigger.txt')


def _write_common(tmp_path, *, available, authorized, rng_state=None, numpy_seed=None):
    part = tmp_path / 'part'
    pretruth = tmp_path / 'pretruth'
    finals = tmp_path / 'finals'
    part.mkdir(); pretruth.mkdir(); finals.mkdir()
    (part / 'contract.json').write_text(json.dumps({
        'purpose': 'product_a_v2_7_2_fresh_part_model_pool_materialization',
        'seed': 2026082201,
        'sealed_fraction': 0.30,
        'sealed_occurrence_raster_values_extracted': False,
    }))
    (pretruth / 'contract.json').write_text(json.dumps({
        'purpose': 'product_a_v2_7_2_fresh_part_pretruth_freeze',
        'deterministic_successor': True,
        'available': available,
        'sealed_audit_authorized': authorized,
        'model_random_state': rng_state,
        'selection_process_numpy_seed': numpy_seed,
        'unavailable_reason': 'pretruth_structural_abstention' if not available else None,
    }))
    pd.DataFrame([{
        'taxon': 'example',
        'process_domain': 'base',
        'status': 'abstain' if not available else 'supported',
    }]).to_csv(pretruth / 'pretruth_process_status.csv', index=False)
    return part, pretruth, finals


def test_unavailable_pretruth_propagates_without_rng_guard_or_sealed_read(tmp_path, monkeypatch):
    part, pretruth, finals = _write_common(
        tmp_path, available=False, authorized=False, rng_state=None, numpy_seed=None
    )
    delegated = {'called': False}

    def forbidden_delegate(**kwargs):
        delegated['called'] = True
        raise AssertionError('unavailable pretruth must not enter scientific sealed-audit path')

    monkeypatch.setattr(recovery_module, 'run_fresh_sealed_audit', forbidden_delegate)
    result = recovery_module.run_recovered_sealed_audit(
        contract_path='unused.json',
        part_dir=part,
        pretruth_dir=pretruth,
        final_fit_root=finals,
        manifest_path='unused.csv',
        output_dir=tmp_path / 'audit',
    )
    assert delegated['called'] is False
    assert result['available'] is False
    assert result['sealed_occurrence_environment_read'] is False
    assert result['structural_or_audit_abstention_propagated_as_unavailable'] is True
    assert result['candidate_or_threshold_retuning_after_sealed_read'] is False
    assert result['random_seed_change_after_sealed_read'] is False


def test_available_authorized_pretruth_delegates_to_original_audit_unchanged(tmp_path, monkeypatch):
    part, pretruth, finals = _write_common(
        tmp_path, available=True, authorized=True, rng_state=0, numpy_seed=0
    )
    calls = []
    sentinel = {'purpose': 'delegated-original-audit'}

    def delegate(**kwargs):
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(recovery_module, 'run_fresh_sealed_audit', delegate)
    result = recovery_module.run_recovered_sealed_audit(
        contract_path='contract.json',
        part_dir=part,
        pretruth_dir=pretruth,
        final_fit_root=finals,
        manifest_path='manifest.csv',
        output_dir=tmp_path / 'audit',
    )
    assert result is sentinel
    assert len(calls) == 1
    assert calls[0]['contract_path'] == 'contract.json'
    assert calls[0]['final_fit_root'] == finals
    assert calls[0]['manifest_path'] == 'manifest.csv'


def test_recovery_contract_freezes_uniform_six_part_nonretuned_recovery():
    c = json.loads(RECOVERY_CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_postsealed_abstention_control_flow_recovery'
    assert c['failed_continuation_run_id'] == 32807401949
    assert c['diagnosis']['failed_audit_jobs'] == [97686120488, 97686120494]
    assert c['diagnosis']['successful_audit_result_contents_used_to_design_repair'] is False
    assert c['repair']['rerun_all_6_audit_parts_uniformly'] is True
    assert c['repair']['reuse_any_old_sealed_audit_as_recovered_decision_input'] is False
    assert c['repair']['available_or_authorized_scientific_audit_function_changed'] is False
    assert c['repair']['unavailable_path_reads_sealed_environment'] is False
    assert c['scientific_invariants']['post_outcome_retuning_allowed'] is False
    assert c['claim_boundary']['recovery_decision_itself_promotes_product_a'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_external_authorization_recovery_is_predeclared_and_pre_audit():
    c = json.loads(EXTERNAL_RECOVERY.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_postsealed_external_authorization_self_reference_recovery'
    assert c['failed_recovery_run_id'] == 32825270429
    assert c['failed_preflight_job_id'] == 97731752335
    assert c['failure_stage'] == 'preflight_before_any_audit'
    assert c['diagnosis']['audit_jobs_started'] is False
    assert c['diagnosis']['aggregate_started'] is False
    assert c['diagnosis']['recovery_artifacts_created'] == 0
    assert c['diagnosis']['sealed_result_contents_used_to_design_repair'] is False
    assert c['repair']['frozen_runtime_reads_local_execution_authorization'] is False
    assert c['repair']['authorization_is_external_to_frozen_runtime'] is True
    assert c['repair']['authorization_commit_and_blob_are_dispatch_inputs'] is True
    assert c['repair']['rerun_all_6_audit_parts_uniformly'] is True
    assert c['repair']['reuse_any_old_sealed_audit_as_recovered_decision_input'] is False
    assert c['repair']['available_or_authorized_scientific_audit_function_changed'] is False
    assert c['repair']['wrapper_changed'] is False
    assert c['repair']['original_sealed_audit_module_changed'] is False
    assert c['scientific_invariants']['post_outcome_retuning_allowed'] is False


def test_recovery_execution_authorization_is_consumed_and_closed():
    e = json.loads(EXECUTION.read_text())
    assert e['implementation_sha'] == 'e20ab07dd84f0908da188567498c09a5f83e711a'
    assert e['frozen_ref'] == 'frozen/product-a-v2-7-2-postsealed-external-auth-e20ab07d'
    assert e['workflow_blob_sha'] == '43b389476b86528277e737d515ed079e4c23e1fb'
    assert e['contract_blob_sha'] == 'ee00a52cd120aafdbfcc2cde6fc4b3271bffa5ff'
    assert e['wrapper_blob_sha'] == 'fa281aac150603fd231f00ae5a0d494e47a8b23e'
    assert e['original_audit_blob_sha'] == '9da77e578cd9d5f523340c19eb2df844600f588a'
    assert e['external_recovery_contract_blob_sha'] == '714ae063ee07239d0e2575972aaa77268e768f7f'
    assert e['source_run_id'] == 32807401949
    assert e['rerun_all_6_audits'] is True
    assert e['reuse_old_audits_for_decision'] is False
    assert e['post_outcome_retuning_allowed'] is False
    assert e['scientific_promotion_allowed'] is False
    assert e['product_b_unblocked'] is False
    assert e['one_shot'] is True
    assert e['consumed_by_run_id'] == 32827603784
    assert e['consumed_decision'] == 'empirical_confirmation_unavailable'
    assert e['consumed_decision_artifact_id'] == 9559443057
    assert e['execution_allowed'] is False


def test_final_receipt_preserves_unavailable_not_negative_boundary():
    r = json.loads(FINAL_RECEIPT.read_text())
    assert r['purpose'] == 'product_a_v2_7_2_fresh_rank2_confirmation_final_receipt'
    assert r['workflow_run_id'] == 32827603784
    assert r['decision'] == 'empirical_confirmation_unavailable'
    assert r['decision_interpretation'] == 'fresh empirical confirmation incomplete; not negative empirical evidence'
    assert r['n_parts'] == 6
    assert r['n_available_parts'] == 4
    assert r['n_unavailable_before_sealed_read'] == 2
    assert r['n_unavailable_after_sealed_read'] == 0
    assert r['n_ecologically_nondominated_parts'] == 4
    assert r['n_strict_ecological_improvement_parts'] == 1
    assert r['six_audits_regenerated_uniformly'] is True
    assert r['old_audits_used_for_decision'] is False
    assert r['post_outcome_retuning_performed'] is False
    assert r['scientific_promotion_allowed'] is False
    assert r['product_b_unblocked'] is False
    assert r['retained_claim'] == 'known_truth_support_only_with_incomplete_fresh_empirical_evidence'
    assert r['decision_artifact']['id'] == 9559443057
    assert r['decision_artifact']['digest'] == 'sha256:23fb5d30bc49dc39f3acc9f77ce40da5f68c993c12830ce3bd904cf26bf62f7e'


def test_recovery_workflow_uses_external_authorization_and_reuses_frozen_scientific_inputs():
    text = WORKFLOW.read_text()
    assert 'authorization_commit_sha:' in text
    assert 'authorization_blob_sha:' in text
    assert 'expected_runtime_sha:' in text
    assert 'expected_frozen_ref:' in text
    assert "auth=json.load(open('configs/product_a_v2_7_2_postsealed_abstention_recovery_execution.json'))" not in text
    assert "auth_meta=get(f'{api}/contents/{auth_path}?ref={auth_ref}')" in text
    assert "base64.b64decode(auth_meta['content']).decode()" in text
    assert "auth.get('execution_allowed') is not True" in text
    assert "auth.get('implementation_sha') != os.environ['GITHUB_SHA']" in text
    assert 'run-id: 32637712231' in text
    assert 'run-id: 32807401949' in text
    assert 'sdmr.v2_7_2_fresh_sealed_audit_recovery' in text
    assert 'sdmr.v2_7_2_fresh_aggregate' in text
    assert 'v272-postsealed-recovery-audit-*' in text
    assert 'product-a-v2-7-2-fresh-rank2-confirmation-decision-recovery' in text


def test_recovery_launcher_remains_external_and_one_shot():
    text = LAUNCHER.read_text()
    assert "authorization_commit_sha=str(event['pull_request']['base']['sha'])" in text
    assert "if json.loads(decoded) != auth:" in text
    assert "verify_blob('src/sdmr/v2_7_2_fresh_sealed_audit_recovery.py',auth['wrapper_blob_sha'])" in text
    assert "verify_blob('src/sdmr/v2_7_2_fresh_sealed_audit.py',auth['original_audit_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_7_2_postsealed_external_authorization_recovery_contract.json',auth['external_recovery_contract_blob_sha'])" in text
    assert "'authorization_commit_sha':authorization_commit_sha" in text
    assert "'authorization_blob_sha':authorization_blob_sha" in text
    assert 'multiple exact recovery runs exist' in text
    assert "'reuse_old_audits_for_decision':False" in text
    assert "'post_outcome_retuning_allowed':False" in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
