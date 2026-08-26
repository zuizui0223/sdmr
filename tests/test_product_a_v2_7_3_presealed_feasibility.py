import hashlib
import json
from pathlib import Path

import pandas as pd


REGISTRY = Path('configs/product_a_v2_7_1_fresh_taxon_candidates.csv')
RANK2 = Path('configs/product_a_v2_7_2_fresh_confirmation_taxa.csv')
RANK3 = Path('configs/product_a_v2_7_3_rank3_taxa.csv')
CONTRACT = Path('configs/product_a_v2_7_3_presealed_feasibility_contract.json')
EXECUTION = Path('configs/product_a_v2_7_3_presealed_feasibility_execution.json')


def test_rank3_panel_is_exact_preexisting_rank3_registry_cohort():
    registry = pd.read_csv(REGISTRY)
    expected = registry.loc[registry['candidate_rank'].eq(3)].reset_index(drop=True)
    observed = pd.read_csv(RANK3).reset_index(drop=True)
    assert len(observed) == 12
    assert observed['validation_stratum'].nunique() == 12
    pd.testing.assert_frame_equal(observed, expected, check_dtype=False)
    digest = hashlib.sha256(RANK3.read_bytes()).hexdigest()
    assert digest == '0466ecf70aae33b950dc7061861f4279d869933b725c9517c4188fbaa64534c3'


def test_rank3_panel_does_not_reuse_rank2_taxa():
    rank2 = set(pd.read_csv(RANK2)['scientific_name'].astype(str))
    rank3 = set(pd.read_csv(RANK3)['scientific_name'].astype(str))
    assert len(rank2) == 12
    assert len(rank3) == 12
    assert rank2.isdisjoint(rank3)


