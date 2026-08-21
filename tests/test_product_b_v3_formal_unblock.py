from pathlib import Path
import json

import pandas as pd

from sdmr.product_b_v3_formal_unblock import (
    apply_product_b_v3_unblock,
    load_product_b_v3_unblock_contract,
)

CONFIG = Path('configs/product_b_v3_formal_unblock_contract.json')


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload) + '\n', encoding='utf-8')


def _sources(tmp_path: Path, *, a_promoted=True, b_supported=True):
    a = tmp_path / 'a'; a.mkdir()
    a_decision = 'product_a_v2_6_promoted' if a_promoted else 'product_a_v2_6_not_promoted'
    _write_json(a / 'contract.json', {
        'purpose': 'product_a_v2_6_continuation_promotion_decision',
        'decision': a_decision,
        'product_a_v2_6_promoted': a_promoted,
        'product_b_empirical_use_unblocked': False,
        'new_postoutcome_scientific_thresholds': False,
        'threshold_relaxation_after_outcome': False,
    })
    pd.DataFrame([{'decision': a_decision, 'product_a_v2_6_promoted': a_promoted}]).to_csv(a / 'decision.csv', index=False)

    b = tmp_path / 'b'; b.mkdir()
    b_decision = 'product_b_v3_known_truth_supported' if b_supported else 'product_b_v3_known_truth_not_supported'
    _write_json(b / 'contract.json', {
        'purpose': 'product_b_v3_fresh_known_truth_decision',
        'decision': b_decision,
        'generating_process_truth_opened_after_pretruth_freeze': True,
        'process_losses_frozen_before_generating_truth_audit': True,
        'thresholds_retuned_after_truth': False,
        'real_empirical_data_read': False,
        'empirical_sealed_outcomes_read': False,
        'product_b_formally_unblocked': False,
        'scientific_empirical_product_b_claim_allowed': False,
        'product_a_representative_available_before_process_audit': True,
    })
    pd.DataFrame([{
        'decision': b_decision,
        'universal_process_recall': 1.0 if b_supported else 0.5,
        'mean_taxon_process_precision': 0.9 if b_supported else 0.6,
    }]).to_csv(b / 'decision.csv', index=False)
    return a, b


def test_v3_unblock_contract_pins_b_and_a_sources_before_outcomes():
    c = load_product_b_v3_unblock_contract(CONFIG)
    assert c['contract_frozen_before_product_a_continuation_sealed_outcome'] is True
    assert c['contract_frozen_before_product_b_v3_known_truth_outcome'] is True
    assert c['new_postoutcome_scientific_thresholds'] is False
    a = c['product_a_promotion_source']
    assert a['implementation_sha'] == '247857614d3844d44a390027c6f06fabb990a38d'
    assert a['frozen_ref'] == 'frozen/product-a-v2-6-continuation-promotion-24785761'
    b = c['product_b_v3_known_truth_source']
    assert b['implementation_sha'] == '06350e55541f3ae0d846985edb196b68c536e2ab'
    assert b['frozen_ref'] == 'frozen/product-b-v3-06350e55'
    assert b['fresh_evaluation_seeds'] == list(range(701, 713))


def test_a_promoted_and_b_supported_unblocks_v3(tmp_path):
    a, b = _sources(tmp_path)
    result = apply_product_b_v3_unblock(
        contract_path=CONFIG,
        product_a_promotion_dir=a,
        product_b_known_truth_dir=b,
        output_dir=tmp_path / 'out',
    )
    assert result['decision'] == 'product_b_v3_formally_unblocked'
    assert result['product_b_v3_formally_unblocked'] is True
    unblock = json.loads((tmp_path / 'out' / 'product_b_v3_formal_unblock_contract.json').read_text())
    assert unblock['empirical_product_b_execution_allowed'] is True


def test_b_failure_keeps_v3_blocked_without_revoking_a(tmp_path):
    a, b = _sources(tmp_path, b_supported=False)
    result = apply_product_b_v3_unblock(contract_path=CONFIG, product_a_promotion_dir=a, product_b_known_truth_dir=b, output_dir=tmp_path / 'out')
    assert result['product_a_v2_6_promoted'] is True
    assert result['product_b_v3_formally_unblocked'] is False


def test_a_failure_keeps_v3_blocked(tmp_path):
    a, b = _sources(tmp_path, a_promoted=False, b_supported=True)
    result = apply_product_b_v3_unblock(contract_path=CONFIG, product_a_promotion_dir=a, product_b_known_truth_dir=b, output_dir=tmp_path / 'out')
    assert result['product_a_v2_6_promoted'] is False
    assert result['product_b_v3_formally_unblocked'] is False
