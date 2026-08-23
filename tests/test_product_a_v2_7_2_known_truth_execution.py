import json
from pathlib import Path

CONTRACT = Path('configs/product_a_v2_7_2_known_truth_execution_contract.json')
LAUNCHER = Path('.github/workflows/product-a-v2-7-2-known-truth-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_2_known_truth_pr_trigger.txt')


def test_v272_known_truth_execution_is_exact_one_shot_and_empirical_sealed_blind():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_2_known_truth_execution_contract'
    assert c['execution_identity_frozen_before_known_truth_outcome'] is True
    assert c['implementation_sha']=='9b40393dda3d03943a403d0e7875e2d616b914e7'
    assert c['frozen_ref']=='frozen/product-a-v2-7-2-known-truth-9b40393d'
    assert c['workflow_file']=='product-a-v2-7-2-known-truth-determinism.yml'
    assert c['scientific_contract_path']=='configs/product_a_v2_7_2_deterministic_successor_contract.json'
    assert c['scientific_contract_blob_sha']=='c251b19c21e199894be3c93d8b36e3d2329a9777'
    assert c['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    assert c['expected_replicates']==2
    assert c['expected_cases_per_replicate']==60
    scope=c['scope']
    assert scope['known_truth_only'] is True
    assert scope['new_truth_seeds']==list(range(3101,3111))
    assert scope['empirical_sealed_environment_read_allowed'] is False
    assert scope['current_v2_7_1_fresh_sealed_rows_read_allowed'] is False
    assert scope['post_outcome_threshold_change_allowed'] is False
    assert scope['post_outcome_random_seed_change_allowed'] is False
    assert scope['scientific_promotion_allowed'] is False
    assert scope['product_b_unblocked'] is False


def test_v272_launcher_verifies_frozen_contract_and_trigger_is_absent():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_2_known_truth_pr_trigger.txt' in text
    assert 'scientific_contract_blob_sha' in text
    assert "payload={'ref':c['frozen_ref']}" in text
    assert 'multiple frozen v2.7.2 known-truth runs exist' in text
    assert "'empirical_sealed_environment_read_allowed':False" in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
