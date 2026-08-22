import hashlib
import json
from pathlib import Path

CONTRACT = Path('configs/product_a_v2_7_1_fresh_source_execution_contract.json')
PANEL = Path('configs/product_a_v2_7_1_fresh_confirmation_taxa.csv')
DECISION = Path('configs/product_a_v2_7_1_fresh_confirmation_contract.json')
SOURCE_GATE = Path('configs/product_a_v2_7_1_fresh_empirical_source_gate.json')
SOURCE_RECEIPT = Path('configs/product_a_v2_7_1_fresh_raw_source_receipt.json')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fresh_raw_source_execution_is_exactly_pinned_and_non_scientific():
    c = json.loads(CONTRACT.read_text())
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


def test_raw_sources_are_now_pinned_but_confirmation_identity_remains_blocked():
    c = json.loads(SOURCE_GATE.read_text())
    r = json.loads(SOURCE_RECEIPT.read_text())
    assert c['execution_allowed'] is False
    assert c['gate_state'] == 'raw_sources_pinned_exact_confirmation_implementation_pending'
    assert r['workflow_run_id'] == 32477393089
    assert r['workflow_conclusion'] == 'success'
    required = c['required_before_execution']
    assert required['focal_file_sha256'] == r['focal']['file_sha256']
    assert required['focal_query_sha256'] == r['focal']['query_sha256']
    assert required['target_group_file_sha256'] == r['target_group']['file_sha256']
    assert required['target_group_query_sha256'] == r['target_group']['query_sha256']
    assert required['target_group_excluded_taxa_sha256'] == sha256(PANEL)
    assert required['implementation_sha'] is None
    assert required['frozen_ref'] is None
    assert required['workflow_file'] is None
