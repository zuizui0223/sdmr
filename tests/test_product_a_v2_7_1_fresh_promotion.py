import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_7_1_fresh_promotion import apply_fresh_promotion, load_fresh_promotion_contract

CONTRACT = Path('configs/product_a_v2_7_1_fresh_promotion_contract.json')


def _known_truth(root: Path, *, supported: bool = True) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        'purpose': 'product_a_v2_6_predeclared_fresh_validation_decision',
        'decision': 'v2_6_supported' if supported else 'v2_6_not_supported',
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
    }
    (root / 'contract.json').write_text(json.dumps(payload) + '\n')


def _fresh(root: Path, decision: str, *, source_kind: str = 'primary') -> None:
    root.mkdir(parents=True, exist_ok=True)
    supported = decision == 'empirical_confirmation_supported'
    contract = {
        'purpose': 'product_a_v2_7_1_fresh_taxon_holdout_empirical_confirmation_decision',
        'n_parts': 6,
        'n_available_parts': 6 if supported else (5 if decision == 'empirical_confirmation_unavailable' else 6),
        'decision': decision,
        'scientific_promotion_allowed': False,
        'product_b_unblocked': False,
        'development_thresholds_retuned_from_fresh_outcomes': False,
        'fresh_thresholds_retuned_after_sealed_read': False,
        'post_outcome_candidate_reselection_performed': False,
        'independence_axis': 'taxon_holdout_not_temporal',
        'temporal_independence_claim_allowed': False,
    }
    (root / 'contract.json').write_text(json.dumps(contract) + '\n')
    pd.DataFrame([{
        'decision': decision,
        'all_empirical_evidence_available': supported,
        'prediction_guardrail': supported,
        'ecological_support': supported,
        'process_reproducibility_support': supported,
        'n_parts': 6,
    }]).to_csv(root / 'decision.csv', index=False)
    if source_kind == 'primary':
        receipt = {
            'purpose': 'product_a_v2_7_1_fresh_confirmation_execution_receipt',
            'workflow_run_id': 32552745281,
            'implementation_sha': '1f158006c0b5dbdd93af70632464727405ababfe',
            'frozen_ref': 'frozen/product-a-v2-7-1-fresh-confirmation-1f158006',
            'decision': decision,
            'scientific_promotion_allowed': False,
            'product_b_unblocked': False,
            'post_outcome_retuning_allowed': False,
        }
        (root / 'execution_receipt.json').write_text(json.dumps(receipt) + '\n')
    elif source_kind == 'technical_continuation':
        receipt = {
            'purpose': 'product_a_v2_7_1_fresh_confirmation_continuation_execution_receipt',
            'workflow_run_id': 999999,
            'implementation_sha': '08edc61eaee19461cee440e8e8cfceb769e7f3f6',
            'frozen_ref': 'frozen/product-a-v2-7-1-fresh-confirmation-continuation-08edc61e',
            'primary_run_id': 32552745281,
            'decision': decision,
            'reran_all_six_sealed_audits': True,
            'scientific_thresholds_changed': False,
            'candidate_reselection_performed': False,
            'scientific_promotion_allowed': False,
            'product_b_unblocked': False,
        }
        (root / 'continuation_execution_receipt.json').write_text(json.dumps(receipt) + '\n')
    else:
        raise ValueError(source_kind)


def test_preoutcome_promotion_contract_is_claim_bounded_and_product_b_separate():
    c = load_fresh_promotion_contract(CONTRACT)
    assert c['contract_frozen_before_fresh_sealed_outcome'] is True
    assert c['new_postoutcome_scientific_thresholds'] is False
    assert c['fresh_taxon_holdout_source']['run_id'] == 32552745281
    assert c['fresh_taxon_holdout_source']['implementation_sha'] == '1f158006c0b5dbdd93af70632464727405ababfe'
    assert c['fresh_taxon_holdout_source']['sealed_audit_artifacts_observed_before_contract'] == 0
    assert c['fresh_taxon_holdout_source']['decision_artifacts_observed_before_contract'] == 0
    continuation = c['technical_continuation_source']
    assert continuation['implementation_sha'] == '08edc61eaee19461cee440e8e8cfceb769e7f3f6'
    assert continuation['frozen_ref'] == 'frozen/product-a-v2-7-1-fresh-confirmation-continuation-08edc61e'
    selection = c['fresh_decision_source_selection']
    assert selection['primary_decision_preferred_when_present'] is True
    assert selection['continuation_allowed_only_when_primary_completed_non_success_without_decision'] is True
    assert selection['source_selection_may_depend_on_scientific_decision_value'] is False
    assert selection['source_selection_may_depend_on_prediction_or_recovery_metrics'] is False
    assert selection['multiple_admissible_decision_sources_forbidden'] is True
    assert c['state_mapping'] == {
        'empirical_confirmation_supported': 'product_a_v2_7_1_promoted',
        'empirical_confirmation_not_supported': 'product_a_v2_7_1_not_promoted',
        'empirical_confirmation_unavailable': 'product_a_v2_7_1_not_promoted',
    }
    identity = c['promoted_product_identity']
    assert identity['target'] == 'realized_environmental_niche_recovery_and_stability'
    assert identity['fundamental_niche_claim_allowed'] is False
    assert identity['temporal_independence_claim_allowed'] is False
    assert identity['causal_physiological_driver_claim_allowed'] is False
    assert identity['universal_process_claim_allowed'] is False
    assert c['product_b']['automatically_unblocked_by_product_a_promotion'] is False
    assert c['product_b']['separate_formal_unblock_gate_required'] is True


