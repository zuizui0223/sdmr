import json
from pathlib import Path

import pandas as pd

CANDIDATES = Path('configs/product_a_v2_7_1_fresh_taxon_candidates.csv')
CONTRACT = Path('configs/product_a_v2_7_1_fresh_taxon_eligibility_contract.json')
PILOT = Path('configs/product_a_pilot_taxa_v1.csv')


def test_fresh_taxon_candidate_pool_is_predeclared_complete_and_disjoint():
    candidates = pd.read_csv(CANDIDATES)
    pilot = pd.read_csv(PILOT)

    assert list(candidates.columns) == [
        'scientific_name',
        'validation_stratum',
        'candidate_rank',
        'selection_basis',
    ]
    assert len(candidates) == 36
    assert candidates['scientific_name'].nunique() == 36
    assert candidates['validation_stratum'].nunique() == 12
    assert set(candidates['scientific_name']).isdisjoint(set(pilot['scientific_name']))

    grouped = candidates.groupby('validation_stratum', sort=True)
    assert all(len(frame) == 3 for _, frame in grouped)
    assert all(set(frame['candidate_rank'].astype(int)) == {1, 2, 3} for _, frame in grouped)


def test_fresh_taxon_eligibility_contract_is_outcome_independent_and_fail_closed():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_taxon_panel_eligibility_contract'
    assert c['freshness_basis'] == 'new_taxa_not_used_as_focal_development_taxa'
    assert c['historical_snapshot']['snapshot_date'] == '2026-08-01'
    assert c['historical_snapshot']['role'] == 'availability_only_for_predeclared_new_taxon_candidates'
    assert c['historical_snapshot']['candidate_taxa_were_focal_development_taxa'] is False
    assert c['historical_snapshot']['reuse_of_current_six_focal_split_parts'] is False

    assert c['thresholds'] == {
        'minimum_occurrences': 80,
        'minimum_unique_0_05_degree_cells': 50,
    }
    assert c['selection_rule']['required_strata'] == 12
    assert c['selection_rule']['required_candidates_per_stratum'] == 3
    assert c['selection_rule']['select_exactly_one_taxon_per_stratum'] is True
    assert c['selection_rule']['within_stratum_rule'] == (
        'lowest_predeclared_candidate_rank_meeting_both_eligibility_thresholds'
    )
    assert c['selection_rule']['if_no_candidate_is_eligible'] == 'panel_unavailable_fail_closed'
    assert c['selection_rule']['post_eligibility_candidate_reordering_allowed'] is False
    assert c['selection_rule']['threshold_relaxation_after_counts_are_seen_allowed'] is False

    allowed = set(c['eligibility_inputs_allowed'])
    assert allowed == {
        'candidate_scientific_name',
        'validation_stratum',
        'candidate_rank',
        'raw_occurrence_row_count',
        'unique_0_05_degree_cell_count',
    }
    forbidden = set(c['eligibility_inputs_forbidden'])
    for field in (
        'CHELSA_environmental_values',
        'candidate_model_scores',
        'AUC',
        'CBI',
        'OR10',
        'AICc',
        'niche_recovery_metrics',
        'process_knockout_outcomes',
        'sealed_confirmation_outcomes',
    ):
        assert field in forbidden

    barrier = c['information_barrier']
    assert barrier['environmental_values_read'] is False
    assert barrier['candidate_model_fitting_allowed'] is False
    assert barrier['scientific_promotion_allowed'] is False
    assert barrier['product_b_unblocked'] is False
    assert barrier['selected_panel_may_only_become_confirmation_evidence_after_separate_source_and_decision_gate'] is True
