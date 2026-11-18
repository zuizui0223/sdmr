"""Complete pre-outcome synthetic regression and source-lock contract tests."""
from pathlib import Path
import importlib.util
import math
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fia_climate_density_growth_v1',ROOT/'experiments/fia_climate_density_growth_v1.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)


def synthetic(n=1800):
    rng=np.random.default_rng(22)
    rows=[]
    for ix in range(n):
        state=('RI','VA','WI')[ix%3]
        statebase={'RI':0,'VA':50,'WI':100}[state]
        county=statebase+ix//90%17
        T=rng.normal(scale=.6); P=rng.normal(scale=.6);density=rng.uniform(0.3,2)
        grow=0.015-0.004*density+0.001*T+0.0005*P-0.0015*T*density+rng.normal(scale=.006)
        rows.append(dict(sp='316',state=state,plot=f'p{ix}',county=f'{county:05d}',year_centered=(ix%35-15)/20,
                         interval=5+rng.uniform(-.4,.4),ln_dia10=rng.normal(),age60=rng.uniform(.4,2),
                         ba100=density,tanom3=T,panom200=P,growth=grow))
    return pd.DataFrame(rows)


def test_baseline_climate_and_delta_scales():
    index={(f,y,m):(float(y-1991),10.0) for f in [f'{c:05d}' for c in range(209)] for y in range(1991,2021) for m in range(4,10)}
    out=model.baseline_climate(index)
    assert len(out)==209
    assert out['00000'][0]==14.5
    assert out['00000'][1]==60.0
    index.pop(('00000',2020,8))
    with pytest.raises(ValueError,match='baseline month'):model.baseline_climate(index)


def test_nested_models_and_deterministic_county_folds():
    d=synthetic()
    sizes=[model.model_design(d,k)[0].shape[1] for k in ('baseline','climate','shared_interaction','state_interaction')]
    assert sizes==[8,10,12,16]
    one=model.assign_county_folds(d)
    other=model.assign_county_folds(d.sample(frac=1,random_state=3))
    assert np.array_equal(one,model.assign_county_folds(d))
    assert np.isin(one,np.arange(5)).all()
    assert set(other)==set(one)


def test_gain_from_real_simulated_climate_x_density_interaction():
    out=model.species_fit(synthetic())
    assert out['status']=='exploratory_county_heldout_association_only'
    assert out['n_growth_pairs']==1800
    assert all(z['status']=='cross_validated' for z in out['scores'].values())
    assert out['incremental_shared_interaction_gain']>0
    assert out['scores']['shared_interaction']['rmse_log_dia_per_year'] < out['scores']['climate']['rmse_log_dia_per_year']


def test_unobserved_or_underpowered_species_not_zeros():
    out=model.species_fit(synthetic().iloc[:55])
    assert out['status']=='insufficient_source_support'
    assert 'scores' not in out


def test_diameter_growth_outcome_must_be_finite():
    assert model.valid_float('') is None
    assert model.valid_float('infinity') is None
    assert model.valid_float('12.5',low=1,high=150)==12.5
    assert model.valid_float('0.0',low=1,high=150) is None


def test_source_manifest_no_growth_not_authorized(tmp_path):
    path=tmp_path/'m.json'
    path.write_text('{"study":"fia_pre_response_county_climate_tree_source_gate_v3","n_eligible_source_states":0}')
    receipt=tmp_path/'n.json';receipt.write_text('{}')
    csv=tmp_path/'x.csv';csv.write_text('')
    plot=tmp_path/'p.json';plot.write_text('{}')
    with pytest.raises(ValueError,match='No full pre-response'):
        model.contract(path,receipt,csv,plot)
