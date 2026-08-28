import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

import sdmr.v2_8_4_presealed_runtime as runtime


RUNTIME_DESIGN = Path('configs/product_a_v2_8_4_runtime_successor_contract.json')
SCIENTIFIC_CONTRACT = Path('configs/product_a_v2_8_3_fresh_confirmation_contract.json')
PROCESS_REGISTRY = Path('configs/product_a_empirical_process_registry_v1.csv')


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _materialization(tmp_path: Path) -> Path:
    part = tmp_path / 'part'
    (part / 'M').mkdir(parents=True)
    _write_json(part / 'contract.json', {
        'purpose': 'product_a_v2_7_2_fresh_part_model_pool_materialization',
        'seed': 2026082201,
        'sealed_occurrence_raster_values_extracted': False,
        'sealed_background_raster_values_extracted': False,
    })
    return part


def _precompute(tmp_path: Path) -> Path:
    pre = tmp_path / 'precompute'
    pre.mkdir()
    _write_json(pre / 'contract.json', {
        'purpose': runtime.PRECOMPUTE_PURPOSE,
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
    })
    pd.DataFrame({'row_index': [0, 1], 'fold': [0, 1], 'microblock': [0, 1]}).to_csv(
        pre / 'partition_presence.csv', index=False
    )
    for M in runtime.M_NAMES:
        pd.DataFrame({'row_index': [0, 1], 'fold': [0, 1], 'microblock': [0, 1]}).to_csv(
            pre / f'partition_background__{M}.csv', index=False
        )
    return pre


def test_base_and_process_knockout_pass_exact_frozen_predictor_sets_to_same_benchmark(monkeypatch, tmp_path):
    part = _materialization(tmp_path)
    pre = _precompute(tmp_path)
    calls = []

    occurrence = pd.DataFrame({
        'species': ['Taxon testii', 'Taxon testii'],
        'longitude': [140.0, 141.0],
        'latitude': [38.0, 39.0],
        'bio1': [1.0, 2.0],
        'bio12': [3.0, 4.0],
    })
    background = pd.DataFrame({
        'species': ['Taxon testii', 'Taxon testii'],
        'longitude': [139.0, 142.0],
        'latitude': [37.0, 40.0],
        'bio1': [0.0, 3.0],
        'bio12': [2.0, 5.0],
    })

    # This is a core semantic-equivalence test, not a parquet integration test.
    # Keep it runnable in the repository's core `.[test]` CI without pyarrow.
    def fake_read_parquet(path):
        path = Path(path)
        if path.name == 'model_occurrences.parquet':
            return occurrence.copy()
        if path.name == 'model_background.parquet':
            return background.copy()
        raise AssertionError(f'unexpected parquet path: {path}')

    def fake_benchmark(**kwargs):
        calls.append({
            'ecological_predictors': tuple(kwargs['ecological_predictors']),
            'procedure_labels': tuple(p.label for p in kwargs['procedures']),
            'outer_folds': kwargs['outer_folds'],
            'chance_auc': kwargs['chance_auc'],
            'minimum_auc_margin': kwargs['minimum_auc_margin'],
            'auc_sem_multiplier': kwargs['auc_sem_multiplier'],
        })
        return SimpleNamespace(
            fold_metrics=pd.DataFrame([{
                'fold': 0,
                'candidate': 'frozen-candidate',
                'procedure': 'frozen-candidate',
                'presence_rank': 0.7,
            }]),
            selection_trace=pd.DataFrame([{'step': 0, 'winner': 'bio1'}]),
        )

    monkeypatch.setattr(runtime.pd, 'read_parquet', fake_read_parquet)
    monkeypatch.setattr(runtime, 'benchmark_recovery_procedures', fake_benchmark)

    base_out = tmp_path / 'base'
    base = runtime.evaluate_group(
        runtime_design_path=RUNTIME_DESIGN,
        scientific_contract_path=SCIENTIFIC_CONTRACT,
        process_registry_path=PROCESS_REGISTRY,
        part_dir=part,
        precompute_dir=pre,
        scientific_execution_id='exec-test',
        taxon='Taxon testii',
        taxon_index=3,
        part_seed=2026082201,
        M_name='buffer_150km',
        evaluation_group='base',
        output_dir=base_out,
        attempt_ordinal=0,
    )
    water_out = tmp_path / 'water'
    water = runtime.evaluate_group(
        runtime_design_path=RUNTIME_DESIGN,
        scientific_contract_path=SCIENTIFIC_CONTRACT,
        process_registry_path=PROCESS_REGISTRY,
        part_dir=part,
        precompute_dir=pre,
        scientific_execution_id='exec-test',
        taxon='Taxon testii',
        taxon_index=3,
        part_seed=2026082201,
        M_name='buffer_150km',
        evaluation_group='water',
        output_dir=water_out,
        attempt_ordinal=1,
    )

    assert calls[0]['ecological_predictors'] == ('bio1', 'bio12')
    assert calls[1]['ecological_predictors'] == ('bio1',)
    for call in calls:
        assert len(call['procedure_labels']) == 8
        assert all(label.endswith('_rs0') for label in call['procedure_labels'])
        assert call['outer_folds'] == 4
        assert call['chance_auc'] == 0.5
        assert call['minimum_auc_margin'] == 0.01
        assert call['auc_sem_multiplier'] == 1.0

    base_metrics = pd.read_csv(base_out / 'fold_metrics.csv')
    water_metrics = pd.read_csv(water_out / 'fold_metrics.csv')
    assert set(base_metrics['group']) == {'base'}
    assert water_metrics.iloc[0]['candidate'] == 'frozen-candidate::exclude::water'
    assert water_metrics.iloc[0]['procedure'] == 'frozen-candidate::exclude::water'
    assert water_metrics.iloc[0]['excluded_process_domain'] == 'water'
    assert water_metrics.iloc[0]['excluded_predictors'] == 'bio12'

    assert base['logical_shard_id'] != water['logical_shard_id']
    assert base['operational_attempt_ordinal'] == 0
    assert water['operational_attempt_ordinal'] == 1
    assert base['sealed_occurrence_environment_read'] is False
    assert water['sealed_occurrence_environment_read'] is False
    assert json.loads((water_out / 'telemetry.json').read_text())['scientific_selection_input'] is False
