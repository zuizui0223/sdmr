import json
from pathlib import Path

import pandas as pd


CONTRACT = Path('configs/product_a_v2_8_geometry_only_validation_calibration_contract.json')
EXECUTION = Path('configs/product_a_v2_8_geometry_only_validation_calibration_execution.json')
REGISTRY = Path('configs/product_a_v2_7_1_fresh_taxon_candidates.csv')


def test_v28_calibration_uses_all_36_consumed_taxa_only_as_geometry_corpus():
    c = json.loads(CONTRACT.read_text())
    r = pd.read_csv(REGISTRY)
    assert c['purpose'] == 'product_a_v2_8_geometry_only_validation_design_calibration'
    assert c['issue'] == 133
    assert c['predeclared_before_v2_8_geometry_calibration_execution'] is True
    assert len(r) == 36
    assert r['validation_stratum'].nunique() == 12
    assert sorted(r['candidate_rank'].unique().tolist()) == [1, 2, 3]
    corpus = c['calibration_corpus']
    assert corpus['n_taxa'] == 36
    assert corpus['n_validation_strata'] == 12
    assert corpus['candidate_ranks'] == [1, 2, 3]
    assert corpus['role'] == 'geometry_only_protocol_calibration'
    assert corpus['future_scientific_confirmation_reuse_allowed'] is False


def test_v28_calibration_is_environment_and_model_blind():
    c = json.loads(CONTRACT.read_text())
    allowed = set(c['frozen_inputs_allowed'])
    forbidden = set(c['forbidden_inputs'])
    assert {'occurrence_coordinates', 'target_group_coordinates', 'M_membership', 'row_counts'} <= allowed
    assert {'CHELSA_values', 'auc', 'continuous_boyce_or_cbi', 'or10', 'aicc', 'candidate_scores', 'sealed_ecological_outcomes'} <= forbidden
    assert allowed.isdisjoint(forbidden)


def test_v28_inherits_structural_partition_without_relaxation():
    c = json.loads(CONTRACT.read_text())
    p = c['inherited_partition']
    assert p['M_km'] == [150, 300, 500]
    assert p['M_is_sensitivity_not_optimization'] is True
    assert p['outer_folds'] == 4
    assert p['spatial_microblocks'] == 12
    assert p['assignment_attempts'] == 32
    assert p['minimum_evaluation_occurrences_per_fold'] == 2
    assert p['minimum_evaluation_background_rows_per_M_fold'] == 5
    assert p['minimum_training_background_rows_per_M_fold'] == 5
    assert p['partition_algorithm_changed'] is False
    assert p['row_count_thresholds_changed'] is False
    assert p['assignment_attempts_changed'] is False


def test_v28_fraction_is_validation_design_axis_and_future_rule_is_global():
    c = json.loads(CONTRACT.read_text())
    a = c['calibration_axis']
    assert a['sealed_fraction_grid'] == [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
    assert a['split_seeds'] == [2026082201, 2026082202, 2026082203, 2026082204, 2026082205]
    assert a['sealed_fraction_is_validation_design_parameter_not_scientific_tuning_target'] is True
    assert a['candidate_or_threshold_adaptation_within_a_fraction'] is False
    rule = c['selection_rule_for_future_confirmation']
    assert rule['future_fraction_fixed_globally_not_per_taxon'] is True
    assert rule['future_fraction_selected_before_future_confirmation_taxa_or_ecological_outcomes'] is True
    assert rule['if_none_pass'].startswith('do_not_launch_fresh_scientific_confirmation')


def test_v28_claim_and_execution_gates_are_closed():
    c = json.loads(CONTRACT.read_text())
    assert c['claim_boundary']['scientific_confirmation_performed'] is False
    assert c['claim_boundary']['product_a_promoted'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False
    assert c['claim_boundary']['geometry_calibration_result_is_ecological_support'] is False
    assert c['claim_boundary']['post_outcome_rescue_of_consumed_rank1_rank2_rank3_taxa'] is False
    e = json.loads(EXECUTION.read_text())
    assert e['geometry_only'] is True
    for key in ('environmental_values_allowed', 'candidate_model_fitting_allowed', 'sealed_ecological_outcomes_allowed', 'scientific_confirmation_allowed', 'scientific_promotion_allowed', 'product_b_unblocked', 'execution_allowed'):
        assert e[key] is False
    assert e['one_shot'] is True
