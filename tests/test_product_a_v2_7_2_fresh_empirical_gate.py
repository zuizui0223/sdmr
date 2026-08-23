import json
from pathlib import Path

import pandas as pd

CANDIDATES = Path('configs/product_a_v2_7_1_fresh_taxon_candidates.csv')
PILOT = Path('configs/product_a_pilot_taxa_v1.csv')
V271 = Path('configs/product_a_v2_7_1_fresh_confirmation_taxa.csv')
V272 = Path('configs/product_a_v2_7_2_fresh_confirmation_taxa.csv')
SELECTION = Path('configs/product_a_v2_7_2_fresh_taxon_panel_selection_result.json')
CONTRACT = Path('configs/product_a_v2_7_2_fresh_confirmation_contract.json')
GATE = Path('configs/product_a_v2_7_2_fresh_empirical_source_gate.json')


def test_v272_panel_is_exactly_predeclared_rank2_and_disjoint():
    candidates = pd.read_csv(CANDIDATES)
    pilot = pd.read_csv(PILOT)
    v271 = pd.read_csv(V271)
    v272 = pd.read_csv(V272)
    expected = candidates.loc[candidates['candidate_rank'].astype(int).eq(2), ['scientific_name', 'validation_stratum']]
    assert len(expected) == 12
    assert len(v272) == 12
    assert set(zip(v272['scientific_name'], v272['validation_stratum'])) == set(zip(expected['scientific_name'], expected['validation_stratum']))
    assert set(v272['scientific_name']).isdisjoint(set(pilot['scientific_name']))
    assert set(v272['scientific_name']).isdisjoint(set(v271['scientific_name']))
    assert v272['validation_stratum'].nunique() == 12


def test_v272_panel_selection_does_not_use_ecological_or_model_outcomes():
    c = json.loads(SELECTION.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_taxon_panel_selection_result'
    assert c['successor_selection_rule']['rule'] == 'select_predeclared_rank2_in_every_stratum_after_rank1_was_consumed_by_v2_7_1_fresh_model_pool'
    assert c['successor_selection_rule']['post_known_truth_empirical_candidate_reordering_allowed'] is False
    assert c['historical_availability_screen']['n_candidates_eligible'] == 36
    assert c['independence']['disjoint_from_v2_7_1_fresh_rank1_panel'] is True
    barrier = c['selection_information_barrier']
    assert all(value is False for value in barrier.values())
    assert c['scientific_promotion_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_v272_empirical_scientific_contract_preserves_v271_decision_thresholds_and_adds_seed_identity():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_taxon_holdout_empirical_confirmation_contract'
    assert c['predeclared_before_any_v2_7_2_empirical_model_or_sealed_outcome'] is True
    assert c['predecessor_rule_continuity']['scientific_decision_thresholds_changed'] is False
    fixed = c['fixed_design']
    assert fixed['M_km'] == [150, 300, 500]
    assert fixed['sealed_fractions'] == [0.2, 0.3]
    assert fixed['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert fixed['procedure_library']['model_random_state'] == 0
    assert fixed['procedure_library']['selection_process_numpy_seed'] == 0
    decision = c['decision_rule']
    assert decision['ecological_noninferiority']['minimum_parts'] == 4
    assert decision['ecological_noninferiority']['strict_improvement_minimum_parts'] == 3
    assert decision['prediction_guardrail']['mean_presence_rank_deficit_vs_auc_comparator_min'] == -0.01
    assert decision['process_reproducibility']['modal_status_fraction_min'] == 2 / 3
    assert decision['post_outcome_threshold_tuning_allowed'] is False
    assert decision['post_outcome_random_seed_change_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_v272_source_gate_is_fail_closed_until_new_raw_sources_and_runtime_are_pinned():
    c = json.loads(GATE.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_empirical_source_gate'
    assert c['gate_state'] == 'waiting_for_new_rank2_raw_sources_and_exact_empirical_runtime'
    assert c['execution_allowed'] is False
    assert c['known_truth_endpoint']['determinism_passed'] is True
    assert c['known_truth_endpoint']['scientific_nonregression_supported'] is True
    assert c['freshness_design']['predeclared_candidate_rank'] == 2
    assert c['historical_catalog_transport']['v2_7_1_rank1_focal_artifact_may_be_reused'] is False
    assert c['historical_catalog_transport']['v2_7_1_target_group_artifact_may_be_reused'] is False
    assert c['historical_catalog_transport']['v2_7_1_split_parts_may_be_reused'] is False
    assert c['historical_catalog_transport']['v2_7_1_sealed_rows_may_be_opened'] is False
    required = c['required_before_execution']
    for key in (
        'focal_file_sha256', 'focal_query_sha256', 'target_group_file_sha256',
        'target_group_query_sha256', 'raw_source_receipt_artifact_id',
        'raw_source_receipt_artifact_digest', 'empirical_runtime_implementation_sha',
        'empirical_runtime_frozen_ref', 'workflow_file',
    ):
        assert required[key] is None
    assert c['scientific_constraints']['post_outcome_threshold_tuning_allowed'] is False
    assert c['scientific_constraints']['post_outcome_random_seed_change_allowed'] is False
    assert c['scientific_constraints']['product_b_unblocked_before_separate_promotion_decision'] is False
