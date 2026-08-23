import json
from pathlib import Path

CONTRACT=Path('configs/product_a_v2_7_2_fresh_source_execution_contract.json')
LAUNCHER=Path('.github/workflows/product-a-v2-7-2-fresh-source-pr-launch.yml')
TRIGGER=Path('configs/product_a_v2_7_2_fresh_source_pr_trigger.txt')


def test_v272_source_execution_is_exact_one_shot_and_source_only():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_2_fresh_raw_source_execution_contract'
    assert c['execution_source_frozen_before_raw_source_outcome'] is True
    assert c['implementation_sha']=='1de8a07cbbd17bdec80432d4d61c8882d46a0764'
    assert c['frozen_ref']=='frozen/product-a-v2-7-2-fresh-source-1de8a07c'
    assert c['workflow_file']=='product-a-v2-7-2-fresh-source-acquisition.yml'
    assert c['source_acquisition_contract_blob_sha']=='c732c46bfeb8fd82b97e1dee30f5794072c1fab0'
    assert c['confirmation_decision_contract_blob_sha']=='04ec0d9519b8ea5ed7720f04cffb79ec0cdf4291'
    assert c['fresh_taxon_panel_sha256']=='918ea2d3e94f93c26616ab30aa055a5dd72b4550d75dbbeb6a675e7a4e950f44'
    assert c['requires_single_workflow_dispatch_run_for_frozen_source'] is True
    assert c['expected_artifacts']['focal']=='product-a-v2-7-2-fresh-focal-source-2026-08-01'
    assert c['expected_artifacts']['target_group']=='product-a-v2-7-2-fresh-target-source-2026-08-01'
    assert c['expected_artifacts']['source_receipt']=='product-a-v2-7-2-fresh-raw-source-receipt'
    assert all(value is False for value in c['scope'].values() if isinstance(value,bool) and value is not True)
    assert c['scope']['raw_occurrence_source_acquisition_only'] is True
    assert c['scope']['empirical_confirmation_execution_allowed'] is False
    assert c['scope']['scientific_promotion_allowed'] is False
    assert c['scope']['product_b_unblocked'] is False


def test_v272_source_launcher_is_one_shot_and_trigger_is_absent():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_2_fresh_source_pr_trigger.txt' in text
    assert 'source_acquisition_contract_blob_sha' in text
    assert 'confirmation_decision_contract_blob_sha' in text
    assert "payload={'ref':c['frozen_ref']}" in text
    assert 'multiple frozen v2.7.2 source runs exist' in text
    assert "'raw_source_only':True" in text
    assert "'empirical_confirmation_execution_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
