import hashlib
import json
from pathlib import Path

ENDPOINT = Path('configs/product_a_v2_7_1_development_endpoint.json')
SOURCE_GATE = Path('configs/product_a_v2_7_1_fresh_empirical_source_gate.json')
SOURCE_RECEIPT = Path('configs/product_a_v2_7_1_fresh_raw_source_receipt.json')
CONFIRMATION = Path('configs/product_a_v2_7_1_fresh_confirmation_contract.json')
PANEL = Path('configs/product_a_v2_7_1_fresh_confirmation_taxa.csv')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    assert {x['taxon'] for x in c['structural_abstentions']} == {'Dryopteris filix-mas', 'Quercus robur'}
    assert c['information_barrier']['sealed_environment_read'] is False
    assert c['information_barrier']['candidate_model_fitting_performed_in_diagnostic'] is False
    assert c['information_barrier']['scientific_promotion_allowed'] is False
    assert c['information_barrier']['product_b_unblocked'] is False
    assert c['stop_rule']['retune_on_current_2026_08_01_snapshot_to_force_72_of_72'] is False
    assert c['next_lane']['genuinely_fresh_empirical_evidence_required'] is True


def test_fresh_taxon_holdout_raw_sources_are_pinned_but_confirmation_execution_stays_closed():
    c = json.loads(SOURCE_GATE.read_text())
    assert c['purpose'] == 'product_a_v2_7_1_fresh_empirical_source_gate'
    assert c['gate_state'] == 'raw_sources_pinned_exact_confirmation_implementation_pending'
    assert c['execution_allowed'] is False

    fresh = c['freshness_design']
    assert fresh['independence_axis'] == 'taxon_holdout_not_temporal'
    assert fresh['disjoint_from_current_pilot_12'] is True
    assert fresh['temporal_independence_claim_allowed'] is False
    assert fresh['new_taxon_panel_path'] == str(PANEL)
    assert fresh['new_taxon_panel_sha256'] == sha256(PANEL)
    assert fresh['eligibility_run_id'] == 32474864368
    assert fresh['eligibility_artifact_id'] == 9444172302

    historical = c['historical_catalog_transport']
    assert historical['snapshot_date'] == '2026-08-01'
    assert historical['catalog_may_be_requeried_for_frozen_disjoint_taxon_panel'] is True
    assert historical['old_pilot_focal_artifact_may_be_reused'] is False
    assert historical['old_target_artifact_excluding_old_pilot_12_may_be_reused'] is False
    assert historical['existing_six_split_parts_may_be_reused_or_relabelled_as_fresh'] is False

    design = c['fixed_confirmation_design']
    assert design['decision_contract_path'] == str(CONFIRMATION)
    assert design['decision_contract_sha256'] == sha256(CONFIRMATION)
    assert design['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert design['sealed_fractions'] == [0.2, 0.3]
    assert design['n_confirmation_parts'] == 6

    receipt = json.loads(SOURCE_RECEIPT.read_text())
    assert receipt['workflow_run_id'] == 32477393089
    assert receipt['workflow_conclusion'] == 'success'
    assert receipt['receipt_artifact']['artifact_id'] == 9445363468
    assert receipt['information_barrier']['environmental_values_read'] is False
    assert receipt['information_barrier']['candidate_model_fitting_performed'] is False
    assert receipt['information_barrier']['sealed_confirmation_outcomes_read'] is False

    required = c['required_before_execution']
    assert required['new_focal_artifact_run_id'] == 32477393089
    assert required['new_focal_artifact_name'] == 'product-a-v2-7-1-fresh-focal-source-2026-08-01'
    assert required['focal_file_sha256'] == '96810e03ce557faad28d8b384d2e2e92ce348b405790f52ffff75ab5bd56c0a0'
    assert required['focal_query_sha256'] == '204080e6ca30cb9eafc7093de82d4e42bacefebd251f15fabb14686da02e1716'
    assert required['new_target_group_artifact_run_id'] == 32477393089
    assert required['new_target_group_artifact_name'] == 'product-a-v2-7-1-fresh-target-source-2026-08-01'
    assert required['target_group_file_sha256'] == '4d6b1830c5750a2339258219bfde24f9e20435c69aaf27eca20c72f59c15a66a'
    assert required['target_group_query_sha256'] == '80864205a643f65e9a42b4a5c282423737d207fb186283a6296e5063f630142e'
    assert required['target_group_excluded_taxa_sha256'] == sha256(PANEL)
    assert required['implementation_sha'] is None
    assert required['frozen_ref'] is None
    assert required['workflow_file'] is None

    constraints = c['scientific_constraints']
    assert constraints['ordinary_prediction_metrics_are_guardrails_not_tuning_target'] is True
    assert constraints['post_outcome_candidate_reselection_allowed'] is False
    assert constraints['post_outcome_threshold_tuning_allowed'] is False
    assert constraints['development_70_of_72_result_may_define_new_scientific_thresholds'] is False
    assert constraints['scientific_promotion_allowed_before_separate_promotion_decision'] is False
    assert constraints['product_b_unblocked_before_separate_promotion_decision'] is False
