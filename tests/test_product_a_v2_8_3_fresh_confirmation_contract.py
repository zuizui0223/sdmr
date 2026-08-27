import hashlib
import json
import math
from pathlib import Path

import pandas as pd


CONTRACT = Path('configs/product_a_v2_8_3_fresh_confirmation_contract.json')
SOURCE_RECEIPT = Path('configs/product_a_v2_8_2_fresh_raw_source_receipt.json')
PANEL = Path('configs/product_a_v2_8_2_fresh_confirmation_taxa.csv')
V271 = Path('configs/product_a_v2_7_1_fresh_confirmation_contract.json')
V272_DETERMINISTIC = Path('configs/product_a_v2_7_2_deterministic_successor_contract.json')
PROCESS_REGISTRY = Path('configs/product_a_empirical_process_registry_v1.csv')
PARTITION = Path('src/sdmr/v2_7_1_evidence_balanced_partition.py')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v283_design_is_predeclared_single_fraction_three_part_translation():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_8_3_single_fraction_fresh_confirmation_contract'
    assert c['tracks_issue'] == 158
    assert c['predeclared_before_any_v2_8_3_structural_or_environmental_outcome'] is True

    geometry = c['upstream_geometry_calibration']
    assert geometry['workflow_run_id'] == 32943026025
    assert geometry['implementation_sha'] == '32d5b67f7b18634830191df52ef56128589f5d82'
    assert geometry['decision_artifact_id'] == 9609352973
    assert geometry['decision_artifact_digest'] == 'sha256:a08c9f40d89b65ccf7357289b7e89bda7e6844cc6c2014edaeafb14c368c63d6'
    assert geometry['selected_global_sealed_fraction'] == 0.25
    assert geometry['fraction_retuning_allowed'] is False
    assert geometry['geometry_result_is_ecological_support'] is False

    design = c['fixed_design']
    assert design['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert design['sealed_fractions'] == [0.25]
    assert design['n_confirmation_parts'] == 3
    assert design['M_km'] == [150, 300, 500]
    assert design['M_is_sensitivity_not_optimization'] is True
    assert design['outer_folds'] == 4
    assert design['spatial_microblocks'] == 12
    assert design['assignment_attempts'] == 32
    assert design['minimum_evaluation_occurrences_per_fold'] == 2
    assert design['minimum_evaluation_background_rows_per_M_fold'] == 5
    assert design['minimum_training_background_rows_per_M_fold'] == 5

    translation = c['single_fraction_denominator_translation']
    assert translation['predecessor_parts'] == 6
    assert translation['successor_parts'] == 3
    assert translation['duplicate_0_25_parts_allowed'] is False
    assert translation['new_post_calibration_split_seeds_allowed'] is False
    assert translation['ecological_nondomination_predecessor_minimum_parts'] == 4
    assert translation['ecological_nondomination_successor_minimum_parts'] == math.ceil((4 / 6) * 3) == 2
    assert translation['strict_improvement_predecessor_minimum_parts'] == 3
    assert translation['strict_improvement_successor_minimum_parts'] == 2

    decision = c['decision_rule']
    assert decision['all_3_parts_required_for_primary_full_denominator_decision'] is True
    assert decision['all_12_taxa_required_in_every_part'] is True
    assert decision['all_3_M_specs_required_in_every_part'] is True
    assert decision['fewer_than_3_structurally_auditable_parts_primary_state'] == 'empirical_confirmation_unavailable'
    assert decision['zero_structurally_auditable_parts_opens_environmental_or_sealed_evidence'] is False
    assert decision['prediction_guardrail']['mean_presence_rank_deficit_vs_auc_comparator_min'] == -0.01
    assert decision['ecological_noninferiority']['minimum_parts'] == 2
    assert decision['ecological_noninferiority']['strict_improvement_minimum_parts'] == 2
    assert abs(decision['process_reproducibility']['modal_status_fraction_min'] - 2 / 3) < 1e-12
    assert decision['post_outcome_candidate_reselection_allowed'] is False
    assert decision['post_outcome_threshold_tuning_allowed'] is False
    assert decision['random_seed_changes_after_outcome_allowed'] is False
    assert decision['scientific_promotion_allowed_by_this_decision'] is False
    assert decision['product_b_remains_blocked_until_separate_promotion_decision'] is True


def test_v283_design_binds_exact_source_panel_and_inherited_semantics_fail_closed():
    c = json.loads(CONTRACT.read_text())
    source = json.loads(SOURCE_RECEIPT.read_text())
    v271 = json.loads(V271.read_text())
    v272 = json.loads(V272_DETERMINISTIC.read_text())
    panel = pd.read_csv(PANEL)

    assert sha256(PANEL) == '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1'
    assert len(panel) == 12 and panel['validation_stratum'].nunique() == 12
    assert set(panel['candidate_rank'].astype(int)) == {1}
    assert c['fresh_taxon_panel']['sha256'] == sha256(PANEL)
    assert c['fresh_taxon_panel']['blob_sha'] == '5c00886724405edeb13dae4f029ec19573ad180f'

    assert source['workflow_run_id'] == 33006988136 and source['workflow_conclusion'] == 'success'
    assert c['upstream_fresh_source']['receipt_blob_sha'] == 'ed4d90a84db354e06a4a214f6a3a184c7e36ea7f'
    assert c['upstream_fresh_source']['receipt_merge_sha'] == '641b0cce93f5349fc00577bdd12312f327f854c5'
    assert c['upstream_fresh_source']['workflow_run_id'] == source['workflow_run_id']
    assert c['upstream_fresh_source']['focal_file_sha256'] == source['focal']['file_sha256']
    assert c['upstream_fresh_source']['focal_query_sha256'] == source['focal']['query_sha256']
    assert c['upstream_fresh_source']['target_file_sha256'] == source['target_group']['file_sha256']
    assert c['upstream_fresh_source']['target_query_sha256'] == source['target_group']['query_sha256']
    assert c['upstream_fresh_source']['snapshot_shard_catalog_sha256'] == source['snapshot']['snapshot_shard_catalog_sha256']

    assert sha256(V271) == '32ed21aedb87bd796324d569b696b97fc58ddbec2ccd848723006f0ea7b1ba5b'
    assert c['inherited_scientific_semantics']['v2_7_1_contract_blob_sha'] == '8b7c2680d2999e61c8672934724988bf0e217fe1'
    assert v271['fixed_design']['split_seeds'] == c['fixed_design']['split_seeds']
    assert v271['fixed_design']['M_km'] == c['fixed_design']['M_km']
    assert v271['fixed_design']['procedure_library'] == c['fixed_design']['procedure_library']
    assert v271['fixed_design']['prediction_adequacy'] == c['fixed_design']['prediction_adequacy']
    assert v271['v2_7_1_partition_aware_audit_space'] == c['fixed_design']['partition_aware_audit_space']
    assert v271['empirical_target']['metrics'] == c['empirical_target']['recovery_metrics']

    assert c['inherited_scientific_semantics']['v2_7_2_deterministic_contract_blob_sha'] == 'c251b19c21e199894be3c93d8b36e3d2329a9777'
    correction = v272['implementation_change']
    assert correction['successor_model_random_state'] == c['inherited_scientific_semantics']['model_random_state'] == 0
    assert correction['successor_selection_process_numpy_seed'] == c['inherited_scientific_semantics']['selection_process_numpy_seed'] == 0
    assert correction['solver'] == c['inherited_scientific_semantics']['solver'] == 'liblinear'
    assert correction['all_other_model_hyperparameters_changed'] is False
    assert correction['procedure_strategies_changed'] is False
    assert correction['candidate_predictor_universe_changed'] is False
    assert correction['prediction_adequacy_changed'] is False
    assert correction['ecological_recovery_metrics_changed'] is False
    assert correction['weighted_super_score_allowed'] is False

    assert sha256(PROCESS_REGISTRY) == '08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d'
    assert c['fixed_design']['process_registry_blob_sha'] == '469a1ced27ff47fe6b731c26cc3b9b0f4a56d58a'
    assert c['fixed_design']['process_registry_sha256'] == sha256(PROCESS_REGISTRY)
    assert c['structural_transportability']['partition_module_blob_sha'] == '2109221ee796bee39093c0f9388d63761a62f4af'
    assert PARTITION.exists()
    assert c['structural_transportability']['n_taxon_M_part_cells'] == 12 * 3 * 3 == 108
    assert c['structural_transportability']['n_cells_per_part'] == 12 * 3 == 36
    assert c['structural_transportability']['environmental_extraction_allowed_only_for_structurally_auditable_complete_parts'] is True
    assert c['structural_transportability']['taxon_M_or_seed_replacement_after_structural_result_allowed'] is False
    assert c['structural_transportability']['incomplete_part_partial_repair_allowed'] is False

    boundary = c['execution_boundary']
    assert boundary['runtime_implementation_sha'] is None
    assert boundary['runtime_frozen_ref'] is None
    assert boundary['execution_allowed'] is False
    assert boundary['structural_query_allowed_before_separate_runtime_freeze_and_authorization'] is False
    assert boundary['environmental_extraction_allowed_before_separate_runtime_freeze_and_authorization'] is False
    assert boundary['model_fitting_allowed_before_separate_runtime_freeze_and_authorization'] is False
    assert boundary['sealed_ecological_read_allowed_before_separate_runtime_freeze_and_authorization'] is False
    assert boundary['scientific_promotion_allowed'] is False
    assert boundary['product_b_unblocked'] is False
    assert boundary['separate_external_one_shot_authorization_required'] is True