def test_supported_primary_fresh_decision_promotes_product_a_only(tmp_path):
    kt = tmp_path / 'kt'; fresh = tmp_path / 'fresh'; out = tmp_path / 'out'
    _known_truth(kt, supported=True)
    _fresh(fresh, 'empirical_confirmation_supported', source_kind='primary')
    result = apply_fresh_promotion(
        contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
    )
    assert result['decision'] == 'product_a_v2_7_1_promoted'
    assert result['fresh_decision_source'] == 'primary'
    assert result['product_a_v2_7_1_promoted'] is True
    assert result['product_b_empirical_use_unblocked'] is False
    protocol = json.loads((out / 'promoted_product_a_v2_7_1_protocol.json').read_text())
    assert protocol['promoted'] is True
    assert protocol['fresh_decision_source'] == 'primary'
    assert protocol['product']['temporal_independence_claim_allowed'] is False


def test_supported_frozen_continuation_is_equivalent_promotion_input(tmp_path):
    kt = tmp_path / 'kt'; fresh = tmp_path / 'fresh'; out = tmp_path / 'out'
    _known_truth(kt, supported=True)
    _fresh(fresh, 'empirical_confirmation_supported', source_kind='technical_continuation')
    result = apply_fresh_promotion(
        contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
    )
    assert result['decision'] == 'product_a_v2_7_1_promoted'
    assert result['fresh_decision_source'] == 'technical_continuation'
    assert result['product_a_v2_7_1_promoted'] is True
    assert result['product_b_empirical_use_unblocked'] is False


def test_negative_and_unavailable_fresh_states_never_promote(tmp_path):
    for i, state in enumerate(('empirical_confirmation_not_supported', 'empirical_confirmation_unavailable')):
        kt = tmp_path / f'kt{i}'; fresh = tmp_path / f'fresh{i}'; out = tmp_path / f'out{i}'
        _known_truth(kt, supported=True)
        _fresh(fresh, state, source_kind='primary')
        result = apply_fresh_promotion(
            contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
        )
        assert result['decision'] == 'product_a_v2_7_1_not_promoted'
        assert result['product_a_v2_7_1_promoted'] is False
        assert result['threshold_relaxation_after_outcome'] is False
        assert result['candidate_reselection_after_outcome'] is False
        assert result['product_b_empirical_use_unblocked'] is False


def test_predecessor_known_truth_is_still_required(tmp_path):
    kt = tmp_path / 'kt'; fresh = tmp_path / 'fresh'; out = tmp_path / 'out'
    _known_truth(kt, supported=False)
    _fresh(fresh, 'empirical_confirmation_supported', source_kind='primary')
    result = apply_fresh_promotion(
        contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
    )
    assert result['decision'] == 'product_a_v2_7_1_not_promoted'
    assert result['product_a_v2_7_1_promoted'] is False
    assert result['product_b_empirical_use_unblocked'] is False


def test_ambiguous_primary_and_continuation_receipts_fail_closed(tmp_path):
    kt = tmp_path / 'kt'; fresh = tmp_path / 'fresh'; out = tmp_path / 'out'
    _known_truth(kt, supported=True)
    _fresh(fresh, 'empirical_confirmation_supported', source_kind='primary')
    continuation = {
        'purpose': 'product_a_v2_7_1_fresh_confirmation_continuation_execution_receipt',
        'implementation_sha': '08edc61eaee19461cee440e8e8cfceb769e7f3f6',
        'frozen_ref': 'frozen/product-a-v2-7-1-fresh-confirmation-continuation-08edc61e',
        'primary_run_id': 32552745281,
        'decision': 'empirical_confirmation_supported',
        'reran_all_six_sealed_audits': True,
        'scientific_thresholds_changed': False,
        'candidate_reselection_performed': False,
        'scientific_promotion_allowed': False,
        'product_b_unblocked': False,
    }
    (fresh / 'continuation_execution_receipt.json').write_text(json.dumps(continuation) + '\n')
    with pytest.raises(ValueError, match='exactly one primary/continuation receipt'):
        apply_fresh_promotion(
            contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
        )
