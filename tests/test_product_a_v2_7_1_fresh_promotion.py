import json
from pathlib import Path

import pandas as pd

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


def _fresh(root: Path, decision: str) -> None:
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


def test_preoutcome_promotion_contract_is_claim_bounded_and_product_b_separate():
    c = load_fresh_promotion_contract(CONTRACT)
    assert c['contract_frozen_before_fresh_sealed_outcome'] is True
    assert c['new_postoutcome_scientific_thresholds'] is False
    assert c['fresh_taxon_holdout_source']['run_id'] == 32552745281
    assert c['fresh_taxon_holdout_source']['implementation_sha'] == '1f158006c0b5dbdd93af70632464727405ababfe'
    assert c['fresh_taxon_holdout_source']['sealed_audit_artifacts_observed_before_contract'] == 0
    assert c['fresh_taxon_holdout_source']['decision_artifacts_observed_before_contract'] == 0
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


def test_supported_fresh_decision_promotes_product_a_only(tmp_path):
    kt = tmp_path / 'kt'; fresh = tmp_path / 'fresh'; out = tmp_path / 'out'
    _known_truth(kt, supported=True)
    _fresh(fresh, 'empirical_confirmation_supported')
    result = apply_fresh_promotion(
        contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
    )
    assert result['decision'] == 'product_a_v2_7_1_promoted'
    assert result['product_a_v2_7_1_promoted'] is True
    assert result['product_b_empirical_use_unblocked'] is False
    row = pd.read_csv(out / 'decision.csv').iloc[0]
    assert bool(row['product_a_v2_7_1_promoted']) is True
    assert bool(row['product_b_empirical_use_unblocked']) is False
    protocol = json.loads((out / 'promoted_product_a_v2_7_1_protocol.json').read_text())
    assert protocol['promoted'] is True
    assert protocol['product']['temporal_independence_claim_allowed'] is False


def test_negative_and_unavailable_fresh_states_never_promote(tmp_path):
    for i, state in enumerate(('empirical_confirmation_not_supported', 'empirical_confirmation_unavailable')):
        kt = tmp_path / f'kt{i}'; fresh = tmp_path / f'fresh{i}'; out = tmp_path / f'out{i}'
        _known_truth(kt, supported=True)
        _fresh(fresh, state)
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
    _fresh(fresh, 'empirical_confirmation_supported')
    result = apply_fresh_promotion(
        contract_path=CONTRACT, known_truth_dir=kt, fresh_empirical_dir=fresh, output_dir=out,
    )
    assert result['decision'] == 'product_a_v2_7_1_not_promoted'
    assert result['product_a_v2_7_1_promoted'] is False
    assert result['product_b_empirical_use_unblocked'] is False
