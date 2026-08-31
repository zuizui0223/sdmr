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
    assert run['authorization_preflight_job_id'] == 99401287346
    assert run['receipt_preflight_job_id'] == 99401310355
    assert run['sealed_part_job_ids'] == {
        '2026082201': 99401464490,
        '2026082202': 99401464527,
        '2026082203': 99401464478,
    }
    assert run['aggregate_decision_job_id'] == 99422033684

    artifact_pins = {
        artifact['artifact_name']: (
            artifact['artifact_id'],
            artifact['artifact_size_bytes'],
            artifact['artifact_digest'],
        )
        for artifact in receipt['run_artifacts']
    }
    assert artifact_pins == {
        'product-a-v2-8-4-sealed-preflight': (
            9747698898,
            2989,
            'sha256:978217d21564062054757c2f4c3e2bc72db5e2f6d8fd756efc94ec647f8fb56a',
        ),
        'product-a-v2-8-4-finalized-part-2026082201': (
            9750048481,
            9761,
            'sha256:56938514d0be4080652514d3900cee2caffea8bd223a3a3bb6cc703abb4e84eb',
        ),
        'product-a-v2-8-4-sealed-state-2026082201': (
            9750047982,
            15336,
            'sha256:d132e457ae669b9bd4af50a990ff2eafd4f82237328b077596b7f19a92a62b1b',
        ),
        'product-a-v2-8-4-finalized-part-2026082202': (
            9749405054,
            9685,
            'sha256:fc5fc6bc9fafc0049d4013e6b9cc1a46c8de61b77a51f3e06d31bbbbcc8672a2',
        ),
        'product-a-v2-8-4-sealed-state-2026082202': (
            9749404799,
            15248,
            'sha256:381c6aaa8de2c73f40e56f2ab642f173aeefa0de7fbb416ae44c0480161cc18b',
        ),
        'product-a-v2-8-4-finalized-part-2026082203': (
            9749815263,
            9839,
            'sha256:2ee21a65f2f7415b785b5b2768c8e5fd61ada01400e45c7898fcd8dab78225af',
        ),
        'product-a-v2-8-4-sealed-state-2026082203': (
            9749814855,
            15419,
            'sha256:02a66c0dd10c0c666da4434ffabba777af05ea9144b085dfac838cf10b91d639',
        ),
        'product-a-v2-8-4-terminal-decision': (
            9750071472,
            3422,
            'sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f',
        ),
    }
    assert receipt['terminal_artifact_files'] == {
        'contract.json': '052eb7d1e77cdb35b433a6fc3a24b72690f8ca7d3d642616ee41b8539369065b',
        'decision.csv': 'b04fc138297fa613158e86ac32c2b8625c167b96ead4c130fab9bf4739ebefef',
        'part_summary.csv': '3e6464d9e68417a8169565385b9ee7bc380471c37b06e28069bce0462f55401c',
        'partial_identification_bounds.csv': '3b90769696b438fe7e8246ead659d29a816b23f33a5d585392e217a27f84b9cf',
        'process_status.csv': 'ddfe6242f2f056c557f3b98bd4d4c776df949ca53cc3e7705d62d18b198090ac',
        'structural_part_summary.csv': 'c80502e158c5687fa8cd5ea45ba3b016f554cef11369401846b718637b34daf4',
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
