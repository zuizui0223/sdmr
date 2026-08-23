import json
from pathlib import Path

EXECUTION=Path('configs/product_a_v2_7_2_post_shard_continuation_execution.json')
PROMOTION=Path('configs/product_a_v2_7_2_fresh_promotion_contract.json')
WORKFLOW=Path('.github/workflows/product-a-v2-7-2-post-shard-continuation.yml')
LAUNCHER=Path('.github/workflows/product-a-v2-7-2-post-shard-continuation-pr-launch.yml')
TRIGGER=Path('configs/product_a_v2_7_2_post_shard_continuation_pr_trigger.txt')


def test_continuation_gate_is_closed_until_exact_build_is_pinned():
    c=json.loads(EXECUTION.read_text())
    assert c['execution_allowed'] is False
    assert c['implementation_sha'] is None
    assert c['frozen_ref'] is None
    assert c['random_state']==271
    assert c['shard_build_run_id'] is None
    assert c['shard_build_receipt_artifact_id'] is None
    assert c['shard_build_receipt_artifact_digest'] is None
    assert c['required_M_shard_artifact_prefix']=='v272-fresh-M-'
    assert c['required_M_shard_artifact_count']==216
    assert c['promotion_source_fields_pinned_before_dispatch'] is False
    assert c['selective_worker_repair_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_promotion_rule_is_frozen_before_sealed_outcome_without_new_thresholds():
    p=json.loads(PROMOTION.read_text())
    assert p['contract_frozen_before_v2_7_2_fresh_sealed_outcome'] is True
    assert p['new_postoutcome_scientific_thresholds'] is False
    assert p['deterministic_execution_repair']['random_state']==271
    assert p['deterministic_execution_repair']['selected_from_scientific_outcome'] is False
    source=p['fresh_taxon_holdout_source']
    assert source['repository_execution_identity_must_be_frozen_before_dispatch'] is True
    assert source['runtime_source_identity_receipt_must_be_created_before_sealed_audit'] is True
    assert source['runtime_source_identity_may_not_depend_on_scientific_metric_or_decision_value'] is True
    assert source['decision_artifact_name']=='product-a-v2-7-2-fresh-taxon-holdout-confirmation-decision'
    assert p['failure_semantics']['random_state_reselection_after_outcome_forbidden'] is True
    assert p['claim_boundary']['automatic_product_b_unblock'] is False


def test_continuation_preserves_full_information_order_and_seed():
    text=WORKFLOW.read_text()
    assert 'v272-fresh-M-' in text
    assert 'n_M_shards' in text
    assert 'v272-fresh-worker-' in text
    assert 'v272-fresh-pretruth-' in text
    assert 'v272-fresh-final-' in text
    assert 'v272-fresh-audit-' in text
    assert 'promotion-source-freeze:' in text
    assert 'needs: [final-fit, promotion-source-freeze]' in text
    assert "SDMR_LOGISTIC_RANDOM_STATE: '271'" in text
    assert 'python -m sdmr.v2_7_1_fresh_pretruth' in text
    assert 'python -m sdmr.v2_7_1_fresh_final_fit' in text
    assert 'python -m sdmr.v2_7_1_fresh_sealed_audit' in text
    assert 'python -m sdmr.v2_7_1_fresh_aggregate' in text
    assert "'source_selection_used_scientific_metric_or_decision_value':False" in text
    assert 'product-a-v2-7-2-fresh-taxon-holdout-confirmation-decision' in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text


def test_continuation_launcher_is_one_shot_and_trigger_absent():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_2_post_shard_continuation_pr_trigger.txt' in text
    assert 'multiple exact deterministic continuation runs exist' in text
    assert "'shard_build_receipt_artifact_digest':c['shard_build_receipt_artifact_digest']" in text
    assert 'promotion source identity was not frozen before dispatch' in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
