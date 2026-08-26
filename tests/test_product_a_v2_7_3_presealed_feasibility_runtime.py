import json
from pathlib import Path

from sdmr.v2_7_3_presealed_feasibility import aggregate_parts


PIN = Path('configs/product_a_v2_7_3_fresh_source_pin.json')
EXECUTION = Path('configs/product_a_v2_7_3_presealed_feasibility_execution.json')
RECEIPT = Path('configs/product_a_v2_7_3_presealed_feasibility_final_receipt.json')
DESIGN = Path('configs/product_a_v2_7_3_presealed_feasibility_contract.json')
MODULE = Path('src/sdmr/v2_7_3_presealed_feasibility.py')
WORKFLOW = Path('.github/workflows/product-a-v2-7-3-presealed-feasibility.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-7-3-presealed-feasibility-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_3_presealed_feasibility_pr_trigger.txt')


def test_exact_rank3_source_is_pinned_before_feasibility():
    p = json.loads(PIN.read_text())
    assert p['purpose'] == 'product_a_v2_7_3_rank3_fresh_raw_source_pin'
    assert p['workflow_run_id'] == 32858840773
    assert p['workflow_conclusion'] == 'success'
    assert p['execution_sha'] == 'a41850a2fd48bef666bd55983020cf398f6ed1ba'
    assert p['execution_ref'] == 'frozen/product-a-v2-7-3-rank3-source-a41850a2'
    assert p['source_receipt_artifact']['id'] == 9568216635
    assert p['source_receipt_artifact']['digest'] == 'sha256:f32d413650d82f2b0694aebd17fa66f9859f13d3ea7f41d706830a6f4f523f75'
    assert p['focal']['artifact_id'] == 9568207639
    assert p['focal']['file_sha256'] == '2339a4b9326711be8bec0a412e83a3888033b86ba4d27dc35a9eb4ed7b3e1ada'
    assert p['focal']['query_sha256'] == '50b9a82d68202a8c69ac77094f441a03ac0e0e0b36a18e17563c8a36ec6150e6'
    assert p['target_group']['artifact_id'] == 9567849055
    assert p['target_group']['file_sha256'] == '665051395d156c3a7263eb57512af5e87eb625d595c08ebf5a4d66a22825aa9f'
    assert p['target_group']['query_sha256'] == 'c1c9f94d8f880e4b0eb165955cc8209ba73a022450b0fc408805e25c14cbb50a'
    assert p['target_group']['excluded_taxa_sha256'] == p['rank3_taxon_panel_sha256']
    assert p['ready_for_presealed_feasibility'] is True
    assert p['ready_for_scientific_model_fitting'] is False
    for value in p['information_barrier'].values():
        assert value is False


def test_presealed_execution_is_consumed_after_exact_frozen_run():
    e = json.loads(EXECUTION.read_text())
    assert e['purpose'] == 'product_a_v2_7_3_presealed_structural_feasibility_execution_authorization'
    assert e['implementation_sha'] == '0b0ab3fa00e04fb86f2db83963c6b1f051f24cf3'
    assert e['frozen_ref'] == 'frozen/product-a-v2-7-3-presealed-0b0ab3fa'
    assert e['workflow_blob_sha'] == '672677d9262a907f584011ad30c8b5e3ed2bd914'
    assert e['module_blob_sha'] == 'cbe3d23e5a06d35167c4a5ff68d50a2ba4581c8d'
    assert e['feasibility_contract_blob_sha'] == '58d4ff7111b88d5109d2d26943e68364c98d2133'
    assert e['source_pin_blob_sha'] == 'a04bc7c5c9a34f4ce6c381f255631c2168720d0a'
    assert e['panel_blob_sha'] == 'e8b734df9571674e1b6e710b4a0f36735425a7b8'
    assert e['evidence_partition_blob_sha'] == '2109221ee796bee39093c0f9388d63761a62f4af'
    assert e['source_acquisition_run_id'] == 32858840773
    assert e['run_all_6_parts'] is True
    assert e['require_full_12_taxa_x_3_M_denominator'] is True
    for key in (
        'open_sealed_environmental_evidence', 'model_pool_fitting_allowed',
        'rank2_sealed_confirmation_outcomes_allowed', 'scientific_runtime_execution_allowed',
        'post_outcome_retuning_allowed', 'candidate_reselection_allowed',
        'scientific_promotion_allowed', 'product_b_unblocked',
    ):
        assert e[key] is False
    assert e['one_shot'] is True
    assert e['execution_allowed'] is False
    assert e['consumed_by_run_id'] == 32925557219
    assert e['consumed_decision'] == 'presealed_unavailable'
    assert e['consumed_decision_artifact_id'] == 9592334790

    receipt = json.loads(RECEIPT.read_text())
    assert receipt['workflow_run_id'] == 32925557219
    assert receipt['workflow_conclusion'] == 'success'
    assert receipt['decision'] == 'presealed_unavailable'
    assert receipt['n_available_parts'] == 4
    assert receipt['interpretation']['presealed_denominator_feasibility_failure'] is True
    assert receipt['interpretation']['negative_ecological_or_model_evidence'] is False


