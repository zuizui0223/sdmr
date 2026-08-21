from pathlib import Path
import json

import pandas as pd

from sdmr.v2_6_continuation_promotion import (
    apply_continuation_promotion,
    load_continuation_promotion_contract,
)

CONFIG = Path('configs/product_a_v2_6_continuation_promotion_contract.json')


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload) + '\n', encoding='utf-8')


def _sources(tmp_path: Path, *, empirical_supported: bool = True):
    kt = tmp_path / 'known'; kt.mkdir()
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


def test_contract_pins_exact_continuation_before_sealed_outcome():
    c = load_continuation_promotion_contract(CONFIG)
    assert c['contract_frozen_before_continuation_sealed_outcome'] is True
    assert c['new_postoutcome_scientific_thresholds'] is False
    source = c['independent_empirical_continuation_source']
    assert source['implementation_sha'] == 'da421c88717b193a1c1046c4d6920e841a4b7584'
    assert source['frozen_ref'] == 'frozen/product-a-v2-6-presealed-continuation-da421c88'
    assert source['workflow_file'] == 'product-a-v2-6-empirical-presealed-continuation.yml'
    assert source['requires_single_workflow_dispatch_run_for_frozen_source'] is True
    assert source['source_pretruth_artifacts_observed_before_continuation'] == 0
    assert source['source_sealed_audit_artifacts_observed_before_continuation'] == 0


def test_supported_continuation_promotes_a_but_does_not_unblock_b(tmp_path):
    kt, emp = _sources(tmp_path, empirical_supported=True)
    result = apply_continuation_promotion(
        contract_path=CONFIG,
        known_truth_dir=kt,
        empirical_continuation_dir=emp,
        output_dir=tmp_path / 'out',
    )
    assert result['decision'] == 'product_a_v2_6_promoted'
    assert result['product_a_v2_6_promoted'] is True
    assert result['product_b_empirical_use_unblocked'] is False


def test_negative_empirical_continuation_is_retained_without_threshold_relaxation(tmp_path):
    kt, emp = _sources(tmp_path, empirical_supported=False)
    result = apply_continuation_promotion(
        contract_path=CONFIG,
        known_truth_dir=kt,
        empirical_continuation_dir=emp,
        output_dir=tmp_path / 'out',
    )
    assert result['decision'] == 'product_a_v2_6_not_promoted'
    assert result['product_a_v2_6_promoted'] is False
    assert result['new_postoutcome_scientific_thresholds'] is False
    assert result['threshold_relaxation_after_outcome'] is False
