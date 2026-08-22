import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_6_empirical_model_pool_worker import M_NAMES
from sdmr.v2_7_1_fresh_model_pool_shard_aggregate import aggregate_fresh_model_pool_shards

CONTRACT = Path('configs/product_a_v2_7_1_fresh_presealed_sharded_continuation_contract.json')


def _write_shard(root: Path, M: str, *, mismatch: bool = False, available: bool = True) -> None:
    d = root / M
    d.mkdir(parents=True)
    payload = {
        'purpose': 'product_a_v2_7_1_fresh_model_pool_M_shard',
        'available': available,
        'unavailable_stage': None if available else 'structural_partition',
        'unavailable_reason': None if available else 'frozen structural support unavailable',
        'taxon': 'Synthetic taxon',
        'taxon_index': 2,
        'part_seed': 2026082201,
        'M': M,
        'partition_seed': 2026082672,
        'selected_assignment_attempt': 1,
        'n_admissible_predictors': 2,
        'admissible_predictors': ['bio1', 'bio12'],
        'audit_predictors': ['bio1', 'bio12'],
        'audit_processes': ['thermal', 'water'],
        'sealed_occurrence_environment_read': False,
        'sealed_occurrence_used_for_selection': False,
        'sealed_occurrence_used_for_process_status': False,
        'candidate_model_fitting_performed': available,
        'candidate_scores_used_for_partition_or_audit_selection': False,
        'transport_shard_only': True,
        'scientific_semantics_changed': False,
    }
    (d / 'contract.json').write_text(json.dumps(payload) + '\n')
    if not available:
        return
    shared = 'x,y\n1,2\n' if not mismatch else f'x,y\n1,{3 if M == M_NAMES[-1] else 2}\n'
    for name in [
        'predictor_coverage.csv',
        'evidence_balanced_partition_support.csv',
        'evidence_balanced_partition_attempts.csv',
        'audit_support.csv',
        'audit_pruning.csv',
        'base_audit_space.csv',
        'partition_presence.csv',
        *[f'partition_background__{x}.csv' for x in M_NAMES],
    ]:
        (d / name).write_text(shared)
    pd.DataFrame([{'fold': 0, 'candidate': 'c', 'M': M}]).to_csv(d / 'base_fold_metrics.csv', index=False)
    pd.DataFrame([{'fold': 0, 'candidate': 'c::exclude::thermal', 'M': M}]).to_csv(d / 'knockout_fold_metrics.csv', index=False)
    pd.DataFrame([{'step': 0, 'M': M}]).to_csv(d / 'selection_trace.csv', index=False)
    pd.DataFrame([{'taxon': 'Synthetic taxon', 'M': M, 'group': 'base', 'status': 'success'}]).to_csv(d / 'worker_status.csv', index=False)


def test_preoutcome_sharded_continuation_is_transport_only_and_fail_closed():
    c = json.loads(CONTRACT.read_text())
    assert c['contract_frozen_before_any_fresh_sealed_audit_artifact'] is True
    assert c['new_scientific_thresholds'] is False
    assert c['primary_source']['run_id'] == 32552745281
    assert c['primary_source']['sealed_audit_artifacts_observed_at_contract_freeze'] == 0
    scope = c['continuation_scope']
    assert scope['reuse_primary_worker_outputs'] is False
    assert scope['rerun_all_72_taxon_part_workers'] is True
    assert scope['split_each_worker_into_exactly_three_M_transport_shards'] is True
    assert scope['n_M_shards'] == 216
    assert scope['require_byte_identical_shared_partition_and_audit_ledgers_across_M_shards'] is True
    assert scope['selective_repair_of_only_failed_primary_workers_allowed'] is False
    invariants = c['scientific_invariants']
    assert all(value is False for key, value in invariants.items() if key.endswith('_changed'))
    assert invariants['partition_or_audit_selection_uses_candidate_scores'] is False
    assert invariants['post_outcome_candidate_reselection_allowed'] is False
    assert invariants['post_outcome_threshold_tuning_allowed'] is False
    activation = c['activation_rule']
    assert activation['primary_run_must_complete_non_success'] is True
    assert activation['primary_decision_artifact_must_be_absent'] is True
    assert activation['primary_pretruth_artifacts_must_be_absent'] is True
    assert activation['primary_sealed_audit_artifacts_must_be_absent'] is True
    assert activation['parity_gate_required_before_continuation_dispatch'] is True
    assert activation['activation_may_not_depend_on_candidate_scores_or_scientific_metric_values'] is True
    assert c['execution_identity']['execution_allowed'] is False
    assert c['claim_boundary']['scientific_promotion_allowed_by_continuation'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_three_M_shards_reassemble_original_worker_contract(tmp_path):
    root = tmp_path / 'shards'
    for M in M_NAMES:
        _write_shard(root, M)
    out = tmp_path / 'worker'
    result = aggregate_fresh_model_pool_shards(
        shard_root=root,
        taxon='Synthetic taxon',
        taxon_index=2,
        part_seed=2026082201,
        output_dir=out,
    )
    assert result['purpose'] == 'product_a_v2_7_1_fresh_model_pool_worker'
    assert result['available'] is True
    assert result['M_specs'] == list(M_NAMES)
    assert result['assembled_from_three_M_transport_shards'] is True
    assert result['scientific_semantics_changed'] is False
    assert result['sealed_occurrence_environment_read'] is False
    assert list(pd.read_csv(out / 'base_fold_metrics.csv')['M']) == list(M_NAMES)
    assert list(pd.read_csv(out / 'worker_status.csv')['M']) == list(M_NAMES)


def test_shards_must_have_identical_shared_partition_and_audit_ledgers(tmp_path):
    root = tmp_path / 'shards'
    for M in M_NAMES:
        _write_shard(root, M, mismatch=True)
    with pytest.raises(ValueError, match='shared file'):
        aggregate_fresh_model_pool_shards(
            shard_root=root,
            taxon='Synthetic taxon',
            taxon_index=2,
            part_seed=2026082201,
            output_dir=tmp_path / 'worker',
        )


def test_unavailable_shard_propagates_without_sealed_read(tmp_path):
    root = tmp_path / 'shards'
    for M in M_NAMES:
        _write_shard(root, M, available=M != M_NAMES[1])
    out = tmp_path / 'worker'
    result = aggregate_fresh_model_pool_shards(
        shard_root=root,
        taxon='Synthetic taxon',
        taxon_index=2,
        part_seed=2026082201,
        output_dir=out,
    )
    assert result['available'] is False
    assert result['sealed_occurrence_environment_read'] is False
    assert result['candidate_model_fitting_performed'] is False
