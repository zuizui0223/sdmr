import json
from pathlib import Path

import pandas as pd

from sdmr.v2_6_empirical_model_pool_worker import M_NAMES
from sdmr.v2_7_2_fresh_model_pool_shard_aggregate import (
    aggregate_fresh_model_pool_shards,
)
from sdmr.v2_8_4_presealed_aggregate import aggregate_groups_resumable
from sdmr.v2_8_4_presealed_runtime import PRECOMPUTE_PURPOSE


RUNTIME_DESIGN = Path('configs/product_a_v2_8_4_runtime_successor_contract.json')


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def test_unavailable_shared_precompute_maps_to_unavailable_legacy_M_shards_without_group_jobs(tmp_path):
    pre = tmp_path / 'precompute'
    pre.mkdir()
    _write_json(pre / 'contract.json', {
        'purpose': PRECOMPUTE_PURPOSE,
        'available': False,
        'unavailable_stage': 'audit_space',
        'unavailable_reason': 'synthetic frozen audit-space abstention',
        'scientific_execution_id': 'exec-test-unavailable',
        'taxon': 'Taxon unavailable',
        'taxon_index': 5,
        'part_seed': 2026082202,
    })
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
        pd.DataFrame().to_csv(pre / filename, index=False)

    m_root = tmp_path / 'M-shards'
    for M in M_NAMES:
        out = m_root / M
        result = aggregate_groups_resumable(
            runtime_design_path=RUNTIME_DESIGN,
            precompute_dir=pre,
            group_root=tmp_path / 'groups-not-created',
            scientific_execution_id='exec-test-unavailable',
            taxon='Taxon unavailable',
            taxon_index=5,
            part_seed=2026082202,
            M_name=M,
            output_dir=out,
        )
        assert result['available'] is False
        assert result['unavailable_stage'] == 'audit_space'
        assert result['candidate_model_fitting_performed'] is False
        assert result['sealed_occurrence_environment_read'] is False
        assert result['scientific_promotion_allowed'] is False
        assert result['product_b_unblocked'] is False

    worker = tmp_path / 'worker'
    result = aggregate_fresh_model_pool_shards(
        shard_root=m_root,
        taxon='Taxon unavailable',
        taxon_index=5,
        part_seed=2026082202,
        output_dir=worker,
    )
    assert result['available'] is False
    assert result['candidate_model_fitting_performed'] is False
    assert result['sealed_occurrence_environment_read'] is False
    assert 'audit_space' in result['unavailable_stage']
