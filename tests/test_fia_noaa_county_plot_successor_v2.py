"""Source-version break tests never read growth or mortality."""
from __future__ import annotations
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('new_fia_plot',ROOT/'experiments/fia_noaa_county_plot_successor_v2.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def plot_zip(state):
    fips={'RI':'44','VA':'51','WI':'55'}[state]
    text=('CN,PREV_PLT_CN,STATECD,COUNTYCD,MEASYEAR,MEASMON\n'
          f'{state}a,,{fips},7,2001,3\n'
          f'{state}b,{state}a,{fips},7,2002,10\n')
    raw=io.BytesIO()
    with ZipFile(raw,'w') as z:z.writestr(state+'_PLOT.csv',text)
    return raw.getvalue()


def synthetic_data(tmp_path):
    z={s:plot_zip(s) for s in m.STATES}
    old={'study':'fia_noaa_county_plot_chain_coverage_v1','n_states_join_complete':0,
         'n_tree_growth_observations_opened':0,'no_climate_density_effect_or_causal_inference':True,
         'states':[{'state':s,'status':'source_unavailable_or_changed',
                    'source_expected_sha256':'f'*64,
                    'actual_sha256':hashlib.sha256(z[s]).hexdigest()} for s in m.STATES]}
    cl=tmp_path/'c.csv'
    cl.write_text('fips_county,year,month,temperature_c,precipitation_mm\n'+
        ''.join(f'{fips}007,{y},{month},20.0,100.0\n' for fips in ('44','51','55')
                for y in (2001,2002) for month in range(4,10)))
    cmeta={'study':'fia_noaa_county_climate_pre_response_v1','no_tree_or_growth_data_opened':True,
           'climate_csv_sha256':hashlib.sha256(cl.read_bytes()).hexdigest(),'climate_csv_rows':36}
    receipt=tmp_path/'climate.json';receipt.write_text(json.dumps(cmeta))
    old['original_noaa_climate_source_sha256']=hashlib.sha256(receipt.read_bytes()).hexdigest()
    stop=tmp_path/'stop.json';stop.write_text(json.dumps(old))
    return z,stop,cl,receipt


def test_exact_new_plot_cohort_eligible_and_not_historical(tmp_path):
    z,stop,cl,receipt=synthetic_data(tmp_path)
    out=m.run(stop,cl,receipt,tmp_path/'out.json',getter=lambda state,table:z[state])
    assert out['n_new_source_complete_states']==3
    assert out['original_frozen_TREE_growth_not_reanalysed']
    assert [r['climate_linkage']['n_county_climate_eligible_plot_links'] for r in out['states']]==[1,1,1]


def test_new_source_drift_fails_without_substituting_old_denominator(tmp_path):
    z,stop,cl,receipt=synthetic_data(tmp_path)
    out=m.run(stop,cl,receipt,tmp_path/'out.json',getter=lambda state,table:z[state]+b'garbage')
    assert out['n_new_source_complete_states']==0
    assert all(r['status']=='new_plot_source_changed_again_stop' for r in out['states'])


def test_original_source_mismatch_must_exist(tmp_path):
    z,stop,cl,receipt=synthetic_data(tmp_path)
    r=json.loads(stop.read_text());r['states'][0]['source_expected_sha256']=r['states'][0]['actual_sha256']
    stop.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='mismatch'):
        m.run(stop,cl,receipt,tmp_path/'out.json',getter=lambda state,table:z[state])


def test_original_noaa_source_digest_cannot_change(tmp_path):
    z,stop,cl,receipt=synthetic_data(tmp_path)
    dat=json.loads(stop.read_text());dat['original_noaa_climate_source_sha256']='f'*64
    stop.write_text(json.dumps(dat))
    with pytest.raises(ValueError,match='NOAA climate receipt'):
        m.run(stop,cl,receipt,tmp_path/'out.json',getter=lambda state,table:z[state])
