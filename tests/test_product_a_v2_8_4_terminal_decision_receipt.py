import json
from pathlib import Path


RECEIPT = Path('configs/product_a_v2_8_4_terminal_decision_receipt.json')
RESULT = Path('docs/product_a_v2_8_4_terminal_result_2026-08-31.md')


def test_v284_terminal_receipt_pins_the_complete_scientific_non_support_result():
    receipt = json.loads(RECEIPT.read_text())
    run = receipt['authoritative_run']
    terminal = receipt['terminal_scientific_decision']
    boundary = receipt['interpretation_boundary']

    assert receipt['scientific_execution_id'] == 'product-a-v2-8-4-fresh-confirmation-v1'
    assert run['workflow_run_id'] == 33364164527
    assert run['workflow_run_attempt'] == 1
    assert run['workflow_run_conclusion'] == 'success'
    assert run['head_sha'] == '1496a6c63b19bf7711511a864ccb448fc123c963'
    assert run['aggregate_decision_job_id'] == 99422033684

    assert len(receipt['run_artifacts']) == 8
    terminal_artifact = next(
        artifact
        for artifact in receipt['run_artifacts']
        if artifact['artifact_name'] == 'product-a-v2-8-4-terminal-decision'
    )
    assert terminal_artifact == {
        'artifact_id': 9750071472,
        'artifact_name': 'product-a-v2-8-4-terminal-decision',
        'artifact_size_bytes': 3422,
        'artifact_digest': 'sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f',
    }
    assert set(receipt['terminal_artifact_files']) == {
        'contract.json',
        'decision.csv',
        'part_summary.csv',
        'partial_identification_bounds.csv',
        'process_status.csv',
        'structural_part_summary.csv',
    }

    assert terminal['decision'] == 'empirical_confirmation_not_supported'
    assert terminal['scientific_terminal_reached'] is True
    assert terminal['technical_stop_or_unavailable'] is False
    assert terminal['all_3_structural_parts_auditable'] is True
    assert terminal['all_primary_scientific_evidence_available'] is True
    assert terminal['primary_denominator'] == 3
    assert terminal['prediction_guardrail'] is True
    assert terminal['ecological_support'] is False
    assert terminal['process_reproducibility_support'] is True
    assert terminal['ecologically_nondominated_parts'] == 3
    assert terminal['strict_ecological_improvement_parts'] == 0
    assert terminal['mean_presence_rank_delta_vs_auc'] == 0.0
    assert terminal['conditional_results_can_override_primary_decision'] is False

    assert boundary['known_truth_lane_remains_supported'] is True
    assert boundary['fresh_empirical_product_a_confirmation_supported'] is False
    assert boundary['separate_promotion_or_nonpromotion_decision_recorded'] is False
    assert boundary['product_b_unblocked'] is False
    assert boundary['post_outcome_retuning_or_candidate_reselection_allowed'] is False
    assert boundary['fourth_workflow_dispatch_allowed'] is False


def test_v284_terminal_result_preserves_the_claim_and_hard_stop_boundaries():
    text = RESULT.read_text()
    assert '`empirical_confirmation_not_supported`' in text
    assert 'not a technical STOP or unavailable state' in text
    assert 'strict ecological improvement in 0/3 parts' in text
    assert 'Product B remains blocked throughout' in text
    assert 'must not be rerun, retuned, rescued, or replaced' in text
    assert 'separate promotion decision' in text
