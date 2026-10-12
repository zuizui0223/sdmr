"""Validate a value-preserving C/F layout intervention."""
import importlib.util
from pathlib import Path
import numpy as np

SCRIPT=Path(__file__).resolve().parents[1]/'experiments/v5_layout_control.py'
def module():
    assert SCRIPT.exists(), 'layout control is not implemented'
    spec=importlib.util.spec_from_file_location('layout_control',SCRIPT)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def test_layout_intervention_changes_no_values_and_has_both_routes():
    m=module()
    assert hasattr(m,'layout_scores'), 'controlled C/F fitting contrast not implemented'
    rng=np.random.default_rng(73)
    x=rng.normal(size=(60,4)); y=np.tile([0,1],30)
    splits=[(np.arange(20,60),np.arange(20)),
            (np.r_[0:20,40:60],np.arange(20,40)),
            (np.arange(40),np.arange(40,60))]
    original=x.copy(); r=m.layout_scores(x,y,splits)
    assert np.array_equal(original,x)
    assert r['same_training_values_all_folds']
    for route in ('raw','scaled'):
        assert set(r[route])=={'C','F'}
        for order in ('C','F'):
            assert len(r[route][order]['fold_scores'])==3
            assert np.isfinite(r[route][order]['mean_score'])
        assert r[route]['C']['training_c_contiguous']==[True]*3
        assert r[route]['F']['training_c_contiguous']==[False]*3
    assert r['maximum_scaled_probability_difference']<1e-8