def test_presealed_module_and_workflow_exclude_scientific_outcome_inputs():
    module = MODULE.read_text()
    workflow = WORKFLOW.read_text()
    design = json.loads(DESIGN.read_text())
    assert 'benchmark_recovery_procedures' not in module
    assert 'select_model_pool_admissible_predictors' not in module
    assert 'select_partition_aware_empirical_audit_space' not in module
    assert 'raster_specs_from_chelsa_manifest' not in module
    assert 'extract_protocol_grid_rasters' not in module
    assert 'make_evidence_balanced_spatial_partitions' in module
    assert 'configs/chelsa_v2_1_plant_candidates.csv' not in workflow
    assert 'v2_7_2_fresh_model_pool' not in workflow
    assert 'v2_7_2_fresh_sealed_audit' not in workflow
    assert 'v273-presealed-raw-source-pair' in workflow
    assert 'product-a-v2-7-3-presealed-feasibility-decision' in workflow
    assert design['presealed_admission_gate']['forbidden_inputs'] == [
        'rank2_sealed_outcomes', 'environmental_raster_values', 'auc', 'presence_rank',
        'continuous_boyce_or_cbi', 'or10', 'aicc', 'niche_overlap_schoener_d_pc12',
        'centroid_distance', 'breadth_log_sd_error', 'quantile_profile_error',
        'candidate_scores', 'selected_predictors', 'fitted_coefficients',
        'process_knockout_outcomes',
    ]


def _part_contract(seed, fraction, available=True):
    return {
        'purpose': 'product_a_v2_7_3_presealed_feasibility_part',
        'available': available,
        'seed': seed,
        'sealed_fraction': fraction,
        'n_taxa': 12,
        'n_feasible_taxa': 12 if available else 11,
        'M_specs': ['buffer_150km', 'buffer_300km', 'buffer_500km'],
        'unavailable_stage': None if available else 'structural_partition',
        'unavailable_reason': None if available else 'synthetic structural abstention',
        'environmental_values_read': False,
        'sealed_environmental_values_read': False,
        'candidate_model_fitting_performed': False,
        'candidate_scores_read': False,
        'rank2_sealed_confirmation_outcomes_read': False,
        'scientific_model_execution_allowed': False,
    }


def test_six_part_aggregate_admits_only_complete_structural_denominator(tmp_path):
    parts = tmp_path / 'parts'
    for seed in (2026082201, 2026082202, 2026082203):
        for fraction in (0.20, 0.30):
            d = parts / f'{seed}-{fraction}'
            d.mkdir(parents=True)
            (d / 'contract.json').write_text(json.dumps(_part_contract(seed, fraction)))
    admitted = aggregate_parts(parts_root=parts, output_dir=tmp_path / 'admitted')
    assert admitted['decision'] == 'presealed_admitted'
    assert admitted['n_available_parts'] == 6
    assert admitted['scientific_model_execution_allowed'] is False
    assert admitted['separate_scientific_runtime_authorization_required_if_admitted'] is True

    bad = parts / '2026082203-0.3' / 'contract.json'
    bad.write_text(json.dumps(_part_contract(2026082203, 0.30, available=False)))
    unavailable = aggregate_parts(parts_root=parts, output_dir=tmp_path / 'unavailable')
    assert unavailable['decision'] == 'presealed_unavailable'
    assert unavailable['n_available_parts'] == 5
    assert unavailable['scientific_model_execution_allowed'] is False


def test_launcher_is_external_one_shot_and_trigger_absent():
    text = LAUNCHER.read_text()
    assert "authorization_commit_sha=str(event['pull_request']['base']['sha'])" in text
    assert "auth.get('execution_allowed') is not True" in text
    assert "verify_blob('.github/workflows/product-a-v2-7-3-presealed-feasibility.yml',auth['workflow_blob_sha'])" in text
    assert "verify_blob('src/sdmr/v2_7_3_presealed_feasibility.py',auth['module_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_7_3_fresh_source_pin.json',auth['source_pin_blob_sha'])" in text
    assert "verify_blob('src/sdmr/v2_7_1_evidence_balanced_partition.py',auth['evidence_partition_blob_sha'])" in text
    assert 'multiple exact v2.7.3 feasibility runs exist' in text
    assert "'environmental_values_allowed':False" in text
    assert "'candidate_model_fitting_allowed':False" in text
    assert "'scientific_runtime_execution_allowed':False" in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
