from pathlib import Path
import json

from sdmr.product_b_v4_known_truth_contract import load_product_b_v4_known_truth_contract

EXECUTION = Path('configs/product_b_v4_execution_preoutcome_contract.json')
SCIENTIFIC = Path('configs/product_b_v4_known_truth_contract.json')


def test_v4_execution_source_is_pinned_before_fresh_outcome():
    e = json.loads(EXECUTION.read_text())
    s = load_product_b_v4_known_truth_contract(SCIENTIFIC)
    assert e['purpose'] == 'product_b_v4_known_truth_execution_preoutcome_contract'
    assert e['contract_frozen_before_product_b_v4_known_truth_outcome'] is True
    assert e['new_postoutcome_scientific_thresholds'] is False
    src = e['product_b_v4_source']
    assert src['implementation_sha'] == '7873c341f3ef05ce51293ac73693ba9729f93d8f'
    assert src['frozen_ref'] == 'frozen/product-b-v4-7873c341'
    assert src['workflow_file'] == 'product-b-v4-known-truth.yml'
    assert src['artifact_name'] == 'product-b-v4-fresh-known-truth-decision'
    assert src['requires_single_workflow_dispatch_run_for_frozen_source'] is True
    assert [x['seed'] for x in s['product_b_evaluation_taxa']] == list(range(src['fresh_seed_minimum'], src['fresh_seed_maximum'] + 1))
    v3 = e['predecessor_v3_negative_evidence']
    assert v3['run_id'] == 32441530888
    assert v3['decision'] == 'product_b_v3_known_truth_not_supported'
    assert v3['thresholds_retuned_after_v3'] is False
    ident = e['v4_scientific_identity']
    assert ident['model_refit_after_process_intervention'] is False
    assert ident['predictor_reselection_after_process_intervention'] is False
    assert ident['weighted_super_score'] is False
    assert e['information_order']['product_a_representative_frozen_before_product_b_process_intervention'] is True
    assert e['information_order']['process_core_frozen_before_generating_truth_read'] is True
    assert e['information_order']['v3_truth_not_used_to_score_v4'] is True
    assert e['claim_boundary']['empirical_product_b_execution_allowed'] is False
    assert e['claim_boundary']['formal_product_b_unblock_requires_separate_post_product_a_promotion_gate'] is True
