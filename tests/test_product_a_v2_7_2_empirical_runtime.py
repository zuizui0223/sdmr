import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_6_empirical_model_pool_worker import M_NAMES
from sdmr.v2_7_2_deterministic_procedure_library import deterministic_procedure_library
from sdmr.v2_7_2_fresh_contract import (
    load_v2_7_2_fresh_confirmation_contract,
    load_v2_7_2_source_receipt,
)
from sdmr.v2_7_2_fresh_model_pool_shard_aggregate import (
    aggregate_fresh_model_pool_shards,
)

CONTRACT = Path('configs/product_a_v2_7_2_fresh_confirmation_contract.json')
SOURCE_GATE = Path('configs/product_a_v2_7_2_fresh_empirical_source_gate.json')


def test_v272_scientific_contract_and_seeded_library_are_frozen():
    c = load_v2_7_2_fresh_confirmation_contract(CONTRACT)
    assert c['fresh_taxon_panel']['predeclared_candidate_rank'] == 2
    assert c['fixed_design']['procedure_library']['model_random_state'] == 0
    assert c['fixed_design']['procedure_library']['selection_process_numpy_seed'] == 0
    procedures = deterministic_procedure_library(c)
    assert len(procedures) == 8
    assert len({p.label for p in procedures}) == 8
    assert all(p.model_spec.random_state == 0 for p in procedures)
    assert all(p.label.endswith('_rs0') for p in procedures)


def test_v272_source_receipt_loader_fails_closed_before_source_identities_are_pinned(tmp_path):
    receipt = tmp_path / 'receipt.json'
    receipt.write_text(json.dumps({'purpose': 'product_a_v2_7_2_fresh_raw_source_receipt'}))
    with pytest.raises(ValueError, match='not fully pinned'):
        load_v2_7_2_source_receipt(receipt, source_gate_path=SOURCE_GATE)


def _write_shard(root: Path, M: str, *, mismatch=False, available=True):
    d = root / M
    d.mkdir(parents=True)
    payload = {
        'purpose': 'product_a_v2_7_2_fresh_model_pool_M_shard',
        'available': available,
        'unavailable_stage': None if available else 'structural_partition',
        'unavailable_reason': None if available else 'frozen support unavailable',
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
        'model_random_state': 0,
        'selection_process_numpy_seed': 0,
        'sealed_occurrence_environment_read': False,
        'sealed_occurrence_used_for_selection': False,
        'sealed_occurrence_used_for_process_status': False,
        'candidate_model_fitting_performed': available,
        'candidate_scores_used_for_partition_or_audit_selection': False,
        'primary_M_shard': True,
        'deterministic_successor': True,
    }
    (d / 'contract.json').write_text(json.dumps(payload) + '\n')
    if not available:
        return
    shared = 'x,y\n1,2\n'
    if mismatch and M == M_NAMES[-1]:
        shared = 'x,y\n1,3\n'
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
    pd.DataFrame([{'fold': 0, 'candidate': 'all|logit_l2_C1_degree2_rs0', 'M': M}]).to_csv(
        d / 'base_fold_metrics.csv', index=False
    )
    pd.DataFrame([{'fold': 0, 'candidate': 'all|logit_l2_C1_degree2_rs0::exclude::thermal', 'M': M}]).to_csv(
        d / 'knockout_fold_metrics.csv', index=False
    )
    pd.DataFrame([{'step': 0, 'M': M}]).to_csv(d / 'selection_trace.csv', index=False)
    pd.DataFrame([{
        'taxon': 'Synthetic taxon', 'M': M, 'group': 'base', 'status': 'success'
    }]).to_csv(d / 'worker_status.csv', index=False)


def test_three_primary_M_shards_reassemble_one_deterministic_worker(tmp_path):
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
    assert result['purpose'] == 'product_a_v2_7_2_fresh_model_pool_worker'
    assert result['available'] is True
    assert result['assembled_from_three_primary_M_shards'] is True
    assert result['shared_partition_and_audit_ledgers_byte_identical'] is True
    assert result['model_random_state'] == 0
    assert result['selection_process_numpy_seed'] == 0
    assert result['deterministic_successor'] is True
    assert list(pd.read_csv(out / 'base_fold_metrics.csv')['M']) == list(M_NAMES)


def test_primary_M_shards_fail_closed_if_shared_ledgers_differ(tmp_path):
    root = tmp_path / 'shards'
    for M in M_NAMES:
        _write_shard(root, M, mismatch=True)
    with pytest.raises(ValueError, match='byte-for-byte'):
        aggregate_fresh_model_pool_shards(
            shard_root=root,
            taxon='Synthetic taxon',
            taxon_index=2,
            part_seed=2026082201,
            output_dir=tmp_path / 'worker',
        )


def test_unavailable_primary_M_shard_propagates_without_sealed_read(tmp_path):
    root = tmp_path / 'shards'
    for M in M_NAMES:
        _write_shard(root, M, available=M != M_NAMES[1])
    result = aggregate_fresh_model_pool_shards(
        shard_root=root,
        taxon='Synthetic taxon',
        taxon_index=2,
        part_seed=2026082201,
        output_dir=tmp_path / 'worker',
    )
    assert result['available'] is False
    assert result['sealed_occurrence_environment_read'] is False
    assert result['candidate_model_fitting_performed'] is False
    assert result['deterministic_successor'] is True
