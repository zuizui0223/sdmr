import json
from pathlib import Path

import pandas as pd

from sdmr.v2_8_3_fresh_aggregate import _decision_frame
from sdmr.v2_8_3_fresh_contract import (
    EXPECTED_SEEDS,
    load_v2_8_3_fresh_confirmation_contract,
    load_v2_8_3_source_receipt,
)


CONTRACT = Path('configs/product_a_v2_8_3_fresh_confirmation_contract.json')
EXECUTION = Path('configs/product_a_v2_8_3_scientific_execution.json')
SOURCE_RECEIPT = Path('configs/product_a_v2_8_2_fresh_raw_source_receipt.json')
WORKFLOW = Path('.github/workflows/product-a-v2-8-3-fresh-confirmation.yml')


EXPECTED_AUTHORIZED_BLOBS = {
    '.github/workflows/product-a-v2-8-3-fresh-confirmation.yml': '19b51b7596a79bf5618b0cf3fd41c5aa86709bd0',
    'configs/product_a_v2_8_3_fresh_confirmation_contract.json': '1928de6d8f1289117415047c7a8d1ee894ca6bbe',
    'configs/product_a_v2_8_3_scientific_execution.json': 'd79268b5ed2be4308e14217f09edcc9f67f0bc57',
    'configs/product_a_v2_8_2_fresh_raw_source_receipt.json': 'ed4d90a84db354e06a4a214f6a3a184c7e36ea7f',
    'configs/product_a_v2_8_2_fresh_confirmation_taxa.csv': '5c00886724405edeb13dae4f029ec19573ad180f',
    'configs/product_a_empirical_process_registry_v1.csv': '469a1ced27ff47fe6b731c26cc3b9b0f4a56d58a',
    'configs/product_a_buffer_specs_v1.csv': '608ce63f4007406e2873e25267a1234933f0487e',
    'configs/chelsa_v2_1_plant_candidates.csv': 'fd680b076df1fba2ce8c3c5c6a64ae151885c0fa',
    'src/sdmr/v2_8_3_fresh_contract.py': 'fc98f7171e02cd89a34124b537f090e341dd6ed3',
    'src/sdmr/v2_8_3_fresh_runtime.py': '363ab04de48b6ea7c7339c57449bb4695e4e0f05',
    'src/sdmr/v2_8_3_presealed_transport.py': 'fecdd061b293973bd2e4ac4c9caddc80fcd943e7',
    'src/sdmr/v2_8_3_fresh_aggregate.py': 'af0e6a9218495e4410b66a61b79db0e29f8d2a1c',
    'src/sdmr/v2_7_2_deterministic_procedure_library.py': 'e8739f14d750e1533c34d417e84969bbbd9a8b35',
    'src/sdmr/v2_7_2_fresh_contract.py': '72e46e863ac97b1af939300a9fdd3f5c66f4459c',
    'src/sdmr/v2_7_2_fresh_materialize.py': 'acfd3868e1cfd51467e961c31c4c6a4bd9e2391c',
    'src/sdmr/v2_7_2_fresh_model_pool_shard.py': '25c5375fbc06b018575bf12b9f71615d6767af2f',
    'src/sdmr/v2_7_2_fresh_model_pool_shard_aggregate.py': '889940a08d49be3ed3d3fbd59d081fa6ff1584e9',
    'src/sdmr/v2_7_2_fresh_pretruth.py': '8005bb080ee6106fca54917504bd4ccad820afa8',
    'src/sdmr/v2_7_2_fresh_final_fit.py': 'ab19eb6e21f06603557ed86c5b443814a9064b42',
    'src/sdmr/v2_7_2_fresh_sealed_audit.py': '9da77e578cd9d5f523340c19eb2df844600f588a',
    'src/sdmr/v2_7_3_presealed_feasibility.py': 'cbe3d23e5a06d35167c4a5ff68d50a2ba4581c8d',
}


def test_v283_contract_is_predeclared_single_fraction_deterministic_and_fail_closed():
    c = load_v2_8_3_fresh_confirmation_contract(CONTRACT)
    load_v2_8_3_source_receipt(SOURCE_RECEIPT)
    assert c['tracks_issue'] == 158
    assert c['source_receipt']['blob_sha'] == 'ed4d90a84db354e06a4a214f6a3a184c7e36ea7f'
    assert c['fresh_taxon_panel']['sha256'] == '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1'
    assert c['fixed_design']['sealed_fractions'] == [0.25]
    assert c['fixed_design']['split_seeds'] == list(EXPECTED_SEEDS)
    assert c['fixed_design']['n_confirmation_parts'] == 3
    assert c['fixed_design']['procedure_library']['model_random_state'] == 0
    assert c['fixed_design']['procedure_library']['selection_process_numpy_seed'] == 0
    assert c['structural_transportability']['n_expected_taxon_M_part_cells'] == 108
    assert c['decision_rule']['ecological_noninferiority']['minimum_parts'] == 2
    assert c['decision_rule']['ecological_noninferiority']['strict_improvement_minimum_parts'] == 2
    assert c['decision_rule']['prediction_guardrail']['mean_presence_rank_deficit_vs_auc_comparator_min'] == -0.01
    assert c['scientific_promotion_run'] is False
    assert c['product_b_unblocked'] is False


