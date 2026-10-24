"""Source-first NOAA county climate validation; fixture data, no internet."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('noaa_county',ROOT/'experiments/fia_noaa_county_climate_source_v1.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
CONF = json.loads((ROOT/'configs/fia_noaa_county_climate_source_v1.json').read_text())


def fixture(fips, variable, year, monthly=None):
    code = '02' if variable=='temperature' else '01'
    vals=monthly if monthly is not None else ([68.0]*12 if variable=='temperature' else [4.0]*12)
    return (f'{fips}{code}{year:04d}  '+ '  '.join(str(x) for x in vals)+'\n').encode('ascii')


def test_source_and_explicit_FIPS_separate_from_climdiv_state_ordinal():
    mod.verify_contract(CONF)
    t,stats=mod.parse_climdiv_county(fixture('44007','temperature',2000),'temperature',CONF)
    p,_=mod.parse_climdiv_county(fixture('44007','precipitation',2000),'precipitation',CONF)
    assert stats['n_distinct_counties']==1
    assert ('44007',2000,4) in t
    assert t[('44007',2000,4)]==20.0
    assert p[('44007',2000,4)]==101.6
    assert not any(f[0]=='37007' for f in t)


def test_missing_month_not_imputed_as_zero():
    raw=[68.0]*12
    raw[3]=-99.99
    t,meta=mod.parse_climdiv_county(fixture('44007','temperature',2000,raw),'temperature',CONF)
    assert ('44007',2000,4) not in t
    assert meta['n_invalid_month_values']==1


def test_malformed_and_wrong_element_fail_closed():
    with pytest.raises(ValueError,match='element'):
        mod.parse_climdiv_county(fixture('44007','precipitation',2000),'temperature',CONF)
    with pytest.raises(ValueError,match='malformed'):
        mod.parse_climdiv_county(b'44007022000 67 44\n','temperature',CONF)
    doubled=fixture('44007','temperature',2000)*2
    with pytest.raises(ValueError,match='duplicate'):
        mod.parse_climdiv_county(doubled,'temperature',CONF)


def test_frozen_source_change_and_bad_FIPS_rejected():
    modified=dict(CONF);modified['states_fips']=dict(CONF['states_fips']);modified['states_fips']['RI']='37'
    with pytest.raises(ValueError,match='FIPS'):
        mod.verify_contract(modified)
    another=dict(CONF);another['snapshot']='latest'
    with pytest.raises(ValueError,match='snapshot'):
        mod.verify_contract(another)


def test_interval_measmon_boundaries_excluded_and_missing_fails():
    rows=[]
    for y in (2001,2002):
        for m in (4,5,6,7,8,9):rows.append(('44007',y,m,20+y-2001,100))
    res=mod.normalize_interval_exposure(rows,'44007',2001,4,2002,10)
    assert res['months']==11  # prior Apr omitted, later Apr..Sep included
    assert res['temperature_c_mean']>20
    assert res['precipitation_mm_per_six_months']==600
    assert mod.normalize_interval_exposure(rows,'44007',2001,4,2001,9) is None
    assert mod.normalize_interval_exposure(rows,'44003',2001,4,2002,10) is None
    incomplete=[r for r in rows if r[1:] != (2001,5,20,100)]
    assert mod.normalize_interval_exposure(incomplete,'44007',2001,4,2002,10) is None


def test_source_coverage_and_csv_hash_excludes_tree_results(tmp_path):
    config=dict(CONF);config['minimum_complete_counties']={'RI':1,'VA':1,'WI':1}
    input_config=tmp_path/'config.json'
    input_config.write_text(json.dumps(config))
    blobs={}
    for name in ('temperature','precipitation'):
        blob=b''
        for county in ('44007','51059','55025'):
            for y in range(1991,2026):blob+=fixture(county,name,y)
        blobs[name]=blob
    def fetch(url):
        return blobs['temperature' if 'tmpccy' in url else 'precipitation']
    out=tmp_path/'out'
    rcpt=mod.run(input_config,out,fetcher=fetch)
    assert rcpt['climate_csv_rows']==3*35*6
    assert rcpt['no_tree_or_growth_data_opened'] is True
    assert rcpt['coverage']['states']['VA']['n_counties_baseline_complete_25years']==1
    assert rcpt['climate_csv_sha256']==hashlib.sha256((out/'noaa_county_growing_months_1991_2025.csv').read_bytes()).hexdigest()