def test_presealed_feasibility_contract_inherits_partition_without_relaxation():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_3_rank3_presealed_structural_feasibility_contract'
    assert c['issue'] == 123
    assert c['declared_before_any_v2_7_3_source_acquisition_partition_model_or_sealed_outcome'] is True
    assert c['predecessor']['decision'] == 'empirical_confirmation_unavailable'
    assert c['predecessor']['decision_is_negative_empirical_evidence'] is False
    assert c['predecessor']['rank2_sealed_outcomes_allowed_for_v2_7_3_design_or_admission'] is False
    panel = c['rank3_panel']
    assert panel['candidate_rank'] == 3
    assert panel['candidate_registry_blob_sha'] == 'ee43c9731eb8ad3673d2fa9271e0c3a8503bd0e0'
    assert panel['candidate_order_preexisted_rank2_outcome'] is True
    assert panel['rank1_consumed'] is True and panel['rank2_consumed'] is True
    assert panel['fallback_or_reselection_after_feasibility_result_allowed'] is False

    design = c['fixed_design']
    assert design['M_km'] == [150, 300, 500]
    assert design['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert design['sealed_fractions'] == [0.2, 0.3]
    assert design['n_parts'] == 6
    assert design['model_random_state'] == 0
    assert design['selection_process_numpy_seed'] == 0

    p = c['inherited_evidence_balanced_partition']
    assert p['outer_folds'] == 4
    assert p['spatial_microblocks'] == 12
    assert p['assignment_attempts'] == 32
    assert p['minimum_evaluation_occurrences_per_fold'] == 2
    assert p['minimum_evaluation_background_rows_per_M_fold'] == 5
    assert p['minimum_training_background_rows_per_M_fold'] == 5
    assert p['thresholds_or_attempts_changed'] is False
    assert p['abstain_if_no_feasible_assignment'] is True

    a = c['inherited_partition_aware_audit_space']
    assert a['minimum_predictor_coverage'] == 0.95
    assert a['minimum_joint_coverage'] == 0.8
    assert a['minimum_processes'] == 4
    assert a['minimum_complete_fit_background_rows_per_M_fold'] == 5
    assert a['minimum_complete_evaluation_background_rows_per_M_fold'] == 5
    assert a['minimum_complete_heldout_occurrence_rows_per_M_fold'] == 2
    assert a['thresholds_changed'] is False


def test_admission_gate_is_strictly_presealed_and_performance_blind():
    c = json.loads(CONTRACT.read_text())
    gate = c['presealed_admission_gate']
    assert gate['runs_before_model_pool_fitting'] is True
    assert gate['runs_before_pretruth_ecological_selection'] is True
    assert gate['runs_before_sealed_raster_extraction'] is True
    assert gate['runs_before_any_sealed_metric'] is True
    assert gate['require_all_12_taxa_x_3_M_in_every_part'] is True
    assert gate['require_all_6_parts_structurally_feasible'] is True
    assert gate['if_any_part_fails'] == 'terminate_v2_7_3_as_presealed_unavailable'
    assert gate['sealed_environmental_evidence_opened_if_gate_fails'] is False
    assert gate['model_pool_fitting_allowed_if_gate_fails'] is False
    assert gate['candidate_replacement_allowed_if_gate_fails'] is False

    allowed = set(gate['allowed_inputs'])
    assert {'fresh_occurrence_coordinates', 'M_membership', 'fold_assignment', 'row_counts'} <= allowed
    forbidden = set(gate['forbidden_inputs'])
    assert {
        'rank2_sealed_outcomes', 'environmental_raster_values', 'auc',
        'presence_rank', 'continuous_boyce_or_cbi', 'or10', 'aicc',
        'niche_overlap_schoener_d_pc12', 'centroid_distance',
        'breadth_log_sd_error', 'quantile_profile_error', 'candidate_scores',
        'selected_predictors', 'fitted_coefficients', 'process_knockout_outcomes'
    } <= forbidden
    assert allowed.isdisjoint(forbidden)


def test_scientific_runtime_and_claim_boundary_remain_frozen():
    c = json.loads(CONTRACT.read_text())
    r = c['scientific_runtime_if_admitted']
    assert r['deterministic_v2_7_2_scientific_procedure_inherited_unchanged'] is True
    assert r['M_grid_changed'] is False
    assert r['candidate_families_changed'] is False
    assert r['prediction_adequacy_guardrail_changed'] is False
    assert r['ecological_recovery_metrics_changed'] is False
    assert r['weighted_super_score_allowed'] is False
    assert r['final_fit_procedure_changed'] is False
    assert r['six_part_decision_rule_changed'] is False
    assert r['post_outcome_candidate_reselection_allowed'] is False
    assert r['post_outcome_threshold_tuning_allowed'] is False
    assert r['post_outcome_random_seed_change_allowed'] is False
    assert r['selective_part_reuse_allowed'] is False
    assert c['claim_boundary']['product_a_promoted'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_v273_execution_gate_is_closed_after_source_pin_before_feasibility_freeze():
    e = json.loads(EXECUTION.read_text())
    assert e['purpose'] == 'product_a_v2_7_3_presealed_structural_feasibility_execution_authorization'
    assert e['implementation_sha'] is None
    assert e['frozen_ref'] is None
    assert e['workflow_blob_sha'] is None
    assert e['module_blob_sha'] is None
    assert e['panel_blob_sha'] is None
    assert e['feasibility_contract_blob_sha'] is None
    assert e['source_pin_blob_sha'] is None
    assert e['evidence_partition_blob_sha'] is None
    assert e['source_acquisition_run_id'] == 32858840773
    assert e['run_all_6_parts'] is True
    assert e['require_full_12_taxa_x_3_M_denominator'] is True
    assert e['open_sealed_environmental_evidence'] is False
    assert e['model_pool_fitting_allowed'] is False
    assert e['rank2_sealed_confirmation_outcomes_allowed'] is False
    assert e['scientific_runtime_execution_allowed'] is False
    assert e['post_outcome_retuning_allowed'] is False
    assert e['candidate_reselection_allowed'] is False
    assert e['scientific_promotion_allowed'] is False
    assert e['product_b_unblocked'] is False
    assert e['one_shot'] is True
    assert e['execution_allowed'] is False
