import json
from pathlib import Path

import pandas as pd

from sdmr.v2_6_empirical_model_pool_worker import M_NAMES
from sdmr.v2_8_4_presealed_aggregate import aggregate_groups_resumable
from sdmr.v2_8_4_presealed_runtime import GROUP_PURPOSE, PRECOMPUTE_PURPOSE


RUNTIME_DESIGN = Path('configs/product_a_v2_8_4_runtime_successor_contract.json')
DOMAINS = (
    'thermal',
    'water',
    'seasonality_phenology',
    'energy_productivity',
    'snow',
    'wind',
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _shared_precompute(root: Path) -> dict:
    root.mkdir(parents=True)
    payload = {
        'purpose': PRECOMPUTE_PURPOSE,
        'available': True,
        'scientific_execution_id': 'exec-row-contract',
        'taxon': 'Taxon contractii',
        'taxon_index': 4,
        'part_seed': 2026082201,
        'partition_seed': 2026082872,
        'selected_assignment_attempt': 5,
        'n_admissible_predictors': 2,
        'admissible_predictors': ['bio1', 'bio12'],
        'audit_predictors': ['bio1', 'bio12'],
        'audit_processes': ['thermal', 'water'],
        'model_random_state': 0,
        'selection_process_numpy_seed': 0,
    }
    _write_json(root / 'contract.json', payload)
    for filename in (
        'predictor_coverage.csv',
        'evidence_balanced_partition_support.csv',
        'evidence_balanced_partition_attempts.csv',
        'audit_support.csv',
        'audit_pruning.csv',
        'base_audit_space.csv',
        'partition_presence.csv',
        *[f'partition_background__{name}.csv' for name in M_NAMES],
    ):
        pd.DataFrame([{'stable': 1}]).to_csv(root / filename, index=False)
    return payload


def _group(root: Path, *, group: str, identity: dict) -> None:
    d = root / group
    d.mkdir(parents=True)
    contract = {
        'purpose': GROUP_PURPOSE,
        'available': True,
        'scientific_execution_id': 'exec-row-contract',
        'logical_shard_id': f'exec-row-contract|group={group}',
        'operational_attempt_ordinal': 0,
        'taxon': 'Taxon contractii',
        'taxon_index': 4,
        'part_seed': 2026082201,
        'M': 'buffer_150km',
        'evaluation_group': group,
        'partition_seed': identity['partition_seed'],
        'selected_assignment_attempt': identity['selected_assignment_attempt'],
        'n_admissible_predictors': identity['n_admissible_predictors'],
        'admissible_predictors': identity['admissible_predictors'],
        'audit_predictors': identity['audit_predictors'],
        'audit_processes': identity['audit_processes'],
        'model_random_state': 0,
        'selection_process_numpy_seed': 0,
        'sealed_occurrence_environment_read': False,
        'sealed_occurrence_used_for_selection': False,
        'sealed_occurrence_used_for_process_status': False,
        'candidate_model_fitting_performed': True,
        'candidate_scores_used_for_partition_or_audit_selection': False,
    }
    _write_json(d / 'contract.json', contract)
    pd.DataFrame([{
        'candidate': f'candidate::{group}',
        'procedure': f'candidate::{group}',
        'fold': 0,
        'taxon': 'Taxon contractii',
        'M': 'buffer_150km',
        'group': group,
        'excluded_process_domain': None if group == 'base' else group,
    }]).to_csv(d / 'fold_metrics.csv', index=False)
    pd.DataFrame([{
        'step': 0,
        'taxon': 'Taxon contractii',
        'M': 'buffer_150km',
        'group': group,
    }]).to_csv(d / 'selection_trace.csv', index=False)
    pd.DataFrame([{
        'taxon': 'Taxon contractii',
        'M': 'buffer_150km',
        'group': group,
        'status': 'success',
        'partition_seed': identity['partition_seed'],
    }]).to_csv(d / 'worker_status.csv', index=False)


def test_resumable_aggregate_restores_partition_seed_and_frozen_process_order(tmp_path):
    pre = tmp_path / 'precompute'
    identity = _shared_precompute(pre)
    groups = tmp_path / 'groups'

    # Deliberately write in a non-scientific operational completion order.
    completion_order = (
        'wind', 'base', 'snow', 'water', 'thermal',
        'energy_productivity', 'seasonality_phenology',
    )
    for group in completion_order:
        _group(groups, group=group, identity=identity)

    out = tmp_path / 'M'
    result = aggregate_groups_resumable(
        runtime_design_path=RUNTIME_DESIGN,
        precompute_dir=pre,
        group_root=groups,
        scientific_execution_id='exec-row-contract',
        taxon='Taxon contractii',
        taxon_index=4,
        part_seed=2026082201,
        M_name='buffer_150km',
        output_dir=out,
    )

    base = pd.read_csv(out / 'base_fold_metrics.csv')
    knockout = pd.read_csv(out / 'knockout_fold_metrics.csv')
    trace = pd.read_csv(out / 'selection_trace.csv')
    status = pd.read_csv(out / 'worker_status.csv')

    assert set(base['partition_seed']) == {identity['partition_seed']}
    assert set(knockout['partition_seed']) == {identity['partition_seed']}
    assert tuple(knockout['group'].astype(str)) == DOMAINS
    assert tuple(trace['group'].astype(str)) == ('base', *DOMAINS)
    assert tuple(status['group'].astype(str)) == ('base', *DOMAINS)
    assert result['predecessor_metric_row_contract_restored'] is True
    assert tuple(result['process_group_order']) == DOMAINS
    assert result['scientific_promotion_allowed'] is False
    assert result['product_b_unblocked'] is False
