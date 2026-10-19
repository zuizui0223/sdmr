"""First measured tree-response boundaries and contracts; synthetic fixtures only."""
from pathlib import Path
import io
import importlib.util
import json
import sqlite3
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('response',ROOT/'experiments/geographic_tree_demography_first_response_v1.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
SRC=ROOT/'evidence/geographic_tree_demography_source_gate_v1'


def sample_zip():
    text='CN,PREV_TRE_CN,SPCD,INVYR,PLT_CN,STATUSCD,DIA,DIAHTCD\n'
    text+=('a,,316.0,2010,plotA,1,5,1\n'
           'b,a,316.0,2015,plotB,1,6,1\n'
           'c,b,316.0,2020,plotC,2,,1\n'
           'd,,316.0,2010,plotA,1,10,1\n'
           'e,d,316.0,2015,plotB,3,,1\n'
           'f,,316.0,2010,plotA,2,7,1\n'
           'g,f,316.0,2015,plotB,2,0,1\n'
           'h,,316.0,2010,plotA,1,5,1\n'
           'i,h,316.0,2015,plotB,0,,1\n'
           'j,,316.0,2010,plotA,1,7,1\n'
           'k,j,316.0,2015,plotB,1,6,1\n'
           'q,,999.0,2010,plotA,1,1,1\n')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('RI_TREE.csv',text)
    return buf.getvalue()


def test_frozen_species_and_verified_sha_from_source_receipts():
    c=json.loads((ROOT/'configs/geographic_tree_demography_first_response_v1.json').read_text())
    wi=json.loads((SRC/'fia_wi_size_cap_successor_v2.json').read_text())
    cw=json.loads((SRC/'fia_official_species_crosswalk.json').read_text())
    out=mod.validate_contract(c,wi,cw)
    assert len(out['species_codes'])==13
    assert out['official_names']['316']=='Acer rubrum'
    assert out['sha_by_state']['RI'].startswith('222098c7')
    assert c['min_interval_years']==1


def test_source_drift_and_posthoc_taxon_addition_refused():
    c=json.loads((ROOT/'configs/geographic_tree_demography_first_response_v1.json').read_text())
    wi=json.loads((SRC/'fia_wi_size_cap_successor_v2.json').read_text())
    cw=json.loads((SRC/'fia_official_species_crosswalk.json').read_text())
    c['nominated_species_codes'].append(999)
    with pytest.raises(ValueError,match='cohort'):
        mod.validate_contract(c,wi,cw)
    c['nominated_species_codes'].pop()
    c['source_zip_sha256_by_state']['RI']='changed'
    with pytest.raises(ValueError,match='source'):
        mod.validate_contract(c,wi,cw)


def test_true_observed_death_not_inferred_from_missing_or_cut(tmp_path):
    z=tmp_path/'RI_TREE.zip';z.write_bytes(sample_zip())
    con=sqlite3.connect(':memory:')
    try:
        read=mod.read_selected_tree_rows(z,'RI_TREE.csv',con,{'316'})
        out=mod.summarize_linked_states(con,{'316':'Acer rubrum'},'RI')['taxa'][0]
        assert read['n_source_rows']==12 and read['n_selected_identity_rows']==11
        assert out['n_valid_forward_links']==6
        assert out['n_prior_live_linked']==5
        assert out['n_observed_live_to_live']==2
        assert out['n_observed_live_to_dead']==1
        assert out['n_removed_excluded']==1
        assert out['n_not_tallied_excluded']==1
        assert out['n_growth_pairs_with_diameter']==2
        assert out['median_annual_log_diameter_change'] is not None
    finally:con.close()


def test_negative_live_diameter_change_preserved_not_clipped(tmp_path):
    z=tmp_path/'RI_TREE.zip';z.write_bytes(sample_zip())
    con=sqlite3.connect(':memory:')
    try:
        mod.read_selected_tree_rows(z,'RI_TREE.csv',con,{'316'})
        out=mod.summarize_linked_states(con,{'316':'Acer rubrum'},'RI')['taxa'][0]
        assert out['size_band_growth_log_means']['5-<10']['n']==2
        # positive 5->6 and negative 7->6 both contribute
        import math
        expected=(math.log(6/5)+math.log(6/7))/5/2
        assert out['size_band_growth_log_means']['5-<10']['mean_annual_log_diameter_change']==pytest.approx(expected)
    finally:con.close()


def test_size_standardization_refuses_pseudo_precision():
    rows=[]
    for st in ('RI','VA','WI'):
        rows.append({'state':st,'taxa':[{'spcd':'316',
          'size_band_growth_log_means':{'1-<5':{'n':10,'mean_annual_log_diameter_change':0.5},
          '5-<10':{'n':35,'mean_annual_log_diameter_change':0.1},
          '10-<20':{'n':0,'mean_annual_log_diameter_change':None},
          '20+':{'n':0,'mean_annual_log_diameter_change':None}}}]})
    z=mod.standardize_size_across_states(rows,['316'])
    assert z['taxa'][0]['n_shared_size_bands']==1
    assert z['taxa'][0]['observed_size_standardized_mean_log_diameter_change_by_state']=={'RI':0.1,'VA':0.1,'WI':0.1}
