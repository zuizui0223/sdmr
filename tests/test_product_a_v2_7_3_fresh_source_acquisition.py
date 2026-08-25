import hashlib
import json
from pathlib import Path


SOURCE = Path('configs/product_a_v2_7_3_fresh_source_acquisition_contract.json')
EXECUTION = Path('configs/product_a_v2_7_3_fresh_source_execution.json')
PANEL = Path('configs/product_a_v2_7_3_rank3_taxa.csv')
DESIGN = Path('configs/product_a_v2_7_3_presealed_feasibility_contract.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-3-fresh-source-acquisition.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-7-3-fresh-source-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_3_fresh_source_pr_trigger.txt')


def test_rank3_source_contract_is_raw_only_and_predeclared():
    c = json.loads(SOURCE.read_text())
    assert c['purpose'] == 'product_a_v2_7_3_rank3_fresh_raw_source_acquisition_contract'
    assert c['issue'] == 123
    assert c['predeclared_before_any_v2_7_3_raw_source_outcome'] is True
    assert c['design_freeze']['merge_sha'] == 'f4bd76206d05852d7262b58a0f70906013408fc9'
    assert c['design_freeze']['panel_blob_sha'] == 'e8b734df9571674e1b6e710b4a0f36735425a7b8'
    assert c['design_freeze']['presealed_feasibility_contract_blob_sha'] == '58d4ff7111b88d5109d2d26943e68364c98d2133'
    assert c['rank3_panel']['candidate_rank'] == 3
    assert c['rank3_panel']['n_taxa'] == 12
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == c['rank3_panel']['sha256']
    assert c['snapshot']['date'] == '2026-08-01'
    assert c['snapshot']['doi'] == '10.15468/dl.fs3btq'
    assert c['snapshot']['same_catalog_as_v2_7_2_allowed'] is True
    assert c['snapshot']['catalog_reuse_is_transport_not_focal_evidence_reuse'] is True
    assert c['parallel_transport']['chunk_count'] == 16
    assert c['target_group_source']['one_per_grid_cell_degrees'] == 0.05
    assert c['focal_source']['rank1_or_rank2_focal_artifact_reused'] is False
    assert c['target_group_source']['rank1_or_rank2_target_artifact_reused'] is False
    barrier = c['information_barrier']
    for key in (
        'CHELSA_environmental_values_read', 'candidate_model_scores_read',
        'candidate_model_fitting_performed', 'niche_recovery_outcomes_read',
        'rank1_or_rank2_split_rows_reused', 'rank1_or_rank2_sealed_rows_read',
        'rank2_sealed_confirmation_outcomes_read',
        'presealed_feasibility_evaluated_during_source_acquisition',
        'scientific_promotion_allowed', 'product_b_unblocked',
    ):
        assert barrier[key] is False


def test_source_execution_gate_is_closed_before_freeze_and_authorization():
    e = json.loads(EXECUTION.read_text())
    assert e['purpose'] == 'product_a_v2_7_3_rank3_fresh_raw_source_execution_authorization'
    assert e['implementation_sha'] is None
    assert e['frozen_ref'] is None
    assert e['workflow_blob_sha'] is None
    assert e['source_contract_blob_sha'] is None
    assert e['panel_blob_sha'] is None
    assert e['presealed_feasibility_contract_blob_sha'] is None
    assert e['source_acquisition_only'] is True
    assert e['chunk_count'] == 16
    assert e['candidate_model_fitting_allowed'] is False
    assert e['CHELSA_environmental_values_allowed'] is False
    assert e['rank2_sealed_confirmation_outcomes_allowed'] is False
    assert e['presealed_feasibility_execution_allowed'] is False
    assert e['scientific_promotion_allowed'] is False
    assert e['product_b_unblocked'] is False
    assert e['one_shot'] is True
    assert e['execution_allowed'] is False


def test_source_workflow_requires_external_authorization_and_uses_rank3_only():
    text = WORKFLOW.read_text()
    assert 'authorization_commit_sha:' in text
    assert 'authorization_blob_sha:' in text
    assert 'expected_runtime_sha:' in text
    assert 'expected_frozen_ref:' in text
    assert "auth=json.load(open('configs/product_a_v2_7_3_fresh_source_execution.json'))" not in text
    assert "meta=get(f'{api}/contents/{auth_path}?ref={auth_ref}')" in text
    assert "auth.get('execution_allowed') is not True" in text
    assert '--taxa configs/product_a_v2_7_3_rank3_taxa.csv' in text
    assert '--exclude-taxa configs/product_a_v2_7_3_rank3_taxa.csv' in text
    assert 'product-a-v2-7-3-rank3-focal-source-2026-08-01' in text
    assert 'product-a-v2-7-3-rank3-target-source-2026-08-01' in text
    assert 'product-a-v2-7-3-rank3-fresh-raw-source-receipt' in text
    assert 'sdmr.fresh_focal_parallel chunk' in text
    assert 'sdmr.fresh_focal_parallel aggregate' in text
    assert 'sdmr-gbif-target-footprint-parallel chunk' in text
    assert 'sdmr-gbif-target-footprint-parallel aggregate' in text
    assert "'environmental_values_read':False" in text
    assert "'candidate_model_fitting_performed':False" in text
    assert "'rank2_sealed_confirmation_outcomes_read':False" in text
    assert "'presealed_feasibility_executed':False" in text


def test_source_launcher_is_one_shot_external_auth_and_trigger_absent():
    text = LAUNCHER.read_text()
    assert "authorization_commit_sha=str(event['pull_request']['base']['sha'])" in text
    assert "if json.loads(decoded)!=auth:" in text
    assert "auth.get('execution_allowed') is not True" in text
    assert "verify_blob('.github/workflows/product-a-v2-7-3-fresh-source-acquisition.yml',auth['workflow_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_7_3_fresh_source_acquisition_contract.json',auth['source_contract_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_7_3_rank3_taxa.csv',auth['panel_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_7_3_presealed_feasibility_contract.json',auth['presealed_feasibility_contract_blob_sha'])" in text
    assert 'multiple exact v2.7.3 source runs exist' in text
    assert "'authorization_commit_sha':authorization_commit_sha" in text
    assert "'authorization_blob_sha':authorization_blob_sha" in text
    assert "'presealed_feasibility_execution_allowed':False" in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()


def test_source_contract_keeps_presealed_design_gate_closed():
    source = json.loads(SOURCE.read_text())
    design = json.loads(DESIGN.read_text())
    assert source['next_gate'].startswith('pin exact rank3 focal/target artifact')
    assert design['execution_identity']['execution_allowed'] is False
    assert design['presealed_admission_gate']['runs_before_model_pool_fitting'] is True
    assert design['presealed_admission_gate']['runs_before_sealed_raster_extraction'] is True
