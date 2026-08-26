import hashlib
import json
from pathlib import Path

import pandas as pd


PANEL = Path('configs/product_a_v2_8_1_fresh_confirmation_taxa.csv')
SELECTION = Path('configs/product_a_v2_8_1_fresh_taxon_panel_selection_result.json')
SOURCE = Path('configs/product_a_v2_8_1_fresh_source_acquisition_contract.json')
EXECUTION = Path('configs/product_a_v2_8_1_fresh_source_execution.json')
WORKFLOW = Path('.github/workflows/product-a-v2-8-1-fresh-source-acquisition.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-8-1-fresh-source-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_8_1_fresh_source_pr_trigger.txt')


def test_v281_selection_result_pins_exact_available_12_taxon_panel():
    result = json.loads(SELECTION.read_text())
    panel = pd.read_csv(PANEL)
    panel_sha = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    assert result['purpose'] == 'product_a_v2_8_1_fresh_taxon_panel_selection_result'
    assert result['status'] == 'available'
    assert result['eligibility_run_id'] == 32988143625
    assert result['eligibility_source_head_sha'] == '2e501f090de9160627c912bbf8273e5a32500a2d'
    assert result['eligibility_artifact']['artifact_id'] == 9613925063
    assert result['eligibility_artifact']['artifact_digest'] == 'sha256:9a97889c0b69048df8142f2e59d4d860682670f13e2781440520c03fa8401dab'
    assert panel_sha == '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1'
    assert result['repository_panel']['sha256'] == panel_sha
    assert result['repository_panel']['byte_for_byte_identical_to_eligibility_artifact_selected_fresh_taxa_csv'] is True
    assert len(panel) == 12 and panel['validation_stratum'].nunique() == 12
    assert panel['scientific_name'].tolist() == result['selected_taxa']
    assert set(panel['candidate_rank'].astype(int)) == {1}
    assert (panel['n_occurrences'].astype(int) >= 80).all()
    assert (panel['n_unique_0_05_degree_cells'].astype(int) >= 50).all()
    assert result['unavailable_strata'] == []
    assert result['selected_global_sealed_fraction_for_future_confirmation'] == 0.25
    assert result['sealed_fraction_retuning_allowed'] is False
    assert result['scientific_confirmation_allowed'] is False
    assert result['scientific_promotion_allowed'] is False
    assert result['product_b_unblocked'] is False
    assert all(value is False for value in result['selection_information_barrier'].values())


def test_v281_source_contract_binds_eligibility_panel_and_stays_raw_only():
    source = json.loads(SOURCE.read_text())
    panel_sha = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    selection_sha = hashlib.sha256(SELECTION.read_bytes()).hexdigest()
    assert source['purpose'] == 'product_a_v2_8_1_fresh_taxon_raw_source_acquisition_contract'
    assert source['issue'] == 149
    assert source['predeclared_after_eligibility_before_any_fresh_source_outcome'] is True
    assert source['eligibility_freeze']['run_id'] == 32988143625
    assert source['eligibility_freeze']['artifact_id'] == 9613925063
    assert source['eligibility_freeze']['selection_result_sha256'] == selection_sha
    assert source['eligibility_freeze']['selected_panel_sha256'] == panel_sha
    assert source['fresh_taxon_panel']['n_taxa'] == 12
    assert source['fresh_taxon_panel']['n_validation_strata'] == 12
    assert source['fresh_taxon_panel']['candidate_rank_fixed_to'] == 1
    assert source['fresh_taxon_panel']['post_count_reselection_allowed'] is False
    assert source['parallel_transport']['chunk_count'] == 16
    assert source['focal_source']['thinning_at_source_acquisition'] is False
    assert source['target_group_source']['exclude_taxa_sha256'] == panel_sha
    assert source['target_group_source']['exclude_taxa_count'] == 12
    assert source['target_group_source']['one_per_grid_cell_degrees'] == 0.05
    assert source['future_confirmation_geometry']['selected_global_sealed_fraction'] == 0.25
    assert source['future_confirmation_geometry']['retuning_allowed'] is False
    assert all(value is False for value in source['information_barrier'].values())


def test_v281_source_execution_is_closed_until_separate_authorization():
    execution = json.loads(EXECUTION.read_text())
    assert execution['purpose'] == 'product_a_v2_8_1_fresh_raw_source_execution_authorization'
    assert execution['implementation_sha'] is None
    assert execution['frozen_ref'] is None
    for key in ('workflow_blob_sha', 'source_contract_blob_sha', 'selection_result_blob_sha', 'panel_blob_sha'):
        assert execution[key] is None
    assert execution['source_acquisition_only'] is True
    assert execution['chunk_count'] == 16
    assert execution['selected_global_sealed_fraction'] == 0.25
    assert execution['sealed_fraction_retuning_allowed'] is False
    for key in ('environmental_values_allowed', 'candidate_model_fitting_allowed', 'sealed_ecological_outcomes_allowed', 'scientific_confirmation_allowed', 'scientific_promotion_allowed', 'product_b_unblocked'):
        assert execution[key] is False
    assert execution['one_shot'] is True
    assert execution['execution_allowed'] is False


def test_v281_source_workflow_stays_raw_only_and_exactly_excludes_selected_panel():
    text = WORKFLOW.read_text()
    assert 'authorization_commit_sha:' in text
    assert 'authorization_blob_sha:' in text
    assert '--taxa configs/product_a_v2_8_1_fresh_confirmation_taxa.csv' in text
    assert '--exclude-taxa configs/product_a_v2_8_1_fresh_confirmation_taxa.csv' in text
    assert 'product-a-v2-8-1-fresh-focal-source-2026-08-01' in text
    assert 'product-a-v2-8-1-fresh-target-source-2026-08-01' in text
    assert 'product-a-v2-8-1-fresh-raw-source-receipt' in text
    assert '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1' in text
    assert "'scientific_confirmation_executed':False" in text
    assert "'scientific_confirmation_allowed':False" in text
    assert 'configs/chelsa_v2_1_plant_candidates.csv' not in text
    assert 'benchmark_recovery_procedures' not in text


def test_v281_source_launcher_requires_separate_authorization_and_trigger_is_absent():
    text = LAUNCHER.read_text()
    assert "authorization_commit_sha=str(event['pull_request']['base']['sha'])" in text
    assert "if json.loads(base64.b64decode(base_auth['content']).decode())!=auth" in text
    assert "auth.get('execution_allowed') is not True" in text
    assert "verify_blob('.github/workflows/product-a-v2-8-1-fresh-source-acquisition.yml',auth['workflow_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_8_1_fresh_confirmation_taxa.csv',auth['panel_blob_sha'])" in text
    assert 'multiple exact v2.8.1 source runs exist' in text
    assert "'scientific_confirmation_allowed':False" in text
    assert not TRIGGER.exists()
