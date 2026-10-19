"""Exact algebra tests and snapshot integrity for stationary-response turnover."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from experiments import geographic_constraint_switch_geometry_v1 as mod

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'evidence/geographic_turnover_native_source_v1/available_climate_cells.csv'


def real_inputs():
    return pd.read_csv(SOURCE),hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def test_source_provenance_and_complete_geography():
    df,sha=real_inputs()
    assert sha==mod.EXPECTED_SOURCE_SHA256
    r=mod.study(df,source_sha256=sha)
    assert r['n_equal_area_climate_cells']==187
    assert [v['climate_cell_counts'] for v in r['results']]==[[30,24],[56,77]]
    assert r['same_response_in_both_regions'] and not r['uses_occurrence_or_effort_columns']


def test_quadratic_exact_real_climate_thresholds():
    df,sha=real_inputs()
    o=mod.study(df,source_sha256=sha)
    q,p=[x['fixed_hypothetical_response']['quadratic'] for x in o['results']]
    assert q['fixed_weight_observed_opportunity_reversal']
    assert p['fixed_weight_observed_opportunity_reversal']
    assert [v['dominant_hypothetical_penalty'] for v in q['regions']]==['moisture','thermal']
    assert [v['dominant_hypothetical_penalty'] for v in p['regions']]==['moisture','thermal']
    assert q['critical_weight_open_interval']==pytest.approx([0.37288,4.120],abs=0.01)
    assert p['critical_weight_open_interval']==pytest.approx([0.1981,1.569],abs=0.01)
    assert q['raw_temperature_overlap_c']==pytest.approx(0.4)
    assert p['raw_temperature_overlap_c']==0


def test_absolute_penalty_and_postsource_grid():
    df,sha=real_inputs()
    r=mod.study(df,source_sha256=sha)
    assert [x['fixed_hypothetical_response']['absolute']['fixed_weight_observed_opportunity_reversal']
            for x in r['results']]==[True,True]
    assert [x['fixed_hypothetical_response']['quadratic']['sensitivity_grid']['n_driver_reversals_under_fixed_weight']
            for x in r['results']]==[61,100]
    assert [x['fixed_hypothetical_response']['absolute']['sensitivity_grid']['n_driver_reversals_under_fixed_weight']
            for x in r['results']]==[63,101]


def test_no_outcome_column_can_change_result():
    df,sha=real_inputs()
    baseline=mod.study(df,source_sha256=sha)
    changed=df.copy()
    for col in changed.columns:
        if 'records' in col or 'effort' in col or 'focal' in col:
            changed[col]=123456
    changed['additional_fitness_outcomes']=0.01
    assert mod.study(changed,source_sha256=sha)==baseline
    assert mod.study(df.sample(frac=1,random_state=123),source_sha256=sha)==baseline


def test_source_hash_and_missing_geography_fail_closed():
    df,sha=real_inputs()
    with pytest.raises(ValueError,match='source bytes'):
        mod.study(df,source_sha256='other')
    with pytest.raises(ValueError,match='four-region'):
        mod.study(df[df.region!='pinus_FI_central'],source_sha256=sha)
    with pytest.raises(ValueError,match='Duplicate'):
        mod.study(pd.concat((df,df.iloc[[0]])),source_sha256=sha)


def test_same_opportunity_cannot_switch_under_identical_response():
    df,_=real_inputs()
    a=df[df.region=='quercus_DE_central']
    params=mod.ILLUSTRATION
    for power in (1,2):
        r=mod.evaluate_pair(a,a.copy(),params=params,power=power)
        assert not r['switch_possible_for_fixed_identical_response_weights']
        assert not r['fixed_weight_observed_opportunity_reversal']
        assert r['critical_weight_open_interval'] is None


def test_exact_threshold_condition_analytically():
    df,_=real_inputs()
    a=df[df.region=='quercus_DE_central']
    b=df[df.region=='quercus_SE_south']
    r=mod.evaluate_pair(a,b,params=mod.ILLUSTRATION,power=2)
    lo,hi=r['critical_weight_open_interval']
    for weight in (lo*0.9,(lo+hi)/2,hi*1.1):
        p=dict(mod.ILLUSTRATION,relative_thermal_weight=weight)
        o=mod.evaluate_pair(a,b,params=p,power=2)
        assert o['fixed_weight_observed_opportunity_reversal']==(lo<weight<hi)


def test_hypothetical_fitness_sorting_does_not_erase_switches():
    df,sha=real_inputs()
    out=mod.study(df,source_sha256=sha)
    for species in out['results']:
        for mode in ('quadratic','absolute'):
            sort=species['fixed_hypothetical_response'][mode]['hypothetically_habitat_sorted_population']
            assert sort['fixed_weight_dominant_pressure_reversal'] is True
            assert [r['dominant_hypothetical_penalty'] for r in sort['regions']]==['moisture','thermal']
            assert all(0 < r['hypothetical_effective_occupied_cells'] <= n
                       for r,n in zip(sort['regions'],species['climate_cell_counts']))
    assert [[species['fixed_hypothetical_response'][mode]['sensitivity_grid']
             ['n_habitat_sorted_driver_reversals_under_fixed_weight'] for mode in ('quadratic','absolute')]
            for species in out['results']]==[[69,70],[104,103]]


def test_current_result_exact_regeneration():
    import json
    df,sha=real_inputs()
    observed=mod.study(df,source_sha256=sha)
    path=ROOT/'results/geographic_constraint_switch_geometry_v1.json'
    assert observed==json.loads(path.read_text())
