from pathlib import Path

from sdmr.v2_7_audit_support_contract import load_v2_7_audit_support_contract

CONFIG = Path('configs/product_a_v2_7_audit_support_development_contract.json')


def test_v2_7_development_contract_preserves_v2_6_unavailable_result_and_fresh_confirmation_boundary():
    c = load_v2_7_audit_support_contract(CONFIG)
    assert c['development_only'] is True
    assert c['scientific_promotion_allowed'] is False
    assert c['independent_empirical_confirmation_claim_allowed'] is False
    assert c['product_b_unblocked'] is False
    predecessor = c['predecessor_v2_6_empirical_result']
    assert predecessor['exact_run_id'] == 32445550518
    assert predecessor['result'] == 'sealed_blind_empirical_confirmation_unavailable'
    assert predecessor['pretruth_artifact_count'] == 0
    assert predecessor['sealed_audit_artifact_count'] == 0
    assert predecessor['sealed_environment_opened'] is False
    assert predecessor['incomplete_taxon_M_cells_per_candidate'] == 23
    source = c['development_source']
    assert source['model_pool_only_reuse_allowed'] is True
    assert source['outer_sealed_environment_read_allowed'] is False
    assert source['current_v2_6_sealed_split_may_not_be_relabelled_as_fresh_v2_7_confirmation'] is True
    assert source['future_independent_confirmation_requires_genuinely_fresh_evidence'] is True
    candidate = c['candidate_universe']
    assert candidate['all_43_predeclared_CHELSA_predictors_remain_candidate_eligible'] is True
    assert candidate['candidate_predictor_availability_gate_unchanged'] == 0.95
    assert candidate['weighted_super_score'] is False
    audit = c['audit_space']
    assert audit['minimum_predictor_coverage'] == 0.95
    assert audit['minimum_joint_coverage'] == 0.80
    assert audit['minimum_processes'] == 4
    assert audit['minimum_complete_fit_background_rows_per_M_fold'] == 5
    assert audit['minimum_complete_evaluation_background_rows_per_M_fold'] == 5
    assert audit['minimum_complete_heldout_occurrence_rows_per_M_fold'] == 2
    assert audit['candidate_scores_used'] is False
    assert audit['sealed_rows_used'] is False
