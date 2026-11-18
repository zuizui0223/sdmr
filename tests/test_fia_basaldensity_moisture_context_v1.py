"""Natural-forest basal area and physiographic site-matching semantics."""
import importlib.util
from pathlib import Path
import io
import json
import sqlite3
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('habitat',ROOT/'experiments/fia_basaldensity_moisture_context_v1.py')
mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)


def zipfile_made(name,contents):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr(name,contents)
    return b.getvalue()


def test_official_physiography_mapping_strict():
    assert mod.physiographic('11')=='xeric'
    assert mod.physiographic('19')=='xeric'
    assert mod.physiographic('21')=='mesic'
    assert mod.physiographic('29')=='mesic'
    assert mod.physiographic('31')=='hydric'
    assert mod.physiographic('39')=='hydric'
    assert mod.physiographic('9') is None
    assert mod.physiographic('') is None


def test_exact_condition_join_and_missing_basal_area(tmp_path):
    p=tmp_path/'RI_COND.zip'
    p.write_bytes(zipfile_made('RI_COND.csv','PLT_CN,CONDID,STDAGE,STDORGCD,COND_STATUS_CD,BALIVE,PHYSCLCD\n'
                         'p1,1,60,0,1,50,12\np2,1,65,0,1,100,22\np3,1,70,0,1,,33\n'))
    r=mod.parse_context(p,'RI_COND.csv')
    assert r[('p1','1')]['age']==60
    assert r[('p1','1')]['basal_area_ft2_ac']==50
    assert r[('p2','1')]['phys']=='mesic'
    assert r[('p3','1')]['basal_area_ft2_ac'] is None
    assert r[('p3','1')]['phys']=='hydric'


def test_source_missing_context_flag_fail_closed(tmp_path):
    p=tmp_path/'RI_COND.zip';p.write_bytes(zipfile_made('RI_COND.csv','PLT_CN,CONDID,STDAGE,STDORGCD,COND_STATUS_CD\np1,1,60,0,1\n'))
    with pytest.raises(ValueError,match='BALIVE'):
        mod.parse_context(p,'RI_COND.csv')


def test_stand_density_gains_require_within_stratum_balance():
    summaries=[]
    for name,shift in zip(mod.STATES,[0.0,0.001,0.003]):
        summaries.append({'state':name,'species':[{'spcd':'316','size_age_density':{
           '5-<10|40-<80|60-<120':{'n':40,'mean_growth':0.01+shift},
           '10-<20|80+|120+':{'n':2,'mean_growth':0.04+shift}},
           'size_age_physio':{},'size_age_density_physio':{}}]})
    result=mod.regional_standardize(summaries,['316'],min_n=10)[0]
    assert result['n_common_strata']==1
    assert result['WI_higher_RI'] is True
    assert result['state_means']['RI']==pytest.approx(.01)


def test_unavailable_comparison_returns_null_not_zero():
    summaries=[]
    for name in mod.STATES:
        summaries.append({'state':name,'species':[{'spcd':'316','size_age_density':{},
                     'size_age_physio':{},'size_age_density_physio':{}}]})
    result=mod.regional_standardize(summaries,['316'],min_n=10)[0]
    assert result['n_common_strata']==0
    assert result['state_means']['WI'] is None
    assert result['WI_higher_RI'] is None


def test_mesic_vs_xeric_requires_matched_size_age_density():
    summaries=[]
    for state in mod.STATES:
      records={
          '5-<10|40-<80|60-<120|mesic':{'n':20,'mean_growth':.04},
          '5-<10|40-<80|60-<120|xeric':{'n':20,'mean_growth':.02},
          '5-<10|80+|60-<120|mesic':{'n':100,'mean_growth':.05}}
      summaries.append({'state':state,'species':[{'spcd':'316','size_age_density_physio':records,
                 'size_age_density':{},'size_age_physio':{}}]})
    z=mod.moisture_site_within_state(summaries,['316'],min_n=10)
    assert len(z)==3
    assert all(x['n_common_stand_size_density_groups']==1 for x in z)
    assert all(x['mesic_minus_xeric_growth']==pytest.approx(.02) for x in z)


def test_predeclared_metadata_and_archived_tree_source_available():
    config=json.loads((ROOT/'configs/fia_habitat_structure_extension_v1.json').read_text())
    import hashlib
    frozen=ROOT/'evidence/fia_new_source_stand_context_v1/aggregate.json'
    assert hashlib.sha256(frozen.read_bytes()).hexdigest()==config['tree_result_sha256']
    assert len(config['species_codes'])==13
    assert config['minimum_eligible_source_pairs_per_state_stratum']==10
