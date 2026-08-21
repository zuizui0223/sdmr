import hashlib
import json
from pathlib import Path

import pandas as pd

PANEL = Path('configs/product_a_v2_7_1_fresh_confirmation_taxa.csv')
PILOT = Path('configs/product_a_pilot_taxa_v1.csv')
SELECTION = Path('configs/product_a_v2_7_1_fresh_taxon_panel_selection_result.json')
CONTRACT = Path('configs/product_a_v2_7_1_fresh_confirmation_contract.json')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fresh_confirmation_panel_is_exactly_12_and_disjoint_from_development_panel():
    panel = pd.read_csv(PANEL)
    pilot = pd.read_csv(PILOT)
    assert list(panel.columns) == ['scientific_name', 'pilot_stratum', 'reason']
    assert len(panel) == 12
    assert panel['scientific_name'].nunique() == 12
    assert panel['pilot_stratum'].nunique() == 12
    assert set(panel['scientific_name']).isdisjoint(set(pilot['scientific_name']))
    assert sha256(PANEL) == '40364e45ce523abe346a32bf7fbbfa70f8aba152a4d9a89f845a58c05b64e554'


def test_selection_result_records_outcome_independent_taxon_holdout():
    c = json.loads(SELECTION.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_taxon_panel_selection_result'
    assert c['eligibility_run_id'] == 32474864368
    assert c['eligibility_artifact']['artifact_id'] == 9444172302
    assert c['candidate_pool']['n_candidates'] == 36
    assert c['candidate_pool']['n_eligible'] == 36
    assert c['repository_panel']['sha256'] == sha256(PANEL)
    assert len(c['selected_taxa']) == 12
    assert set(c['selected_taxa']) == set(pd.read_csv(PANEL)['scientific_name'])
    assert c['independence']['axis'] == 'taxon_holdout_not_temporal'
    assert c['independence']['disjoint_from_product_a_pilot_12'] is True
    assert c['independence']['temporal_independence_claim_allowed'] is False
    barrier = c['selection_information_barrier']
    for key in (
        'environmental_values_used',
        'AUC_used',
        'CBI_used',
        'OR10_used',
        'AICc_used',
        'candidate_model_scores_used',
        'niche_recovery_outcomes_used',
        'sealed_confirmation_outcomes_used',
        'post_count_threshold_relaxation',
        'post_count_candidate_reordering',
    ):
        assert barrier[key] is False
    assert c['scientific_promotion_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_fresh_confirmation_reuses_v271_method_without_new_threshold_tuning():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_taxon_holdout_empirical_confirmation_contract'
    assert c['predeclared_before_any_fresh_taxon_model_or_sealed_outcome'] is True
    assert c['independence_axis'] == 'taxon_holdout_not_temporal'
    assert c['temporal_independence_claim_allowed'] is False
    assert c['development_70_of_72_used_to_tune_thresholds'] is False
    assert c['fresh_taxon_panel']['sha256'] == sha256(PANEL)
    assert c['fixed_design']['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert c['fixed_design']['sealed_fractions'] == [0.2, 0.3]
    assert c['fixed_design']['M_km'] == [150, 300, 500]

    partition = c['v2_7_1_evidence_balanced_partition']
    assert partition['spatial_microblocks'] == 12
    assert partition['outer_folds'] == 4
    assert partition['assignment_attempts'] == 32
    assert partition['minimum_evaluation_occurrences_per_fold'] == 2
    assert partition['minimum_evaluation_background_rows_per_M_fold'] == 5
    assert partition['minimum_training_background_rows_per_M_fold'] == 5
    assert partition['environmental_values_used_for_partition_assignment'] is False
    assert partition['candidate_scores_used_for_partition_assignment'] is False
    assert partition['sealed_rows_used_for_partition_assignment'] is False
    assert partition['abstain_if_no_feasible_assignment'] is True

    audit = c['v2_7_1_partition_aware_audit_space']
    assert audit['minimum_predictor_coverage'] == 0.95
    assert audit['minimum_joint_coverage'] == 0.80
    assert audit['minimum_processes'] == 4
    assert audit['thresholds_unchanged_from_v2_7_development'] is True

    target = c['empirical_target']
    assert target['ordinary_prediction_metrics_are_guardrails_not_tuning_target'] is True
    assert target['recovery_metrics_must_remain_separate'] is True
    assert target['weighted_super_score_allowed'] is False
    assert target['metrics'] == [
        'niche_overlap_schoener_d_pc12',
        'centroid_distance',
        'breadth_log_sd_error',
        'quantile_profile_error',
    ]

    decision = c['decision_rule']
    assert decision['all_6_parts_required'] is True
    assert decision['all_12_taxa_required_in_every_part'] is True
    assert decision['all_3_M_specs_required_in_every_part'] is True
    assert decision['structural_or_audit_abstention_makes_part_unavailable_not_pass'] is True
    assert decision['prediction_guardrail']['mean_presence_rank_deficit_vs_auc_comparator_min'] == -0.01
    assert decision['ecological_noninferiority']['minimum_parts'] == 4
    assert decision['ecological_noninferiority']['strict_improvement_minimum_parts'] == 3
    assert decision['process_reproducibility']['modal_status_fraction_min'] == 2 / 3
    assert decision['post_outcome_candidate_reselection_allowed'] is False
    assert decision['post_outcome_threshold_tuning_allowed'] is False
    assert decision['scientific_promotion_allowed_by_this_decision'] is False
    assert decision['product_b_remains_blocked_until_separate_promotion_decision'] is True
