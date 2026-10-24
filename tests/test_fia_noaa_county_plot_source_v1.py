from __future__ import annotations
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path
import pytest

ROOT=Path(__file__).parents[1]
s=importlib.util.spec_from_file_location('join_gate',ROOT/'experiments/fia_noaa_county_plot_source_v1.py')
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)


def make_zip():
    src=('CN,PREV_PLT_CN,STATECD,COUNTYCD,MEASYEAR,MEASMON\n'
         'r1,,44,7,2001,3\n'
         'r2,r1,44,7,2002,10\n'
         'r3,r2,44,7,2003,6\n'
         'r4,r2,44,9,2003,10\n')
    dst=io.BytesIO()
    with zipfile.ZipFile(dst,'w') as zip:
        zip.writestr('RI_PLOT.csv',src)
    return dst.getvalue()


def make_climate():
    return {('44007',y,m):(20,100) for y in (2001,2002,2003) for m in range(4,10)}


def test_fia_plot_fips_is_not_noaa_ordinal_and_interval():
    p=make_zip()
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp:
        path=Path(tmp)/'RI_PLOT.zip';path.write_bytes(p)
        data,a=m.parse_plots(path,'RI_PLOT.csv','RI')
    assert a['n_plot_rows']==4
    assert data['r2'][1]=='44007'
    r=m.summarize_plot_chain(data,make_climate(),'RI')
    assert r['n_county_climate_eligible_plot_links']==1
    assert r['exclusions']['county_changed_between_censuses']==1
    assert r['exclusions']['climate_not_complete_in_two_census_interval']==1


def test_missing_plot_county_or_source_climate_refused():
    assert m.interval_climate(make_climate(),'44099',(2001,3),(2002,10)) is None
    assert m.interval_climate(make_climate(),'44007',(2001,4),(2001,9)) is None
    assert m.interval_climate(make_climate(),'44007',(2001,3),(2002,10))[0]==12


def test_load_exact_climate_source_shas_fail_closed(tmp_path):
    data='fips_county,year,month,temperature_c,precipitation_mm\n44007,2001,4,20,100\n'
    c=tmp_path/'climate.csv';c.write_text(data)
    receipt={'study':'fia_noaa_county_climate_pre_response_v1','no_tree_or_growth_data_opened':True,
             'climate_csv_sha256':hashlib.sha256(c.read_bytes()).hexdigest(),'climate_csv_rows':1}
    p=tmp_path/'r.json';p.write_text(json.dumps(receipt))
    x,_=m.load_climate(c,p)
    assert x[('44007',2001,4)]==(20.0,100.0)
    c.write_text(data+' ') 
    with pytest.raises(ValueError,match='checksum'):
        m.load_climate(c,p)


def test_source_archive_identity_fail_closed(tmp_path):
    data=make_zip()
    p=tmp_path/'plot.zip';p.write_bytes(data)
    src=tmp_path/'receipt.json'
    src.write_text(json.dumps({'n_states_complete':3,'states':[
        {'state':name,'plot':{'zip_sha256':'inaccessible'}} for name in ('RI','VA','WI')]}))
    c=tmp_path/'climate.csv'
    c.write_text('fips_county,year,month,temperature_c,precipitation_mm\n44007,2001,4,20,100\n')
    clim=tmp_path/'source.json';clim.write_text(json.dumps({
        'study':'fia_noaa_county_climate_pre_response_v1','no_tree_or_growth_data_opened':True,
        'climate_csv_rows':1,'climate_csv_sha256':hashlib.sha256(c.read_bytes()).hexdigest()}))
    out=m.run(src,c,clim,tmp_path/'output.json',getter=lambda st,table:data)
    assert out['n_states_join_complete']==0
    assert all(x['status']=='source_unavailable_or_changed' for x in out['states'])
    assert out['n_tree_growth_observations_opened']==0
