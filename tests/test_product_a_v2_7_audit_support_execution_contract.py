import json
from pathlib import Path

CONFIG = Path('configs/product_a_v2_7_audit_support_execution_contract.json')


def test_v2_7_audit_support_execution_is_frozen_and_development_only():
    c = json.loads(CONFIG.read_text())
    assert c['purpose'] == 'product_a_v2_7_audit_support_development_execution_contract'
    assert c['execution_source_frozen_before_diagnostic_outcome'] is True
    assert c['implementation_sha'] == '0bb0bdd99303ca956681de15cfe3fad903dad7a9'
    assert c['frozen_ref'] == 'frozen/product-a-v2-7-audit-support-0bb0bdd9'
    assert c['workflow_file'] == 'product-a-v2-7-audit-support-development.yml'
    assert c['summary_artifact_name'] == 'product-a-v2-7-audit-support-development-summary'
    assert c['requires_single_workflow_dispatch_run_for_frozen_source'] is True
    assert c['development_only'] is True
    assert c['scientific_promotion_allowed'] is False
    assert c['independent_empirical_confirmation_claim_allowed'] is False
    assert c['product_b_unblocked'] is False
    assert c['source_model_pool_materialization_run_id'] == 32260616084
    assert c['source_v2_6_unavailable_run_id'] == 32445550518
    assert c['source_v2_6_sealed_environment_opened'] is False
    assert c['sealed_environment_read_allowed'] is False
    assert c['candidate_model_fitting_allowed_in_this_diagnostic'] is False
    assert c['diagnostic_denominator']['expected_diagnostics'] == 72
    assert c['outcome_use']['may_inform_v2_7_development'] is True
    assert c['outcome_use']['may_not_reclassify_current_v2_6_split_as_independent_v2_7_confirmation'] is True
    assert c['outcome_use']['future_promotion_requires_genuinely_fresh_empirical_evidence'] is True
