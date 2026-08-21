from pathlib import Path
import json

import pandas as pd

from sdmr.v2_6_continuation_v3_promotion import (
    apply_continuation_v3_promotion,
    load_continuation_v3_promotion_contract,
)

CONFIG = Path('configs/product_a_v2_6_continuation_v3_promotion_contract.json')


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload) + '\n', encoding='utf-8')


def _sources(tmp_path: Path, *, empirical_supported: bool = True):
    kt = tmp_path / 'kt'; kt.mkdir()
    _write_json(kt / 'contract.json', {
        'purpose': 'product_a_v2_6_predeclared_fresh_validation_decision',
        'decision': 'v2_6_supported',
        'all_process_and_boundary_products_written_before_truth_read': True,
        'process_support': True,
        'boundary_support': True,
        'validation_generating_truth_read_after_product_freeze': True,
        'candidate_selection_performed_during_validation': False,
        'scientific_threshold_tuning_performed_during_validation': False,
        'validation_truth_used_for_calibration': False,
        'product_b_unblocked': False,
        'scientific_promotion_allowed': False,
        'known_truth_result_directly_allows_empirical_promotion': False,
    })
    emp = tmp_path / 'emp'; emp.mkdir()
    decision = 'empirical_confirmation_supported' if empirical_supported else 'empirical_confirmation_not_supported'
    _write_json(emp / 'contract.json', {
        'purpose': 'product_a_v2_6_independent_empirical_confirmation_decision',
        'decision': decision,
        'n_parts': 6,
        'known_truth_thresholds_retuned_from_empirical_outcomes': False,
        'empirical_thresholds_retuned_after_sealed_read': False,
        'scientific_promotion_allowed': False,
        'product_b_unblocked': False,
    })
    pd.DataFrame([{
        'decision': decision,
        'all_empirical_evidence_available': True,
        'prediction_guardrail': empirical_supported,
        'ecological_support': empirical_supported,
        'process_reproducibility_support': empirical_supported,
    }]).to_csv(emp / 'decision.csv', index=False)
    return kt, emp


def test_contract_pins_exact_cont3_source_before_outcome():
    c = load_continuation_v3_promotion_contract(CONFIG)
    assert c['contract_frozen_before_continuation_v3_sealed_outcome'] is True
    assert c['new_postoutcome_scientific_thresholds'] is False
    src = c['independent_empirical_continuation_v3_source']
    assert src['implementation_sha'] == '5ce106bb955d0912b1c65ff8dd23a61a3e66aee1'
    assert src['frozen_ref'] == 'frozen/product-a-v2-6-continuation-v3-5ce106bb'
    assert src['workflow_file'] == 'product-a-v2-6-empirical-presealed-continuation-v2.yml'
    assert src['source_presealed_required_M_shards'] == 216
    assert src['transport_and_merge_repairs_only'] is True
    assert src['scientific_contract_changed'] is False
    assert [x['run_id'] for x in src['technical_predecessors']] == [32434610154, 32442269594]
    assert all(x['pretruth_artifacts'] == 0 for x in src['technical_predecessors'])
    assert all(x['sealed_environment_opened'] is False for x in src['technical_predecessors'])


def test_supported_sources_promote_product_a(tmp_path):
    kt, emp = _sources(tmp_path)
    result = apply_continuation_v3_promotion(
        contract_path=CONFIG,
        known_truth_dir=kt,
        empirical_continuation_dir=emp,
        output_dir=tmp_path / 'out',
    )
    assert result['decision'] == 'product_a_v2_6_promoted'
    assert result['product_a_v2_6_promoted'] is True
    assert result['product_b_empirical_use_unblocked'] is False


def test_negative_empirical_outcome_is_retained_without_threshold_relaxation(tmp_path):
    kt, emp = _sources(tmp_path, empirical_supported=False)
    result = apply_continuation_v3_promotion(
        contract_path=CONFIG,
        known_truth_dir=kt,
        empirical_continuation_dir=emp,
        output_dir=tmp_path / 'out',
    )
    assert result['decision'] == 'product_a_v2_6_not_promoted'
    assert result['product_a_v2_6_promoted'] is False
    assert result['threshold_relaxation_after_outcome'] is False
