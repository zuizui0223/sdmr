"""Tests use outcome-neutral synthetic source; never request live FIA archives."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fia_climate_tree_source_gate_v3',ROOT/'experiments/fia_climate_tree_source_gate_v3.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_zip(state,table,columns,rows):
    text=','.join(columns)+'\n'+'\n'.join(','.join(map(str,r)) for r in rows)+'\n'
    buf=io.BytesIO()
    with ZipFile(buf,'w') as z:z.writestr(f'{state}_{table}.csv',text)
    return buf.getvalue()


def test_noaa_exposure_boundary_months_excluded():
    index={('44001',y,m):(float(y-2000),float(m)) for y in range(2000,2003) for m in range(4,10)}
    r=mod.interval_exposure(index,'44001',(2000,4),(2002,9))
    assert r['n_months']==16
    assert r['temperature_c']==pytest.approx((5*0+6*1+5*2)/16)
    assert mod.interval_exposure(index,'44001',(2002,9),(2000,4)) is None
    del index[('44001',2001,5)]
    assert mod.interval_exposure(index,'44001',(2000,4),(2002,9)) is None


def test_same_county_plot_chain_and_unknown_date_are_not_zero(tmp_path):
    index={('44001',y,m):(8.,120.) for y in range(2000,2003) for m in range(4,10)}
    p=tmp_path/'RI_PLOT.zip'
    p.write_bytes(make_zip('RI','PLOT',['CN','PREV_PLT_CN','STATECD','COUNTYCD','MEASYEAR','MEASMON'],[
      ['a','',44,1,2000,3],['b','a',44,1,2002,10],['c','a',44,1,2002,''],['d','a',44,3,2002,10]]))
    eligible,counts=mod.read_plots(p,'RI_PLOT.csv','RI',index)
    assert len(eligible)==1
    assert eligible['b'][0]=='a'
    assert counts['invalid_county_or_date']==1
    assert counts['county_drift_or_missing']>=1


def test_condition_columns_missing_hard_error(tmp_path):
    z=tmp_path/'RI_COND.zip';z.write_bytes(make_zip('RI','COND',['PLT_CN','CONDID'],[['a',1]]))
    with pytest.raises(ValueError,match='COND missing'):
      mod.read_conds(z,'RI_COND.csv')


def test_tree_selected_links_use_no_status_or_diameter(tmp_path):
    cols=['CN','PREV_TRE_CN','SPCD','PLT_CN','CONDID','INVYR','STATUSCD','DIA']
    rows=[['t1','',316,'a',1,2000,1,4.5],['t2','t1',316,'b',1,2002,2,7.0],
          ['t3','t1',802,'b',1,2002,1,100.0],['other','',99,'a',1,2000,1,22.],
          ['wrong','t1',316,'b',1,1999,1,22.]]
    z=tmp_path/'RI_TREE.zip';z.write_bytes(make_zip('RI','TREE',cols,rows))
    exp={'b':('a','44001',{'n_months':16})}
    valid={('a','1'),('b','1')}
    a,b=mod.source_tree_links(z,'RI_TREE.csv',exp,valid)
    assert b['316']['n_source_forward_same_species_links']==1
    assert b['316']['n_plot_climate_eligible_links']==1
    assert b['316']['n_natural_forest_with_age_and_density']==1
    # Biological outcomes are deliberately never accessed, despite changed values.
    rows[0][-2:]=[2,None];rows[1][-2:]=[3,0.0]
    z.write_bytes(make_zip('RI','TREE',cols,rows))
    aa,bb=mod.source_tree_links(z,'RI_TREE.csv',exp,valid)
    assert (a,b)==(aa,bb)


def test_fia_source_filenames_fixed_and_coverage_limit(tmp_path):
    payload=make_zip('RI','TREE',['CN','PREV_TRE_CN','SPCD','PLT_CN','CONDID','INVYR'],[['x','',316,'p',1,2000]])
    r,path=mod.fetch_zip('RI','TREE',tmp_path,fetcher=lambda a,b:payload)
    assert r['status']=='ready' and r['sha256']==hashlib.sha256(payload).hexdigest()
    assert r['member']=='RI_TREE.csv'
    with pytest.raises(ValueError):mod.fetch_zip('NY','TREE',tmp_path)


def test_original_successor_requires_no_response_and_source_sha(tmp_path):
    clim=tmp_path/'climate.csv';clim.write_bytes(b'fips_county,year,month,temperature_c,precipitation_mm\n')
    count=mod.sha(clim)
    succ={'study':'fia_noaa_new_plot_version_successor_v2','n_new_source_complete_states':3,
          'original_frozen_TREE_growth_not_reanalysed':True,
          'states':[{'state':s,'status':'successor_new_plot_climate_ready','new_plot_source_sha256':'a'*64} for s in mod.STATES]}
    receipt={'study':'fia_noaa_county_climate_pre_response_v1','climate_csv_rows':43890,'climate_csv_sha256':count}
    assert list(mod.verify_inputs(succ,receipt,clim))==list(mod.STATES)
    succ['states'][1]['new_plot_source_sha256']='b'*63
    with pytest.raises(ValueError,match='SHA'):mod.verify_inputs(succ,receipt,clim)
    succ['states'][1]['new_plot_source_sha256']='a'*64
    receipt['climate_csv_sha256']='0'*64
    with pytest.raises(ValueError,match='CSV changed'):mod.verify_inputs(succ,receipt,clim)


def test_result_contains_all_species_even_with_missing_source(tmp_path):
    assert len(mod.SPECIES)==13 and len(set(mod.SPECIES))==13
    assert set(mod.STATES)=={'RI','VA','WI'}
    assert all(len(v)==2 for v in mod.FIPS.values())
