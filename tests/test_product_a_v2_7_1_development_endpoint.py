import json
from pathlib import Path

ENDPOINT = Path('configs/product_a_v2_7_1_development_endpoint.json')
SOURCE_GATE = Path('configs/product_a_v2_7_1_fresh_empirical_source_gate.json')


def test_v271_development_endpoint_is_frozen_without_promotion():
    c = json.loads(ENDPOINT.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_development_endpoint'
    assert c['development_endpoint_frozen'] is True
    assert c['implementation_sha'] == 'e93e93cc97551df3fa32a8dfb17bc813dd2cdf39'
    assert c['workflow_run_id'] == 32455011154
    assert c['workflow_run_conclusion'] == 'success'
    assert c['summary_artifact']['artifact_id'] == 9437018612
    assert c['diagnostic_result']['n_diagnostics'] == 72
    assert c['diagnostic_result']['legacy_v2_7_audit_support_available'] == 39
    assert c['diagnostic_result']['v2_7_1_audit_support_available'] == 70
    assert c['diagnostic_result']['n_improved_from_legacy_v2_7'] == 31
    assert c['diagnostic_result']['n_regressed_from_legacy_v2_7'] == 0
    assert len(c['structural_abstentions']) == 2
    assert {x['taxon'] for x in c['structural_abstentions']} == {
        'Dryopteris filix-mas',
        'Quercus robur',
    }
    assert c['information_barrier']['sealed_environment_read'] is False
    assert c['information_barrier']['candidate_model_fitting_performed_in_diagnostic'] is False
    assert c['information_barrier']['scientific_promotion_allowed'] is False
    assert c['information_barrier']['product_b_unblocked'] is False
    assert c['stop_rule']['retune_on_current_2026_08_01_snapshot_to_force_72_of_72'] is False
    assert c['next_lane']['genuinely_fresh_empirical_evidence_required'] is True


def test_fresh_empirical_source_gate_fails_closed_until_source_is_pinned():
    c = json.loads(SOURCE_GATE.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_empirical_source_gate'
    assert c['gate_state'] == 'blocked_until_genuinely_fresh_source_is_pinned'
    assert c['execution_allowed'] is False
    assert c['historical_development_source']['snapshot_date'] == '2026-08-01'
    assert c['historical_development_source']['may_be_used_as_fresh_confirmation_denominator'] is False
    assert c['historical_development_source']['existing_six_split_parts_may_be_relabelled_as_fresh'] is False
    assert c['freshness_rule']['requires_new_untouched_occurrence_snapshot_and_or_new_taxon_panel'] is True
    required = c['required_before_execution']
    for key in (
        'snapshot_or_download_identifier',
        'snapshot_created_at',
        'focal_file_sha256',
        'target_group_file_sha256',
        'taxon_panel_path',
        'taxon_panel_sha256',
        'implementation_sha',
        'frozen_ref',
        'split_seeds',
        'sealed_fractions',
        'decision_contract_path',
    ):
        assert required[key] is None
    assert c['scientific_constraints']['ordinary_prediction_metrics_are_guardrails_not_tuning_target'] is True
    assert c['scientific_constraints']['post_outcome_candidate_reselection_allowed'] is False
    assert c['scientific_constraints']['post_outcome_threshold_tuning_allowed'] is False
    assert c['scientific_constraints']['development_70_of_72_result_may_define_new_scientific_thresholds'] is False
    assert c['scientific_constraints']['scientific_promotion_allowed_before_gate_is_satisfied'] is False
    assert c['scientific_constraints']['product_b_unblocked_before_separate_promotion_decision'] is False
