import json
from pathlib import Path

INVARIANTS=Path('configs/product_a_v2_7_1_fresh_presealed_shard_build_v2_invariants.json')
EXECUTION=Path('configs/product_a_v2_7_1_fresh_presealed_shard_build_v2_execution.json')
WORKFLOW=Path('.github/workflows/product-a-v2-7-1-fresh-presealed-shard-build-v2.yml')
LAUNCHER=Path('.github/workflows/product-a-v2-7-1-fresh-presealed-shard-build-v2-pr-launch.yml')
TRIGGER=Path('configs/product_a_v2_7_1_fresh_presealed_shard_build_v2_pr_trigger.txt')


def test_v2_invariants_pin_old_scientific_source_and_current_parity_run_preoutcome():
    c=json.loads(INVARIANTS.read_text())
    assert c['frozen_before_parity_v2_outcome_opened'] is True
    s=c['scientific_source']
    assert s['implementation_sha']=='e4f407cfd3c9fc76804243f3e26613531474ff5e'
    assert s['execution_uses_exact_source_checkout'] is True
    assert s['wrapper_may_not_modify_scientific_source'] is True
    p=c['parity_source']
    assert p['workflow_run_id']==32614371301
    assert p['implementation_sha']=='3e578e14f2949662b64206ee959ee571e52cced2'
    assert p['floating_relative_tolerance']==0.0005
    assert p['floating_absolute_tolerance']==0.0005
    assert c['build_scope']['total_M_shards']==216
    assert c['build_scope']['selective_repair_allowed'] is False
    assert c['claim_boundary']['scientific_decision_generated'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_v2_execution_gate_is_closed_until_parity_artifact_is_pinned():
    c=json.loads(EXECUTION.read_text())
    assert c['execution_allowed'] is False
    assert c['wrapper_sha'] is None
    assert c['wrapper_ref'] is None
    assert c['parity_run_id']==32614371301
    assert c['parity_artifact_id'] is None
    assert c['parity_artifact_digest'] is None
    assert c['parity_passed'] is None
    assert c['one_shot_required'] is True
    assert c['scientific_promotion_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_v2_workflow_runs_science_from_original_exact_commit():
    text=WORKFLOW.read_text()
    assert 'ref: e4f407cfd3c9fc76804243f3e26613531474ff5e' in text
    assert 'test "$(git rev-parse HEAD)" = "e4f407cfd3c9fc76804243f3e26613531474ff5e"' in text
    assert 'total_M_shards' in text
    assert 'gh run download 32614371301' in text
    assert "r.get('fit_code_changed_for_parity') is not False" in text
    assert 'v271-fresh-recovery-v2-M-' in text
    assert 'scientific_implementation_sha' in text


def test_v2_launcher_is_one_shot_and_trigger_absent_from_scaffold():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_1_fresh_presealed_shard_build_v2_pr_trigger.txt' in text
    assert 'multiple exact shard-build v2 runs exist' in text
    assert "'expected_wrapper_sha':c['wrapper_sha']" in text
    assert "'parity_artifact_digest':c['parity_artifact_digest']" in text
    assert "'sealed_environment_read_allowed':False" in text
    assert "'scientific_decision_generated':False" in text
    assert not TRIGGER.exists()
