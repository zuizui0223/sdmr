import json
from pathlib import Path


BOUNDARY = Path('configs/product_a_v2_8_4_sealed_boundary_contract.json')
WORKFLOW = Path('.github/workflows/product-a-v2-8-4-sealed-reusable.yml')


def test_sealed_implementation_preserves_frozen_scientific_boundary():
    boundary = json.loads(BOUNDARY.read_text())
    inv = boundary['scientific_invariants']
    assert inv['sealed_fraction'] == 0.25
    assert inv['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert inv['M_km'] == [150, 300, 500]
    assert inv['model_random_state'] == 0
    assert inv['selection_process_numpy_seed'] == 0
    assert inv['primary_denominator'] == 3
    assert inv['prediction_guardrail_mean_presence_rank_delta_vs_auc_min'] == -0.01
    assert inv['ecological_nondomination_minimum_parts'] == 2
    assert inv['strict_ecological_improvement_minimum_parts'] == 2
    assert inv['process_modal_status_fraction_min'] == 2.0 / 3.0
    for key in (
        'candidate_predictor_universe_changed', 'candidate_library_changed',
        'thresholds_changed', 'taxa_changed', 'M_changed', 'seeds_changed',
        'fraction_changed', 'denominator_changed', 'decision_rule_changed',
        'scientific_promotion_allowed', 'product_b_unblocked',
    ):
        assert inv[key] is False


def test_reusable_workflow_has_no_scientific_retuning_surface():
    text = WORKFLOW.read_text()
    forbidden = (
        '--sealed-fraction', '--threshold', '--seed ', '--M ',
        'candidate-pruning', 'early-stopping', 'scientific_promotion_allowed: true',
        'product_b_unblocked: true',
    )
    for token in forbidden:
        assert token not in text
    assert "SOURCE_RUN_ID: '33036252432'" in text
    assert 'configs/product_a_v2_8_3_fresh_confirmation_contract.json' in text
    assert 'configs/product_a_v2_8_2_fresh_confirmation_taxa.csv' in text
    assert 'configs/chelsa_v2_1_plant_candidates.csv' in text