def test_v283_execution_authorization_is_closed_or_exactly_pinned():
    a = json.loads(EXECUTION.read_text())
    assert a['purpose'] == 'product_a_v2_8_3_fresh_scientific_execution_authorization'
    assert a['one_shot'] is True
    assert a['source_receipt_blob_sha'] == 'ed4d90a84db354e06a4a214f6a3a184c7e36ea7f'
    assert a['selected_panel_sha256'] == '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1'
    assert a['selected_global_sealed_fraction'] == 0.25
    assert a['split_seeds'] == list(EXPECTED_SEEDS)

    phase_keys = (
        'structural_transport_allowed',
        'environmental_values_allowed_after_structural_admission',
        'candidate_model_fitting_allowed_after_structural_admission',
        'candidate_scores_allowed_only_inside_frozen_model_pool_procedure',
        'sealed_ecological_outcomes_allowed_after_pretruth_and_final_fit',
        'scientific_confirmation_allowed',
    )
    immutable_false_keys = (
        'post_outcome_candidate_reselection_allowed',
        'post_outcome_threshold_tuning_allowed',
        'post_outcome_random_seed_change_allowed',
        'post_outcome_fraction_change_allowed',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    )
    for key in immutable_false_keys:
        assert a[key] is False

    if a['execution_allowed'] is False:
        assert a['implementation_sha'] is None and a['frozen_ref'] is None
        assert a['frozen_blobs'] == {}
        for key in phase_keys:
            assert a[key] is False
    else:
        assert a['execution_allowed'] is True
        assert a['implementation_sha'] == '8095dd814f2c20babe2865f5a5a0835dde047727'
        assert a['frozen_ref'] == 'frozen/product-a-v2-8-3-fresh-confirmation-8095dd81'
        assert a['frozen_blobs'] == EXPECTED_AUTHORIZED_BLOBS
        for key in phase_keys:
            assert a[key] is True


def test_v283_workflow_freezes_structural_gate_before_any_environmental_model_stage():
    text = WORKFLOW.read_text()
    assert 'product-a-v2-8-3-fresh-confirmation' in text
    assert 'authorization_commit_sha' in text and 'authorization_blob_sha' in text
    assert 'structural-part:' in text and 'structural-aggregate:' in text
    assert 'materialize:\n    needs: structural-aggregate' in text
    assert 'Freeze all 108 structural cells before any environmental extraction' in text
    assert '--sealed-fraction' not in text
    assert '0.20' not in text and '0.30' not in text
    assert "'scientific_promotion_allowed'," in text
    assert "'product_b_unblocked'," in text
    assert 'v283-final-part-${{ matrix.seed }}' in text


def _parts(*, last_available=True, nondominated=(True, True, False), strict=(True, True, False)):
    rows = []
    for i, seed in enumerate(EXPECTED_SEEDS):
        available = bool(last_available or i < 2)
        rows.append({
            'part_id': f'seed{seed}_sealed0.25',
            'seed': seed,
            'sealed_fraction': 0.25,
            'all_12_taxa': available,
            'all_3_M_specs': available,
            'mean_presence_rank_delta_vs_auc': 0.0 if available else float('nan'),
            'ecologically_nondominated_vs_auc': bool(nondominated[i]) if available else False,
            'strict_ecological_improvement_vs_auc': bool(strict[i]) if available else False,
            'part_available': available,
        })
    return pd.DataFrame(rows)


def _structural(*, last_available=True):
    return pd.DataFrame([
        {
            'seed': seed,
            'sealed_fraction': 0.25,
            'part_id': f'seed{seed}_sealed0.25',
            'structurally_auditable': bool(last_available or i < 2),
        }
        for i, seed in enumerate(EXPECTED_SEEDS)
    ])


def _process():
    taxa = [f'taxon_{i:02d}' for i in range(12)]
    domains = ['thermal', 'water', 'seasonality_phenology', 'energy_productivity', 'snow', 'wind']
    return pd.DataFrame([
        {
            'part_id': f'seed{seed}_sealed0.25',
            'taxon': taxon,
            'process_domain': domain,
            'status': 'stable',
        }
        for seed in EXPECTED_SEEDS for taxon in taxa for domain in domains
    ])


def test_v283_three_part_decision_uses_predeclared_two_of_three_ecological_thresholds():
    decision, bounds = _decision_frame(
        part_summary=_parts(), process_status=_process(), structural_parts=_structural()
    )
    row = decision.iloc[0]
    assert row['decision'] == 'empirical_confirmation_supported'
    assert bool(row['prediction_guardrail'])
    assert bool(row['ecological_support'])
    assert bool(row['process_reproducibility_support'])
    assert int(row['n_ecologically_nondominated_parts']) == 2
    assert int(row['n_strict_ecological_improvement_parts']) == 2
    assert not bounds['applicable_due_to_structural_unavailability'].any()


def test_v283_primary_fails_closed_but_structural_bounds_preserve_conditional_information():
    decision, bounds = _decision_frame(
        part_summary=_parts(last_available=False, nondominated=(True, True, False), strict=(True, True, False)),
        process_status=_process(),
        structural_parts=_structural(last_available=False),
    )
    row = decision.iloc[0]
    assert row['decision'] == 'empirical_confirmation_unavailable'
    assert int(row['n_structurally_unavailable_parts']) == 1
    assert int(row['n_conditional_ecological_parts_available']) == 2
    assert not bool(row['all_primary_scientific_evidence_available'])
    assert not bool(row['conditional_results_can_override_primary_decision'])
    assert bounds['applicable_due_to_structural_unavailability'].all()
    assert bounds['bounds_interpretable_without_additional_missing_scientific_evidence'].all()
    assert set(bounds['lower_bound']) == {2.0 / 3.0}
    assert set(bounds['upper_bound']) == {1.0}
    assert not bounds['can_override_primary_decision'].any()
