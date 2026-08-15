import numpy as np
import pandas as pd

from sdmr.method import freeze_candidate_methods
from sdmr.model import ModelSpec


def _model_pool():
    rng = np.random.default_rng(114)
    n_p = 24
    n_b = 48
    presence = pd.DataFrame({
        'signal': rng.normal(1.2, 0.35, n_p),
        'noise': rng.normal(0, 1, n_p),
    })
    background = pd.DataFrame({
        'signal': rng.normal(-1.0, 0.45, n_b),
        'noise': rng.normal(0, 1, n_b),
    })
    presence_groups = np.arange(n_p) % 6
    background_groups = np.arange(n_b) % 6
    return presence, background, presence_groups, background_groups


def _protocol_signature(protocols):
    return {
        key: (
            value.predictors,
            value.model_spec.label,
            value.inner_score,
        )
        for key, value in protocols.items()
    }


def test_modelspec_parallel_is_exactly_equivalent(monkeypatch):
    p, b, pg, bg = _model_pool()
    specs = [
        ModelSpec(C=0.1, degree=1, penalty='l2'),
        ModelSpec(C=1.0, degree=1, penalty='l1'),
        ModelSpec(C=1.0, degree=2, penalty='l2'),
        ModelSpec(C=10.0, degree=1, penalty='l2'),
    ]
    kwargs = dict(
        model_specs=specs,
        inner_folds=3,
        min_gain=0.001,
        max_predictors=2,
        vif_threshold=5.0,
    )

    monkeypatch.setenv('SDMR_MODEL_SPEC_JOBS', '1')
    sequential_protocols, sequential_grid = freeze_candidate_methods(
        p, b, pg, bg, ['signal', 'noise'], **kwargs
    )
    monkeypatch.setenv('SDMR_MODEL_SPEC_JOBS', '3')
    parallel_protocols, parallel_grid = freeze_candidate_methods(
        p, b, pg, bg, ['signal', 'noise'], **kwargs
    )

    assert _protocol_signature(parallel_protocols) == _protocol_signature(sequential_protocols)
    pd.testing.assert_frame_equal(parallel_grid, sequential_grid)


def test_modelspec_parallel_env_rejects_invalid_values(monkeypatch):
    p, b, pg, bg = _model_pool()
    monkeypatch.setenv('SDMR_MODEL_SPEC_JOBS', '0')
    try:
        freeze_candidate_methods(
            p, b, pg, bg, ['signal', 'noise'],
            model_specs=[ModelSpec(C=1.0, degree=1, penalty='l2')],
            inner_folds=2,
            max_predictors=2,
        )
    except ValueError as exc:
        assert 'SDMR_MODEL_SPEC_JOBS' in str(exc)
    else:
        raise AssertionError('invalid SDMR_MODEL_SPEC_JOBS should fail')
