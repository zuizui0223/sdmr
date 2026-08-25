import json
from pathlib import Path


CONTRACT = Path('configs/product_a_v2_7_2_fresh_post_rebuild_continuation_contract.json')
EXECUTION = Path('configs/product_a_v2_7_2_fresh_post_rebuild_execution_contract.json')
RECEIPT = Path('configs/product_a_v2_7_2_fresh_post_rebuild_source_receipt.json')
RECOVERY = Path('configs/product_a_v2_7_2_fresh_post_rebuild_transport_recovery_contract.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-2-fresh-post-rebuild-continuation.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-7-2-fresh-post-rebuild-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_2_fresh_post_rebuild_pr_trigger.txt')


def test_post_rebuild_contract_pins_one_exact_successful_rebuild_but_runtime_self_gate_stays_closed():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_post_full_shard_rebuild_continuation_contract'
    assert c['predeclared_before_full_rebuild_outcome_and_before_any_rank2_pretruth_or_sealed_outcome'] is True
    src = c['required_rebuild_source']
    assert src['workflow_run_id'] == 32694094350
    assert src['implementation_sha'] == '820d760d9d852207b521a80aaf5a5ae30451950f'
    assert src['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-full-shard-rebuild-820d760d'
    assert src['require_workflow_conclusion_success'] is True
    assert src['require_exactly_216_rebuild_M_shards'] is True
    assert src['require_all_shards_from_one_exact_rebuild_run'] is True
    assert src['artifact_name_prefix'] == 'v272-rebuild-M-'
    assert src['old_partial_shards_from_run_32637712231_allowed'] is False
    assert src['selective_shard_substitution_allowed'] is False
    assert c['execution_identity']['execution_allowed'] is False


def test_success_receipt_records_rebuild_without_crossing_scientific_boundary():
    r = json.loads(RECEIPT.read_text())
    assert r['workflow_run_id'] == 32694094350
    assert r['workflow_conclusion'] == 'success'
    assert r['required_rebuild_M_shards'] == 216
    assert r['old_partial_shards_reused'] is False
    assert r['sealed_outcome_opened'] is False
    assert r['scientific_decision_produced'] is False
    assert r['scientific_promotion_allowed'] is False
    assert r['product_b_unblocked'] is False


def test_failed_continuation_is_transport_only_and_recovery_rebuilds_all_72_workers():
    r = json.loads(RECOVERY.read_text())
    assert r['purpose'] == 'product_a_v2_7_2_fresh_post_rebuild_paginated_artifact_transport_recovery'
    assert r['declared_before_any_rank2_pretruth_or_sealed_audit'] is True
    failed = r['failed_continuation']
    assert failed['workflow_run_id'] == 32796308769
    assert failed['implementation_sha'] == 'e37c1b5582a75d7685f55b5cc1d3370ef04ed63c'
    assert failed['preflight_success'] is True
    assert failed['exact_216_rebuild_shards_verified'] is True
    assert failed['failure_stage'] == 'aggregate_worker_artifact_transport'
    assert failed['pretruth_started'] is False
    assert failed['sealed_audit_started'] is False
    assert failed['scientific_decision_produced'] is False
    diagnosis = r['diagnosis']
    assert diagnosis['rebuild_artifacts_missing'] is False
    assert diagnosis['actions_download_artifact_remote_listing_count_observed'] == 200
    assert diagnosis['rebuild_shard_count_verified_by_paginated_api'] == 216
    recovery = r['recovery']
    assert recovery['source_rebuild_run_id'] == 32694094350
    assert recovery['required_rebuild_shards'] == 216
    assert recovery['rerun_all_72_aggregate_workers'] is True
    assert recovery['reuse_any_worker_from_run_32796308769'] is False
    assert recovery['only_implementation_change'] == 'rebuild-shard artifact transport'
    assert recovery['scientific_runtime_modules_changed'] is False
    assert r['information_boundary']['sealed_outcome_seen_before_recovery_declaration'] is False
    assert r['execution_identity']['execution_allowed'] is False


def test_transport_successor_authorization_pins_exact_frozen_identity():
    e = json.loads(EXECUTION.read_text())
    assert e['purpose'] == 'product_a_v2_7_2_fresh_post_rebuild_continuation_execution_authorization'
    assert e['predeclared_before_rebuild_outcome_and_before_rank2_pretruth_or_sealed_audit'] is True
    assert e['technical_successor_authorized_after_transport_failure_before_rank2_pretruth_or_sealed_audit'] is True
    assert e['implementation_sha'] == '811427392f5d3c4fd4c70385f3479605fdce1dc1'
    assert e['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-post-rebuild-transport-81142739'
    assert e['workflow_blob_sha'] == 'b1a6052832932302aa58a1cb6f056da7b5d7fc78'
    assert e['continuation_contract_blob_sha'] == '80749a964e399d0a9576468410ea4633cb9b961f'
    assert e['transport_recovery_contract_blob_sha'] == 'c87c0e31e5dc01a6fcdf30e4d58f13ae26b97769'
    assert e['successful_rebuild_run_id'] == 32694094350
    assert e['successful_rebuild_sha'] == '820d760d9d852207b521a80aaf5a5ae30451950f'
    assert e['supersedes_continuation_run_id'] == 32796308769
    assert e['reuse_any_worker_from_superseded_run'] is False
    assert e['rerun_all_72_aggregate_workers'] is True
    assert e['requires_exact_216_rebuild_shards'] is True
    assert e['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    assert e['post_outcome_retuning_allowed'] is False
    assert e['scientific_promotion_allowed'] is False
    assert e['product_b_unblocked'] is False
    assert e['execution_allowed'] is True


def test_continuation_graph_preserves_72_6_72_6_1_information_order():
    c = json.loads(CONTRACT.read_text())
    assert c['continuation_graph'] == {
        'aggregate_workers': 72,
        'exactly_three_M_shards_per_worker': True,
        'shared_partition_and_audit_ledgers_must_be_byte_identical': True,
        'pretruth_parts': 6,
        'final_fit_jobs': 72,
        'sealed_audit_parts': 6,
        'decision_artifacts': 1,
    }


def test_worker_transport_paginates_all_rebuild_artifacts_and_downloads_exact_three_by_id():
    text = WORKFLOW.read_text()
    assert "artifacts?per_page=100&page={page}" in text
    assert "actions/artifacts/{int(artifact['id'])}/zip" in text
    assert "if len(matched)!=3 or len(set(names))!=3 or set(names)!=set(expected)" in text
    assert "for M in ('buffer_150km','buffer_300km','buffer_500km')" in text
    assert 'pattern: v272-rebuild-M-${{ matrix.seed }}-${{ matrix.sealed_fraction }}-taxon${{ matrix.taxon_index }}-*' not in text
    assert 'name: Download exact three rebuilt M shards through paginated API' in text
    assert 'run-id: 32637712231' in text
    assert 'name: v272-fresh-part-${{ matrix.seed }}-${{ matrix.sealed_fraction }}' in text
    assert 'pattern: v272-fresh-M-${{ matrix.seed }}' not in text
    assert "len(shard_names)!=216" in text
    assert "set(shard_names)!=expected" in text


def test_continuation_reuses_v272_scientific_runtime_without_new_selection_logic():
    text = WORKFLOW.read_text()
    for module in (
        'sdmr.v2_7_2_fresh_model_pool_shard_aggregate',
        'sdmr.v2_7_2_fresh_pretruth',
        'sdmr.v2_7_2_fresh_final_fit',
        'sdmr.v2_7_2_fresh_sealed_audit',
        'sdmr.v2_7_2_fresh_aggregate',
    ):
        assert module in text
    assert "assert c['deterministic_successor'] is True" in text
    assert "assert c['model_random_state']==0" in text
    assert "assert c['candidate_or_threshold_retuning_after_sealed_read'] is False" in text
    assert "assert c['random_seed_change_after_sealed_read'] is False" in text


def test_sealed_audit_cannot_start_before_pretruth_and_all_final_fits():
    text = WORKFLOW.read_text()
    assert 'pretruth:\n    needs: aggregate-worker' in text
    assert 'final-fit:\n    needs: pretruth' in text
    assert 'sealed-audit:\n    needs: final-fit' in text
    assert 'aggregate:\n    needs: sealed-audit' in text


def test_generic_launcher_verifies_transport_recovery_and_remains_one_shot():
    text = LAUNCHER.read_text()
    assert "auth.get('execution_allowed') is not True" in text
    assert "auth.get('rerun_all_72_aggregate_workers') is not True" in text
    assert "recovery.get('purpose')!='product_a_v2_7_2_fresh_post_rebuild_paginated_artifact_transport_recovery'" in text
    assert "verify_blob(auth['transport_recovery_contract_path'],auth['transport_recovery_contract_blob_sha'])" in text
    assert "len(names)!=216" in text
    assert "set(names)!=expected" in text
    assert 'multiple exact post-rebuild continuation runs exist' in text
    assert "payload={'ref':auth['frozen_ref']}" in text
    assert "'reuse_any_worker_from_superseded_run':False" in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()


def test_decision_does_not_promote_product_a_or_unblock_product_b():
    c = json.loads(CONTRACT.read_text())
    assert c['claim_boundary']['continuation_decision_itself_promotes_product_a'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False
    text = WORKFLOW.read_text()
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert "'post_outcome_retuning_allowed':False" in text
    assert 'name: product-a-v2-7-2-fresh-rank2-confirmation-decision' in text
