import json
from pathlib import Path

CONTRACT=Path('configs/product_a_v2_7_1_fresh_presealed_shard_build_contract.json')
WORKFLOW=Path('.github/workflows/product-a-v2-7-1-fresh-presealed-shard-build.yml')


def test_presealed_shard_build_is_scientifically_inert_and_uniform():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_1_fresh_presealed_shard_recovery_build_preoutcome_contract'
    assert c['contract_frozen_before_any_fresh_pretruth_or_sealed_outcome'] is True
    p=c['primary_source']
    assert p['run_id']==32552745281
    assert p['terminal_model_pool_failure_observed'] is True
    assert p['reference_failed_job_id']==96996726229
    assert p['reference_failed_job_conclusion']=='cancelled'
    assert p['reference_worker_artifact_written'] is False
    assert p['pretruth_artifacts_observed']==0
    assert p['sealed_audit_artifacts_observed']==0
    scope=c['build_scope']
    assert scope['sealed_blind_only'] is True
    assert scope['reuse_primary_worker_outputs'] is False
    assert scope['taxon_part_cells']==72
    assert scope['M_specs_per_cell']==3
    assert scope['total_M_shards']==216
    assert scope['rerun_all_taxon_part_M_shards_uniformly'] is True
    assert scope['selective_repair_allowed'] is False
    assert scope['aggregate_workers_in_this_build'] is False
    assert scope['pretruth_in_this_build'] is False
    assert scope['sealed_audit_in_this_build'] is False
    activation=c['activation_rule']
    assert activation['at_least_one_terminal_primary_model_pool_failure_required'] is True
    assert activation['primary_run_completion_required_for_shard_build'] is False
    assert activation['primary_pretruth_artifacts_must_be_absent'] is True
    assert activation['successful_pinned_parity_required'] is True
    assert c['execution_identity']['execution_allowed'] is False
    assert c['claim_boundary']['scientific_decision_generated'] is False
    assert c['claim_boundary']['scientific_promotion_allowed'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_shard_build_workflow_stops_before_pretruth_and_has_216_uniform_shards():
    text=WORKFLOW.read_text()
    assert 'primary_run_completion_required_for_shard_build' not in text
    assert "j.get('conclusion') in {'failure','cancelled','timed_out'}" in text
    assert "for prefix in ('v271-fresh-pretruth-','v271-fresh-final-','v271-fresh-audit-')" in text
    assert 'max-parallel: 48' in text
    assert 'M: [buffer_150km, buffer_300km, buffer_500km]' in text
    assert 'v271-fresh-recovery-M-' in text
    assert 'n_expected_M_shards' in text
    assert "'sealed_environment_read':False" in text
    assert "'pretruth_performed':False" in text
    assert "'scientific_decision_generated':False" in text
