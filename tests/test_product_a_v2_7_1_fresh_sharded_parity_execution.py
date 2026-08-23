import json
from pathlib import Path

CONTRACT = Path('configs/product_a_v2_7_1_fresh_sharded_parity_execution_contract.json')
LAUNCHER = Path('.github/workflows/product-a-v2-7-1-fresh-sharded-parity-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_1_fresh_sharded_parity_pr_trigger.txt')


def test_sharded_parity_execution_is_exact_and_sealed_blind():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_1_fresh_sharded_parity_execution_contract'
    assert c['execution_identity_frozen_before_parity_outcome'] is True
    assert c['implementation_sha']=='3e578e14f2949662b64206ee959ee571e52cced2'
    assert c['frozen_ref']=='frozen/product-a-v2-7-1-fresh-sharded-parity-v2-3e578e14'
    assert c['workflow_file']=='product-a-v2-7-1-fresh-sharded-parity.yml'
    assert c['parity_definition_contract']=='configs/product_a_v2_7_1_fresh_sharded_parity_v2_contract.json'
    assert c['supersedes_failed_parity_run_id']==32574696718
    assert c['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    ref=c['primary_reference']
    assert ref['run_id']==32552745281
    assert ref['worker_artifact_id']==9473775642
    assert ref['worker_artifact_digest']=='sha256:95b6d0ed1dc101c3633d45cbf0770f7f3498c0641541521a3c198c55a6052184'
    scope=c['scope']
    assert scope['parity_only'] is True
    assert scope['all_three_M_recomputed'] is True
    assert scope['sealed_environment_read_allowed'] is False
    assert scope['scientific_metric_outcome_used_for_dispatch'] is False
    assert scope['scientific_threshold_change_allowed'] is False
    assert scope['candidate_reselection_allowed'] is False
    assert scope['fit_code_change_allowed'] is False
    assert scope['scientific_promotion_allowed'] is False
    assert scope['product_b_unblocked'] is False


def test_parity_launcher_is_one_shot_and_trigger_is_not_in_gate_pr():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_1_fresh_sharded_parity_pr_trigger.txt' in text
    assert 'multiple frozen parity runs exist' in text
    assert "payload={'ref':c['frozen_ref']}" in text
    assert "sealed_environment_read_allowed':False" in text
    assert "scientific_promotion_allowed':False" in text
    assert "product_b_unblocked':False" in text
    assert not TRIGGER.exists()
