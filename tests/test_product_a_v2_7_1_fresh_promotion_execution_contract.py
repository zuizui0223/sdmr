import json
from pathlib import Path

CONTRACT = Path('configs/product_a_v2_7_1_fresh_promotion_execution_contract.json')
LAUNCHER = Path('.github/workflows/product-a-v2-7-1-fresh-promotion-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_1_fresh_promotion_pr_trigger.txt')


def test_fresh_promotion_execution_identity_is_frozen_before_outcome():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_1_fresh_promotion_execution_contract'
    assert c['execution_identity_frozen_before_any_fresh_sealed_decision'] is True
    assert c['implementation_sha']=='e5762c71554dcc11e94ce54560f6ff3660f41322'
    assert c['frozen_ref']=='frozen/product-a-v2-7-1-fresh-promotion-e5762c71'
    assert c['workflow_file']=='product-a-v2-7-1-fresh-promotion.yml'
    assert c['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    primary=c['primary_fresh_source']
    assert primary['run_id']==32552745281
    assert primary['implementation_sha']=='1f158006c0b5dbdd93af70632464727405ababfe'
    continuation=c['technical_continuation_source']
    assert continuation['implementation_sha']=='08edc61eaee19461cee440e8e8cfceb769e7f3f6'
    activation=c['activation_rule']
    assert activation['primary_decision_artifact_preferred_when_present'] is True
    assert activation['continuation_decision_admissible_only_if_primary_completed_non_success_without_decision'] is True
    assert activation['exactly_one_admissible_fresh_decision_source_required'] is True
    assert activation['scientific_decision_value_may_trigger_dispatch'] is False
    assert activation['prediction_or_recovery_metric_value_may_trigger_dispatch'] is False
    assert activation['promotion_workflow_itself_applies_frozen_state_mapping'] is True
    scope=c['scope']
    assert scope['mechanical_product_a_promotion_mapping_only'] is True
    assert scope['new_scientific_threshold_allowed'] is False
    assert scope['candidate_reselection_allowed'] is False
    assert scope['threshold_retuning_allowed'] is False
    assert scope['fresh_evidence_reanalysis_allowed'] is False
    assert scope['fundamental_niche_claim_allowed'] is False
    assert scope['temporal_independence_claim_allowed'] is False
    assert scope['causal_physiological_driver_claim_allowed'] is False
    assert scope['universal_process_claim_allowed'] is False
    assert scope['product_b_unblocked'] is False


def test_promotion_launcher_is_dormant_and_does_not_read_scientific_values():
    assert LAUNCHER.exists()
    assert not TRIGGER.exists()
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_1_fresh_promotion_execution_contract.json' in text
    assert "scientific_decision_value_read_by_launcher':False" in text
    assert "prediction_or_recovery_metric_value_read_by_launcher':False" in text
    assert "both primary and continuation decisions exist; promotion launch is ambiguous" in text
    assert "no admissible fresh decision source exists yet" in text
    assert "multiple frozen promotion runs exist" in text
    assert "payload={'ref':execution['frozen_ref']}" in text
    assert 'product-a-v2-7-1-fresh-promotion-launch-receipt' in text
