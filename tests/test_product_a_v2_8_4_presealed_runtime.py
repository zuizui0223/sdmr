import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_6_empirical_model_pool_worker import M_NAMES
from sdmr.v2_7_2_fresh_model_pool_shard_aggregate import (
    aggregate_fresh_model_pool_shards,
)
from sdmr.v2_8_4_presealed_runtime import (
    COMPAT_M_SHARD_PURPOSE,
    GROUP_PURPOSE,
    PRECOMPUTE_PURPOSE,
    _load_runtime_design,
    _logical_shard_id,
    aggregate_groups,
)


RUNTIME_DESIGN = Path('configs/product_a_v2_8_4_runtime_successor_contract.json')
GROUPS = (
    'base',
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


def _write_shared_precompute(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        'purpose': PRECOMPUTE_PURPOSE,
        'available': True,
        'scientific_execution_id': 'exec-test',
        'taxon': 'Taxon testii',
        'taxon_index': 3,
        'part_seed': 2026082201,
        'partition_seed': 2026082772,
        'selected_assignment_attempt': 4,
        'n_admissible_predictors': 2,
        'admissible_predictors': ['bio1', 'bio12'],
        'audit_predictors': ['bio1', 'bio12'],
        'audit_processes': ['thermal', 'water'],
        'model_random_state': 0,
        'selection_process_numpy_seed': 0,
    }
    _write_json(root / 'contract.json', payload)
    shared = [
        'predictor_coverage.csv',
        'evidence_balanced_partition_support.csv',
        'evidence_balanced_partition_attempts.csv',
        'audit_support.csv',
        'audit_pruning.csv',
        'base_audit_space.csv',
        'partition_presence.csv',
        *[f'partition_background__{name}.csv' for name in M_NAMES],
    ]
    for filename in shared:
        pd.DataFrame([{'stable': 1}]).to_csv(root / filename, index=False)
    return payload


def _write_group(root: Path, *, M: str, group: str, identity: dict) -> None:
    d = root / group
    d.mkdir(parents=True, exist_ok=True)
    contract = {
        'purpose': GROUP_PURPOSE,
        'available': True,
        'scientific_execution_id': 'exec-test',
        'logical_shard_id': _logical_shard_id(
            scientific_execution_id='exec-test',
            part_seed=2026082201,
            taxon_index=3,
            M_name=M,
            evaluation_group=group,
        ),
        'operational_attempt_ordinal': 0,
        'taxon': 'Taxon testii',
        'taxon_index': 3,
        'part_seed': 2026082201,
        'M': M,
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
        'v2_8_4_runtime_successor': True,
    }
    _write_json(d / 'contract.json', contract)
    pd.DataFrame([{
        'candidate': f'candidate::{group}',
        'procedure': f'candidate::{group}',
        'fold': 0,
        'taxon': 'Taxon testii',
        'M': M,
        'group': group,
    }]).to_csv(d / 'fold_metrics.csv', index=False)
    pd.DataFrame([{
        'step': 0,
        'taxon': 'Taxon testii',
        'M': M,
        'group': group,
    }]).to_csv(d / 'selection_trace.csv', index=False)
    pd.DataFrame([{
        'taxon': 'Taxon testii',
        'M': M,
        'group': group,
        'status': 'success',
        'error': None,
        'partition_seed': identity['partition_seed'],
    }]).to_csv(d / 'worker_status.csv', index=False)


def test_operational_attempt_is_not_part_of_logical_scientific_identity():
    first = _logical_shard_id(
        scientific_execution_id='exec-test',
        part_seed=2026082201,
        taxon_index=3,
        M_name='buffer_150km',
        evaluation_group='water',
    )
    second = _logical_shard_id(
        scientific_execution_id='exec-test',
        part_seed=2026082201,
        taxon_index=3,
        M_name='buffer_150km',
        evaluation_group='water',
    )
    assert first == second
    assert 'run' not in first and 'attempt' not in first


def test_runtime_design_fails_closed_if_science_is_marked_changed(tmp_path):
    payload = json.loads(RUNTIME_DESIGN.read_text(encoding='utf-8'))
    payload['scientific_invariants']['taxa_changed'] = True
    mutated = tmp_path / 'mutated.json'
    _write_json(mutated, payload)
    with pytest.raises(ValueError, match='taxa_changed'):
        _load_runtime_design(mutated)


def test_seven_group_assembly_preserves_legacy_M_shard_contract_and_downstream_worker(tmp_path):
    pre = tmp_path / 'precompute'
    identity = _write_shared_precompute(pre)
    m_root = tmp_path / 'M-shards'

    for M in M_NAMES:
        groups = tmp_path / f'groups-{M}'
        for group in GROUPS:
            _write_group(groups, M=M, group=group, identity=identity)
        out = m_root / M
        result = aggregate_groups(
            runtime_design_path=RUNTIME_DESIGN,
            precompute_dir=pre,
            group_root=groups,
            scientific_execution_id='exec-test',
            taxon='Taxon testii',
            taxon_index=3,
            part_seed=2026082201,
            M_name=M,
            output_dir=out,
        )
        assert result['purpose'] == COMPAT_M_SHARD_PURPOSE
        assert result['available'] is True
        assert result['v2_8_4_runtime_successor'] is True
        assert result['assembled_from_seven_independent_group_shards'] is True
        assert result['M_shared_precompute_reused'] is True
        assert result['telemetry_used_for_scientific_selection'] is False
        assert result['scientific_promotion_allowed'] is False
        assert result['product_b_unblocked'] is False

        base = pd.read_csv(out / 'base_fold_metrics.csv')
        knockout = pd.read_csv(out / 'knockout_fold_metrics.csv')
        status = pd.read_csv(out / 'worker_status.csv')
        assert set(base['group']) == {'base'}
        assert set(knockout['group']) == set(GROUPS) - {'base'}
        assert set(status['group']) == set(GROUPS)

    worker = tmp_path / 'worker'
    result = aggregate_fresh_model_pool_shards(
        shard_root=m_root,
        taxon='Taxon testii',
        taxon_index=3,
        part_seed=2026082201,
        output_dir=worker,
    )
    assert result['available'] is True
    assert result['assembled_from_three_primary_M_shards'] is True
    assert result['model_random_state'] == 0
    assert result['selection_process_numpy_seed'] == 0
    assert set(pd.read_csv(worker / 'base_fold_metrics.csv')['M']) == set(M_NAMES)
    assert set(pd.read_csv(worker / 'knockout_fold_metrics.csv')['M']) == set(M_NAMES)
