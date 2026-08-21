from pathlib import Path

from sdmr.v2_7_1_evidence_balanced_contract import load_v2_7_1_evidence_balanced_contract

CONFIG=Path('configs/product_a_v2_7_1_evidence_balanced_folds_development_contract.json')


def test_v271_contract_keeps_v27_result_and_uses_counts_only_for_partition():
    c=load_v2_7_1_evidence_balanced_contract(CONFIG)
    assert c['development_only'] is True
    assert c['scientific_promotion_allowed'] is False
    assert c['independent_empirical_confirmation_claim_allowed'] is False
    p=c['predecessor_v2_7_development_result']
    assert p['run_id']==32447844270
    assert p['n_audit_support_available']==39
    assert p['availability_fraction']==39/72
    assert p['sealed_environment_read'] is False
    d=c['diagnosis']
    assert d['example_total_evaluation_background_rows']==2
    assert d['minimum_required_evaluation_background_rows']==5
    fold=c['evidence_balanced_partition']
    assert fold['spatial_microblocks']==12
    assert fold['outer_folds']==4
    assert fold['assignment_attempts']==32
    assert fold['shared_occurrence_fold_assignment_across_all_M'] is True
    assert fold['minimum_evaluation_occurrences_per_fold']==2
    assert fold['minimum_evaluation_background_rows_per_M_fold']==5
    assert fold['minimum_training_background_rows_per_M_fold']==5
    assert fold['environmental_values_used'] is False
    assert fold['candidate_scores_used'] is False
    assert fold['process_knockout_outcomes_used'] is False
    assert fold['sealed_rows_used'] is False
    audit=c['audit_space_after_partition']
    assert audit['minimum_predictor_coverage']==0.95
    assert audit['minimum_joint_coverage']==0.80
    assert audit['minimum_processes']==4
    assert audit['thresholds_unchanged_from_v2_7'] is True
    assert c['development_source']['future_independent_confirmation_requires_genuinely_fresh_empirical_evidence'] is True
