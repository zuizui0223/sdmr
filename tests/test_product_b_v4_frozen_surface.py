from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.model import ModelSpec, fit_relative_suitability_model
from sdmr.niche_recovery_procedure import RecoveryProcedure, benchmark_recovery_procedures
from sdmr.product_b_v4_known_truth_contract import load_product_b_v4_known_truth_contract
from sdmr.product_b_v4_surface_intervention import (
    frozen_surface_process_intervention,
    score_with_joint_reference_marginalization,
)

CONFIG = Path('configs/product_b_v4_known_truth_contract.json')


def _frames(seed=41):
    rng = np.random.default_rng(seed)
    n_p, n_b = 80, 160
    b = pd.DataFrame({
        'temperature': rng.normal(0, 1, n_b),
        'water': rng.normal(0, 1, n_b),
        'soil': rng.normal(0, 1, n_b),
        'seasonality': rng.normal(0, 1, n_b),
        'noise': rng.normal(0, 1, n_b),
    })
    p = pd.DataFrame({
        'temperature': rng.normal(0.8, 0.8, n_p),
        'water': rng.normal(0.7, 0.8, n_p),
        'soil': rng.normal(0, 1, n_p),
        'seasonality': rng.normal(0, 1, n_p),
        'noise': rng.normal(0, 1, n_p),
    })
    # Audit space is independent of the fitted-column names but complete.
    for frame in (p, b):
        frame['audit_temperature'] = frame['temperature']
        frame['audit_water'] = frame['water']
    pg = np.tile(np.arange(8), n_p // 8 + 1)[:n_p]
    bg = np.tile(np.arange(8), n_b // 8 + 1)[:n_b]
    return p, b, pg, bg


def test_v4_contract_keeps_v3_negative_and_uses_fresh_truth():
    c = load_product_b_v4_known_truth_contract(CONFIG)
    assert c['opened_generating_truth_seed_maximum'] == 712
    assert [x['seed'] for x in c['product_b_evaluation_taxa']] == list(range(721, 733))
    assert c['successor_history'][-1]['outcome'] == 'product_b_v3_known_truth_not_supported'
    assert c['diagnosis']['v3_thresholds_retuned'] is False
    s = c['process_intervention_semantics']
    assert s['model_refit_after_process_intervention'] is False
    assert s['predictor_reselection_after_process_intervention'] is False
    assert s['intervention'] == 'joint_training_background_marginalization'
    assert s['process_reference_rows_maximum'] == 64
    assert c['process_constraint_rule']['min_pareto_worsening_fraction'] == 2 / 3
    assert c['universality_rule']['stable_core_min_validation_confirmation_fraction'] == 0.8


def test_joint_reference_marginalization_keeps_model_fixed_and_is_deterministic():
    p, b, _, _ = _frames()
    predictors = ('temperature', 'water', 'soil')
    model = fit_relative_suitability_model(p, b, predictors, model_spec=ModelSpec(C=1.0, degree=2))
    x = score_with_joint_reference_marginalization(
        model, b.iloc[:20], predictors, ('temperature', 'water'), b, max_reference_rows=16
    )
    y = score_with_joint_reference_marginalization(
        model, b.iloc[:20], predictors, ('temperature', 'water'), b, max_reference_rows=16
    )
    assert np.allclose(x, y, equal_nan=True)
    assert np.isfinite(x).all()
    # Jointly marginalizing two fitted drivers should remove row-specific variation
    # carried only by those two columns but retain soil-dependent variation.
    assert float(np.nanstd(x)) > 0


def test_frozen_surface_intervention_reconstructs_base_and_never_refits_after_process(tmp_path):
    p, b, pg, bg = _frames(52)
    predictors = ('temperature', 'water', 'soil', 'seasonality', 'noise')
    audit = ('audit_temperature', 'audit_water')
    proc = RecoveryProcedure(
        strategy='all',
        model_spec=ModelSpec(C=1.0, degree=2),
        inner_folds=2,
        max_predictors=4,
        predictive_min_gain=0.0,
    )
    bench = benchmark_recovery_procedures(
        p,
        b,
        pg,
        bg,
        predictors,
        audit,
        (proc,),
        outer_folds=2,
        chance_auc=0.5,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=1.0,
    )
    base = bench.fold_metrics
    assert set(base['fold'].astype(int)) == {0, 1}
    out = frozen_surface_process_intervention(
        p,
        b,
        pg,
        bg,
        base,
        audit,
        proc,
        ('temperature', 'water', 'soil', 'seasonality', 'noise'),
        {x: x for x in ('temperature', 'water', 'soil', 'seasonality', 'noise')},
        outer_folds=2,
        max_reference_rows=16,
        base_reconstruction_tolerance=1e-8,
    )
    assert len(out) == 10
    assert set(out['fold'].astype(int)) == {0, 1}
    assert out['model_refit_after_process_intervention'].eq(False).all()
    assert out['predictor_reselection_after_process_intervention'].eq(False).all()
    assert out['fitted_product_a_surface_frozen'].eq(True).all()
    assert out['base_surface_reconstruction_verified'].eq(True).all()
    assert out['process_intervention'].eq('joint_training_background_marginalization').all()
    for _, group in out.groupby('excluded_process_domain'):
        assert set(group['fold'].astype(int)) == {0, 1}
