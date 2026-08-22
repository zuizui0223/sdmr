import json
from pathlib import Path

CONTRACT=Path('configs/product_a_v2_7_1_fresh_post_shard_continuation_contract.json')
WORKFLOW=Path('.github/workflows/product-a-v2-7-1-fresh-post-shard-continuation.yml')


def test_post_shard_continuation_is_frozen_and_scientifically_unchanged():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_1_fresh_post_shard_continuation_preoutcome_contract'
    assert c['contract_frozen_before_any_recovered_pretruth_or_sealed_outcome'] is True
    assert c['new_scientific_thresholds'] is False
    assert c['primary_source']['run_id']==32552745281
    assert c['primary_source']['terminal_model_pool_timeout_observed'] is True
    assert c['primary_source']['pretruth_artifacts_observed_at_contract_freeze']==0
    assert c['parity_source']['workflow_run_id']==32574696718
    build=c['shard_build_source']
    assert build['implementation_sha']=='e4f407cfd3c9fc76804243f3e26613531474ff5e'
    assert build['required_M_shard_artifact_count']==216
    assert build['sealed_environment_read'] is False
    scope=c['continuation_scope']
    assert scope['consume_one_exact_shard_build_run_only'] is True
    assert scope['consume_primary_worker_outputs'] is False
    assert scope['aggregate_exactly_216_M_shards_into_72_workers'] is True
    assert scope['freeze_exactly_six_pretruth_parts'] is True
    assert scope['fit_exactly_72_final_taxon_part_models_before_sealed_audit'] is True
    assert scope['open_exactly_six_sealed_audits_after_pretruth_and_final_fit'] is True
    assert scope['apply_same_frozen_six_part_decision'] is True
    assert scope['selective_shard_or_worker_repair_allowed'] is False
    inv=c['scientific_invariants']
    assert all(v is False for k,v in inv.items() if k.endswith('_changed'))
    assert inv['post_outcome_candidate_reselection_allowed'] is False
    assert inv['post_outcome_threshold_tuning_allowed'] is False
    assert c['execution_identity']['execution_allowed'] is False
    assert c['decision_artifact']['scientific_promotion_allowed_by_this_workflow'] is False
    assert c['decision_artifact']['product_b_unblocked'] is False


def test_post_shard_workflow_consumes_exact_build_and_preserves_information_order():
    text=WORKFLOW.read_text()
    assert "required_M_shard_artifact_count" in text
    assert "gh run download \"$RUN_ID\"" in text
    assert "--pattern 'v271-fresh-recovery-M-${{ matrix.seed }}-${{ matrix.sealed_fraction }}-taxon${{ matrix.taxon_index }}-*'" in text
    assert 'v2_7_1_fresh_model_pool_shard_aggregate' in text
    assert 'v2_7_1_fresh_pretruth' in text
    assert 'v2_7_1_fresh_final_fit' in text
    assert 'v2_7_1_fresh_sealed_audit' in text
    assert 'v2_7_1_fresh_aggregate' in text
    assert 'needs: aggregate-worker' in text
    assert 'needs: pretruth-freeze' in text
    assert 'needs: final-fit' in text
    assert 'needs: sealed-audit' in text
    assert 'product-a-v2-7-1-fresh-taxon-holdout-confirmation-decision-post-shard-continuation' in text
