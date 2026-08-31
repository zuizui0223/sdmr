import csv
import hashlib
import json
import subprocess
from pathlib import Path


TERMINAL = Path('configs/product_a_v2_8_4_terminal_decision_receipt.json')
DECISION = Path('configs/product_a_v2_8_4_promotion_decision.json')
EVIDENCE = Path('configs/product_a_v2_8_4_manuscript_evidence_table.csv')
MANUSCRIPT = Path('docs/product_a_manuscript_closure_2026-08-31.md')


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_separate_nonpromotion_decision_uses_only_the_fixed_terminal_record():
    terminal = json.loads(TERMINAL.read_text())
    decision = json.loads(DECISION.read_text())
    source = decision['source_terminal_record']
    criteria = decision['frozen_criteria_assessment']
    result = decision['separate_decision']

    assert source['path'] == TERMINAL.as_posix()
    assert source['repository_ref'] == 'a6b68302ac7435f3626082508c3d00e7b241679c'
    assert source['git_blob_sha'] == '678568bf0b002e62f645068c726fa36d6c2ffc34'
    assert subprocess.check_output(
        ['git', 'hash-object', '--path', TERMINAL.as_posix(), TERMINAL.as_posix()],
        text=True,
    ).strip() == '678568bf0b002e62f645068c726fa36d6c2ffc34'
    assert _sha(TERMINAL) == 'b310308a4a2409939547f67355897dd1aa23df43484ca2b4abf68c9b3a178f72'
    assert source['newline_canonical_sha256'] == 'b310308a4a2409939547f67355897dd1aa23df43484ca2b4abf68c9b3a178f72'
    assert source['workflow_run_id'] == terminal['authoritative_run']['workflow_run_id'] == 33364164527
    assert source['terminal_artifact_id'] == 9750071472
    assert source['terminal_scientific_decision'] == terminal['terminal_scientific_decision']['decision']

    assert criteria['valid_fresh_empirical_terminal_decision'] is True
    assert criteria['full_primary_denominator_complete'] is True
    assert criteria['primary_denominator'] == 3
    assert criteria['technical_stop_or_unavailable'] is False
    assert criteria['prediction_guardrail'] is True
    assert criteria['ecological_support'] is False
    assert criteria['process_reproducibility_support'] is True
    assert criteria['ecologically_nondominated_parts'] == 3
    assert criteria['strict_ecological_improvement_parts'] == 0
    assert criteria['mean_presence_rank_delta_vs_auc'] == 0.0
    assert criteria['conditional_results_can_override_primary_decision'] is False

    assert result['product_a_promotion_decision'] == 'not_promoted'
    assert result['scientific_promotion_allowed'] is False
    assert result['product_b_unblocked'] is False
    assert result['known_truth_support_preserved'] is True
    assert result['fresh_empirical_advantage_supported'] is False


def test_publication_route_and_development_hard_stop_are_fail_closed():
    decision = json.loads(DECISION.read_text())
    route = decision['publication_route']
    stop = decision['development_hard_stop']

    assert route['highest_challenge_nee_or_ecology_letters_triggered'] is False
    assert route['primary_target'] == 'Methods in Ecology and Evolution'
    assert route['immediate_fallback'] == 'Ecological Informatics'
    assert route['product_b_route_exists'] is False
    assert route['journal_target_may_trigger_additional_favorable_dataset_hunting'] is False

    assert stop['valid_product_a_terminal_condition_met'] is True
    assert stop['separate_promotion_or_nonpromotion_condition_met'] is True
    assert stop['product_a_scientific_development_closed'] is True
    assert stop['additional_product_a_experiment_allowed'] is False
    assert stop['consumed_endpoint_rerun_retune_rescue_or_replacement_allowed'] is False
    assert stop['taxon_seed_M_fraction_threshold_candidate_provider_or_denominator_change_allowed'] is False


def test_manuscript_evidence_and_claim_ceiling_are_complete():
    with EVIDENCE.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            'evidence_unit', 'status', 'scientific_role', 'authoritative_source', 'claim_use'
        ]
        rows = list(reader)
    assert rows == [
        {
            'evidence_unit': 'known_truth_v2_6',
            'status': 'supported',
            'scientific_role': 'known_truth_recovery_and_process_safety',
            'authoritative_source': 'docs/product_a_v2_6_fresh_validation_result_2026-08-19.md',
            'claim_use': 'supports_architecture_not_empirical_promotion',
        },
        {
            'evidence_unit': 'known_truth_v2_7_2',
            'status': 'supported',
            'scientific_role': 'deterministic_known_truth_recovery',
            'authoritative_source': 'docs/product_a_v2_7_2_known_truth_result_2026-08-23.md',
            'claim_use': 'supports_implementation_and_known_truth_claims_only',
        },
        {
            'evidence_unit': 'empirical_v2_8_3',
            'status': 'technical_execution_terminal',
            'scientific_role': 'presealed_runtime_cancellation',
            'authoritative_source': 'run_33036252432',
            'claim_use': 'provenance_only_not_scientific_negative',
        },
        {
            'evidence_unit': 'empirical_v2_8_4',
            'status': 'empirical_confirmation_not_supported',
            'scientific_role': 'full_denominator_fresh_terminal',
            'authoritative_source': 'run_33364164527_artifact_9750071472',
            'claim_use': 'primary_fresh_scientific_result',
        },
        {
            'evidence_unit': 'prediction_guardrail',
            'status': 'supported',
            'scientific_role': 'presence_rank_guardrail',
            'authoritative_source': 'run_33364164527_artifact_9750071472',
            'claim_use': 'conditional_component_of_terminal_result',
        },
        {
            'evidence_unit': 'ecological_support',
            'status': 'not_supported',
            'scientific_role': 'strict_ecological_improvement_rule',
            'authoritative_source': 'run_33364164527_artifact_9750071472',
            'claim_use': 'blocks_product_a_promotion',
        },
        {
            'evidence_unit': 'process_reproducibility',
            'status': 'supported',
            'scientific_role': 'process_status_modal_reproducibility',
            'authoritative_source': 'run_33364164527_artifact_9750071472',
            'claim_use': 'conditional_and_cannot_override_primary',
        },
        {
            'evidence_unit': 'product_a_promotion',
            'status': 'not_promoted',
            'scientific_role': 'separate_promotion_decision',
            'authoritative_source': 'configs/product_a_v2_8_4_promotion_decision.json',
            'claim_use': 'closes_product_a_scientific_development',
        },
        {
            'evidence_unit': 'product_b',
            'status': 'blocked',
            'scientific_role': 'separate_paper_entry_gate',
            'authoritative_source': 'configs/product_a_v2_8_4_promotion_decision.json',
            'claim_use': 'no_product_b_analysis_or_claim',
        },
    ]

    text = MANUSCRIPT.read_text()
    assert 'scientific scope closed / proceed to submission assembly' in text
    assert 'strict ecological improvement in none' in text
    assert 'does not establish that AUC is universally optimal' in text
    assert 'Do not start another Product-A experiment' in text
    assert 'Submit this bounded result without waiting for Product B' in text
