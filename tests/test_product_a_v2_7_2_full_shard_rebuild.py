import json
from pathlib import Path

REBUILD = Path('configs/product_a_v2_7_2_fresh_full_shard_rebuild_contract.json')
CONT = Path('configs/product_a_v2_7_2_fresh_post_rebuild_continuation_contract.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-2-fresh-full-shard-rebuild.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-7-2-fresh-full-shard-rebuild-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_2_fresh_full_shard_rebuild_pr_trigger.txt')


def test_full_rebuild_uses_only_six_exact_presealed_parts_and_reruns_all_216():
    c = json.loads(REBUILD.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_full_216_shard_rebuild_contract'
    assert c['predeclared_before_any_rank2_pretruth_or_sealed_outcome'] is True
    assert c['scientific_parent']['implementation_sha'] == '5073d6c701f36fdae0bf5df9a1d42f1863d994a8'
    old = c['superseded_full_run']
    assert old['workflow_run_id'] == 32637712231
    assert old['all_6_materializations_success'] is True
    assert old['pretruth_started'] is False
    assert old['sealed_audit_started'] is False
    assert old['scientific_decision_produced'] is False
    assert old['reference_timeout_job_id'] == 97205950056
    assert old['configured_timeout_minutes'] == 240
    parts = c['reusable_presealed_materializations']['parts']
    assert len(parts) == 6
    assert len({p['artifact_id'] for p in parts}) == 6
    assert all(p['artifact_digest'].startswith('sha256:') for p in parts)
    r = c['uniform_rebuild']
    assert r['taxon_part_cells'] == 72
    assert r['M_per_cell'] == 3
    assert r['required_shards'] == 216
    assert r['all_216_recomputed'] is True
    assert r['partial_shards_from_run_32637712231_reused'] is False
    assert r['selective_retry_or_substitution_allowed'] is False
    assert r['previous_timeout_minutes'] == 240
    assert r['rebuild_timeout_minutes'] == 360
    assert r['only_execution_change'] == 'per-M-shard wall-clock budget 240_to_360_minutes'
    assert r['model_or_scientific_rule_changed'] is False
    execution = c['execution_identity']
    assert execution['implementation_sha'] == '820d760d9d852207b521a80aaf5a5ae30451950f'
    assert execution['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-full-shard-rebuild-820d760d'
    assert execution['workflow_file'] == 'product-a-v2-7-2-fresh-full-shard-rebuild.yml'
    assert execution['workflow_blob_sha'] == '2cfa74be267e2ea60c6a4d1f60aa72c02978af5d'
    assert execution['runtime_contract_blob_sha'] == 'b61b087fd0887c52239ee6f60ffabfd0cd1c4176'
    assert execution['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    assert execution['execution_allowed'] is True


def test_rebuild_workflow_is_shard_only_and_uses_360_min_uniform_budget():
    text = WORKFLOW.read_text()
    assert 'timeout-minutes: 360' in text
    assert 'max-parallel: 48' in text
    assert "seed: [2026082201, 2026082202, 2026082203]" in text
    assert "sealed_fraction: ['0.20', '0.30']" in text
    assert 'taxon_index: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]' in text
    assert 'M: [buffer_150km, buffer_300km, buffer_500km]' in text
    assert 'run-id: 32637712231' in text
    assert 'v272-rebuild-M-' in text
    assert 'v272-fresh-M-' not in text
    assert 'v2_7_2_fresh_model_pool_shard' in text
    assert 'v2_7_2_fresh_pretruth' not in text
    assert 'v2_7_2_fresh_final_fit' not in text
    assert 'v2_7_2_fresh_sealed_audit' not in text
    assert 'v2_7_2_fresh_aggregate' not in text


def test_post_rebuild_continuation_pins_successful_build_but_execution_remains_closed():
    c = json.loads(CONT.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_post_full_shard_rebuild_continuation_contract'
    assert c['predeclared_before_full_rebuild_outcome_and_before_any_rank2_pretruth_or_sealed_outcome'] is True
    source = c['required_rebuild_source']
    assert source['workflow_run_id'] == 32694094350
    assert source['implementation_sha'] == '820d760d9d852207b521a80aaf5a5ae30451950f'
    assert source['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-full-shard-rebuild-820d760d'
    assert source['require_workflow_conclusion_success'] is True
    assert source['require_exactly_216_rebuild_M_shards'] is True
    assert source['require_all_shards_from_one_exact_rebuild_run'] is True
    assert source['old_partial_shards_from_run_32637712231_allowed'] is False
    assert source['selective_shard_substitution_allowed'] is False
    graph = c['continuation_graph']
    assert graph['aggregate_workers'] == 72
    assert graph['exactly_three_M_shards_per_worker'] is True
    assert graph['pretruth_parts'] == 6
    assert graph['final_fit_jobs'] == 72
    assert graph['sealed_audit_parts'] == 6
    assert c['scientific_invariants']['weighted_super_score_allowed'] is False
    assert c['scientific_invariants']['post_outcome_threshold_tuning_allowed'] is False
    assert c['claim_boundary']['continuation_decision_itself_promotes_product_a'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False
    assert c['execution_identity']['execution_allowed'] is False


def test_full_rebuild_launcher_is_one_shot_and_trigger_is_not_committed():
    text = LAUNCHER.read_text()
    assert 'product_a_v2_7_2_fresh_full_shard_rebuild_pr_trigger.txt' in text
    assert 'multiple exact full-shard rebuild runs exist' in text
    assert "payload={'ref':e['frozen_ref']}" in text
    assert "'required_shards':216" in text
    assert "'sealed_environment_read_allowed':False" in text
    assert "'scientific_decision_generated':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
