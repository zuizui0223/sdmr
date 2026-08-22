import hashlib
import json
from pathlib import Path

RAW_CONTRACT = Path('configs/product_a_v2_7_1_fresh_source_execution_contract.json')
CONFIRMATION_EXECUTION = Path('configs/product_a_v2_7_1_fresh_confirmation_execution_contract.json')
PANEL = Path('configs/product_a_v2_7_1_fresh_confirmation_taxa.csv')
DECISION = Path('configs/product_a_v2_7_1_fresh_confirmation_contract.json')
SOURCE_GATE = Path('configs/product_a_v2_7_1_fresh_empirical_source_gate.json')
SOURCE_RECEIPT = Path('configs/product_a_v2_7_1_fresh_raw_source_receipt.json')
LAUNCHER = Path('.github/workflows/product-a-v2-7-1-fresh-confirmation-pr-launch.yml')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fresh_raw_source_execution_is_exactly_pinned_and_non_scientific():
    c = json.loads(RAW_CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_raw_source_execution_contract'
    assert c['execution_source_frozen_before_raw_source_outcome'] is True
    assert c['implementation_sha'] == '7c6dbf0ab11fa21451fc46b7c6960d4aa3ca6656'
    assert c['frozen_ref'] == 'frozen/product-a-v2-7-1-fresh-source-7c6dbf0a'
    assert c['workflow_file'] == 'product-a-v2-7-1-fresh-source-acquisition.yml'
    assert c['requires_single_workflow_dispatch_run_for_frozen_source'] is True
    assert c['fresh_taxon_panel_sha256'] == sha256(PANEL)
    assert c['confirmation_decision_contract_sha256'] == sha256(DECISION)
    assert c['expected_artifacts']['focal'] == 'product-a-v2-7-1-fresh-focal-source-2026-08-01'
    assert c['expected_artifacts']['target_group'] == 'product-a-v2-7-1-fresh-target-source-2026-08-01'
    assert c['expected_artifacts']['source_receipt'] == 'product-a-v2-7-1-fresh-raw-source-receipt'
    scope = c['scope']
    assert scope['raw_occurrence_source_acquisition_only'] is True
    assert scope['candidate_model_fitting_allowed'] is False
    assert scope['CHELSA_environmental_values_allowed'] is False
    assert scope['sealed_confirmation_outcomes_allowed'] is False
    assert scope['empirical_confirmation_execution_allowed'] is False
    assert scope['scientific_promotion_allowed'] is False
    assert scope['product_b_unblocked'] is False


def test_fresh_confirmation_execution_identity_is_frozen_and_gate_is_open():
    e = json.loads(CONFIRMATION_EXECUTION.read_text())
    g = json.loads(SOURCE_GATE.read_text())
    r = json.loads(SOURCE_RECEIPT.read_text())
    assert e['purpose'] == 'product_a_v2_7_1_fresh_confirmation_execution_contract'
    assert e['execution_identity_frozen_before_confirmation_outcome'] is True
    assert e['implementation_sha'] == '1f158006c0b5dbdd93af70632464727405ababfe'
    assert e['frozen_ref'] == 'frozen/product-a-v2-7-1-fresh-confirmation-1f158006'
    assert e['workflow_file'] == 'product-a-v2-7-1-fresh-confirmation.yml'
    assert e['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    assert e['raw_source_workflow_run_id'] == 32477393089
    assert e['fresh_taxon_panel_sha256'] == sha256(PANEL)
    assert e['decision_contract_sha256'] == sha256(DECISION)
    scope = e['scope']
    assert scope['fresh_taxon_holdout_empirical_confirmation_execution'] is True
    assert scope['taxon_panel_change_allowed'] is False
    assert scope['split_or_threshold_change_allowed'] is False
    assert scope['post_outcome_candidate_reselection_allowed'] is False
    assert scope['post_outcome_threshold_tuning_allowed'] is False
    assert scope['scientific_promotion_allowed'] is False
    assert scope['product_b_unblocked'] is False

    assert g['gate_state'] == 'ready_for_one_shot_fresh_confirmation'
    assert g['execution_allowed'] is True
    required = g['required_before_execution']
    for key in ('implementation_sha', 'frozen_ref', 'workflow_file'):
        assert required[key] == e[key]
    assert required['focal_file_sha256'] == r['focal']['file_sha256']
    assert required['focal_query_sha256'] == r['focal']['query_sha256']
    assert required['target_group_file_sha256'] == r['target_group']['file_sha256']
    assert required['target_group_query_sha256'] == r['target_group']['query_sha256']
    assert required['target_group_excluded_taxa_sha256'] == sha256(PANEL)


def test_confirmation_launcher_is_trigger_only_and_one_shot():
    text = LAUNCHER.read_text(encoding='utf-8')
    assert "configs/product_a_v2_7_1_fresh_confirmation_pr_trigger.txt" in text
    assert "requires_single_workflow_dispatch_run_for_frozen_identity" in text
    assert "multiple frozen fresh-confirmation runs exist" in text
    assert "payload={'ref':execution['frozen_ref']}" in text
    assert 'scientific_promotion_allowed' in text
    assert 'product_b_unblocked' in text
    assert 'post_outcome_retuning_allowed' in text
