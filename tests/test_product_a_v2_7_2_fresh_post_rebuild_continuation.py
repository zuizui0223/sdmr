import json
from pathlib import Path


CONTRACT = Path('configs/product_a_v2_7_2_fresh_post_rebuild_continuation_contract.json')
EXECUTION = Path('configs/product_a_v2_7_2_fresh_post_rebuild_execution_contract.json')
RECEIPT = Path('configs/product_a_v2_7_2_fresh_post_rebuild_source_receipt.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-2-fresh-post-rebuild-continuation.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-7-2-fresh-post-rebuild-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_2_fresh_post_rebuild_pr_trigger.txt')


def test_post_rebuild_contract_pins_one_exact_successful_rebuild_but_execution_stays_closed():
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
    assert r['purpose'] == 'product_a_v2_7_2_fresh_full_shard_rebuild_success_receipt'
    assert r['workflow_run_id'] == 32694094350
    assert r['implementation_sha'] == '820d760d9d852207b521a80aaf5a5ae30451950f'
    assert r['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-full-shard-rebuild-820d760d'
    assert r['workflow_conclusion'] == 'success'
    assert r['required_rebuild_M_shards'] == 216
    assert r['terminal_expected_artifact']['name'] == 'v272-rebuild-M-2026082203-0.30-taxon11-buffer_500km'
    assert r['terminal_expected_artifact']['artifact_id'] == 9527656492
    assert r['terminal_expected_artifact']['digest'] == 'sha256:2082a3d667113a90e9dfc19670cbda2ca5a689f1fc9f9af8c1e9627338a7393b'
    assert r['old_partial_shards_reused'] is False
    assert r['selective_shard_substitution_allowed'] is False
    assert r['sealed_outcome_opened'] is False
    assert r['scientific_decision_produced'] is False
    assert r['scientific_promotion_allowed'] is False
    assert r['product_b_unblocked'] is False


def test_execution_authorization_is_predeclared_and_pins_one_frozen_runtime():
    e = json.loads(EXECUTION.read_text())
    assert e['purpose'] == 'product_a_v2_7_2_fresh_post_rebuild_continuation_execution_authorization'
    assert e['predeclared_before_rebuild_outcome_and_before_rank2_pretruth_or_sealed_audit'] is True
    assert e['implementation_sha'] == 'e37c1b5582a75d7685f55b5cc1d3370ef04ed63c'
    assert e['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-post-rebuild-continuation-e37c1b55'
    assert e['workflow_blob_sha'] == '5993f30e32f64a64828a8ebb3bba8732b7975bfb'
    assert e['continuation_contract_blob_sha'] == '80749a964e399d0a9576468410ea4633cb9b961f'
    assert e['successful_rebuild_run_id'] == 32694094350
    assert e['successful_rebuild_sha'] == '820d760d9d852207b521a80aaf5a5ae30451950f'
    assert e['successful_rebuild_ref'] == 'frozen/product-a-v2-7-2-fresh-full-shard-rebuild-820d760d'
    assert e['requires_exact_216_rebuild_shards'] is True
    assert e['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    assert e['post_outcome_retuning_allowed'] is False
    assert e['scientific_promotion_allowed'] is False
    assert e['product_b_unblocked'] is False
    assert e['execution_allowed'] is True


def test_continuation_graph_preserves_72_6_72_6_1_information_order():
    c = json.loads(CONTRACT.read_text())
    g = c['continuation_graph']
    assert g == {
        'aggregate_workers': 72,
        'exactly_three_M_shards_per_worker': True,
        'shared_partition_and_audit_ledgers_must_be_byte_identical': True,
        'pretruth_parts': 6,
        'final_fit_jobs': 72,
        'sealed_audit_parts': 6,
        'decision_artifacts': 1,
    }
    assert c['information_order'] == [
        'verify_one_exact_successful_216_shard_rebuild',
        'aggregate_exactly_three_rebuild_M_shards_into_each_of_72_workers',
        'freeze_six_pretruth_representatives_and_process_status_tables',
        'fit_and_serialize_72_final_representatives',
        'open_each_parts_sealed_environment_only_after_pretruth_and_all_required_final_models',
        'apply_unchanged_six_part_empirical_decision',
    ]


def test_continuation_workflow_uses_only_rebuild_shards_and_original_presealed_parts():
    text = WORKFLOW.read_text()
    assert 'pattern: v272-rebuild-M-${{ matrix.seed }}-${{ matrix.sealed_fraction }}-taxon${{ matrix.taxon_index }}-*' in text
    assert 'run-id: ${{ needs.preflight.outputs.rebuild_run_id }}' in text
    assert 'run-id: 32637712231' in text
    assert 'name: v272-fresh-part-${{ matrix.seed }}-${{ matrix.sealed_fraction }}' in text
    assert 'pattern: v272-fresh-M-${{ matrix.seed }}' not in text
    assert "len(shard_names)!=216" in text
    assert "set(shard_names)!=expected" in text
    assert "rebuild.get('conclusion')!='success'" in text


def test_frozen_runtime_has_no_execution_identity_self_reference():
    text = WORKFLOW.read_text()
    assert "e.get('execution_allowed')" not in text
    assert 'post-rebuild continuation exact execution identity mismatch' not in text
    assert 'successful rebuild source is not pinned' in text
    assert "rebuild.get('head_sha')!=s['implementation_sha']" in text
    assert "rebuild.get('head_branch')!=s['frozen_ref']" in text


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


def test_generic_launcher_is_one_shot_authorized_but_trigger_is_absent():
    text = LAUNCHER.read_text()
    assert 'product_a_v2_7_2_fresh_post_rebuild_pr_trigger.txt' in text
    assert "auth.get('execution_allowed') is not True" in text
    assert "len(names)!=216" in text
    assert "set(names)!=expected" in text
    assert 'multiple exact post-rebuild continuation runs exist' in text
    assert "payload={'ref':auth['frozen_ref']}" in text
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
