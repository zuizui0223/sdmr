import json
from pathlib import Path

CONTRACT = Path('configs/product_a_v2_7_1_fresh_confirmation_continuation_contract.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-1-fresh-confirmation-continuation.yml')


def test_continuation_is_preoutcome_transport_fix_not_scientific_redesign():
    c = json.loads(CONTRACT.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_confirmation_technical_continuation_preoutcome_contract'
    assert c['contract_frozen_before_any_fresh_sealed_audit_artifact'] is True
    assert c['new_scientific_thresholds'] is False
    assert c['primary_source']['run_id'] == 32552745281
    assert c['primary_source']['implementation_sha'] == '1f158006c0b5dbdd93af70632464727405ababfe'
    assert c['preoutcome_bug']['scientific_module_behavior_correct'] is True
    assert c['preoutcome_bug']['workflow_wrapper_behavior_incomplete'] is True
    assert c['preoutcome_bug']['sealed_audit_artifacts_observed_at_discovery'] == 0
    scope = c['continuation_scope']
    assert scope['rerun_materialization'] is False
    assert scope['rerun_model_pool'] is False
    assert scope['rerun_pretruth_selection'] is False
    assert scope['rerun_final_model_fitting'] is False
    assert scope['rerun_all_six_sealed_audits_not_selected_subset'] is True
    assert scope['reapply_same_frozen_six_part_decision'] is True
    assert scope['candidate_reselection_allowed'] is False
    assert scope['threshold_retuning_allowed'] is False
    activation = c['activation_rule']
    assert activation['primary_run_must_be_completed_non_success'] is True
    assert activation['primary_decision_artifact_must_be_absent'] is True
    assert activation['primary_six_part_artifacts_required'] is True
    assert activation['primary_six_pretruth_artifacts_required'] is True
    assert activation['primary_72_final_fit_artifacts_required'] is True
    assert activation['continuation_execution_identity_must_be_pinned_before_dispatch'] is True
    assert activation['activation_may_not_depend_on_scientific_metric_values'] is True
    assert c['claim_boundary']['scientific_promotion_allowed_by_continuation'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_continuation_workflow_accepts_both_fail_closed_unavailable_paths():
    text = WORKFLOW.read_text()
    assert 'run-id: 32552745281' in text
    assert "count('v271-fresh-part-')!=6" in text
    assert "count('v271-fresh-pretruth-')!=6" in text
    assert "count('v271-fresh-final-')!=72" in text
    assert 'rerun_all_six_sealed_audits_not_selected_subset' in text
    assert "elif c['sealed_occurrence_environment_read']" in text
    assert "c['undefined_sealed_ecological_evidence_propagated_as_unavailable'] is True" in text
    assert "c['structural_or_audit_abstention_propagated_as_unavailable'] is True" in text
    assert 'product-a-v2-7-1-fresh-taxon-holdout-confirmation-decision-continuation' in text
