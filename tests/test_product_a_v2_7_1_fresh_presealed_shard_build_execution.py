import json
from pathlib import Path

CONTRACT=Path('configs/product_a_v2_7_1_fresh_presealed_shard_build_contract.json')
LAUNCHER=Path('.github/workflows/product-a-v2-7-1-fresh-presealed-shard-build-pr-launch.yml')
TRIGGER=Path('configs/product_a_v2_7_1_fresh_presealed_shard_build_pr_trigger.txt')


def test_exact_shard_build_identity_is_pinned_but_closed_pending_parity():
    c=json.loads(CONTRACT.read_text())
    e=c['execution_identity']
    assert e['implementation_sha']=='e4f407cfd3c9fc76804243f3e26613531474ff5e'
    assert e['frozen_ref']=='frozen/product-a-v2-7-1-fresh-presealed-shard-build-e4f407cf'
    assert e['workflow_file']=='product-a-v2-7-1-fresh-presealed-shard-build.yml'
    assert e['execution_allowed'] is False
    p=c['parity_source']
    assert p['workflow_run_id']==32574696718
    assert p['artifact_id'] is None
    assert p['artifact_digest'] is None
    assert p['parity_passed'] is None
    assert c['build_scope']['sealed_blind_only'] is True
    assert c['build_scope']['total_M_shards']==216
    assert c['claim_boundary']['scientific_decision_generated'] is False


def test_shard_build_launcher_is_one_shot_and_not_triggered_by_gate_pr():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_1_fresh_presealed_shard_build_pr_trigger.txt' in text
    assert 'multiple exact shard-build runs exist' in text
    assert "payload={'ref':e['frozen_ref']}" in text
    assert "'sealed_environment_read_allowed':False" in text
    assert "'scientific_decision_generated':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
