"""Offline regressions for independent FIA TREE/PLOT/COND joining and controls."""
from pathlib import Path
import importlib.util
import json
import hashlib
import io
import zipfile
import pytest

SRC=Path(__file__).parents[1]/'experiments/fia_tree_plot_condition_join_v1.py'
s=importlib.util.spec_from_file_location('fia_joint',SRC)
mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)


def zip_file(name,s):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr(name,s)
    return b.getvalue()


def fake_fia(state,table):
    if table=='PLOT':
        return zip_file(state+'_PLOT.csv', 'CN,PREV_PLT_CN,INVYR,MEASYEAR,MEASMON,PLOT_STATUS_CD\n'
                'p1,,2015,2014,1,1\np2,p1,2020,2020,1,1\n')
    if table=='COND':
        return zip_file(state+'_COND.csv','PLT_CN,CONDID,STDAGE,STDORGCD,COND_STATUS_CD\n'
                'p1,1,62,0,1\np2,1,68,0,1\n')
    raise ValueError(table)


def fake_tree(state):
    return zip_file(state+'_TREE.csv','CN,PREV_TRE_CN,SPCD,PLT_CN,CONDID,INVYR,STATUSCD,DIA,DIAHTCD\n'
            'a,,316,p1,1,2015,1,6,1\nb,a,316,p2,1,2020,1,7,1\n'
            'c,,316,p1,1,2015,1,8,1\nd,c,316,p2,1,2020,2,,1\n'
            'e,,129,p1,1,2015,1,10,1\nf,e,129,p2,1,2020,1,12,1\n')


def test_dates_do_not_use_inventory_as_measurement():
    assert mod._valid_date(2020,1)==pytest.approx(2020+(1-.5)/12)
    assert mod._valid_date(2020,'') is None
    assert mod._valid_date(9999,1) is None


def test_independent_current_archive_growth_join(tmp_path):
    from hashlib import sha256
    years={}
    for st in mod.STATES:
        for tab in ('PLOT','COND'):
            data=fake_fia(st,tab);years[(st,tab)]=sha256(data).hexdigest()
    source={'n_states_complete':3,'states':[
        {'state':st,'status':'source_linked_metadata_ready',
         'plot':{'zip_sha256':years[(st,'PLOT')]},'cond':{'zip_sha256':years[(st,'COND')]}}
        for st in mod.STATES]}
    config={'study_id':'fia_measurement_date_stand_context_v1',
      'source_lineage':'independent_new_source_no_reuse_of_historical_tree',
      'states':list(mod.STATES),'species_codes':[68,129,261,316,318,371,531,541,743,762,802,833,837],
      'minimum_matched_pairs_per_common_stratum':10,
      'source_sha256':sha256(json.dumps(source,indent=2,sort_keys=True).encode()).hexdigest()}
    names={'candidate_crosswalk':{'taxa':[{'status':'official_reference_matched',
      'source_spcd_normalized':str(s),'scientific_name':f'Species {s}'} for s in config['species_codes']]}}
    for n,object_ in (('config',config),('source',source),('names',names)):
        (tmp_path/(n+'.json')).write_text(json.dumps(object_,indent=2,sort_keys=True)+'\n')
    output=mod.run(tmp_path/'config.json',tmp_path/'source.json',tmp_path/'names.json',tmp_path/'output.json',
                  fetch_plotcond=fake_fia,fetch_trees=fake_tree)
    assert len(output['states'])==3
    for state in output['states']:
        ac=next(x for x in state['species'] if x['spcd']=='316')
        assert ac['n_growth_pairs']==1
        assert ac['counters']['observed_dead']==1
        assert ac['counters']['inventory_vs_measurement_interval_different']==2
        assert ac['n_natural_stand_age_pairs']==1
        assert ac['size_age_strata']['5-<10|40-<80']['n']==1
        assert ac['mean_growth_measyear']<ac['mean_growth_invyr_same_pairs']
    assert output['no_causal_climate_or_niche_evolution_claim'] is True
    assert all(x['n_shared_size_age_strata']==0 for x in output['cross_state_size_stand_age_standardization'])


def test_frozen_source_fails_after_changed_plot(tmp_path):
    # Reuse fixture factory but mutate one source archive independently.
    p=tmp_path/'PLOT.zip';p.write_bytes(fake_fia('RI','PLOT'))
    m,fn=mod.source._fetch('RI','PLOT',tmp_path,fetcher=fake_fia)
    assert m['status']=='ready'
    assert m['zip_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()


def test_no_available_common_strata_is_missing_not_zero():
    states=[]
    for st in mod.STATES:
      bands={k:{'n':1,'mean_measyear_normalized':.01,'mean_invyr_normalized_same_pairs':.012}
             for k in ('1-<5|0-<40','1-<5|40-<80','1-<5|80+', '5-<10|0-<40','5-<10|40-<80','5-<10|80+',
                       '10-<20|0-<40','10-<20|40-<80','10-<20|80+','20+|0-<40','20+|40-<80','20+|80+')}
      states.append({'state':st,'species':[{'spcd':'316','size_age_strata':bands}]})
    x=mod.cross_state_standardize(states,['316'])[0]
    assert x['n_shared_size_age_strata']==0 and x['by_state']['RI']['measyear'] is None


def test_prior_natural_needed_for_natural_age_group(tmp_path):
    db=mod.sqlite3.connect(':memory:')
    try:
        t=tmp_path/'RI_TREE.zip';t.write_bytes(fake_tree('RI'))
        mod.parse_selected_tree(t,'RI_TREE.csv',db,{'316','129'})
        plots={'p1':{'previous':'','measure':2014.0,'invyr':2015},
               'p2':{'previous':'p1','measure':2020.0,'invyr':2020}}
        conds={('p1','1'):{'age':65,'origin':'1','forest':True},
               ('p2','1'):{'age':70,'origin':'1','forest':True}}
        x=mod.summarize_pairs(db,plots,conds,['316'])['species'][0]
        assert x['n_growth_pairs']==1
        assert x['n_natural_stand_age_pairs']==0
        assert x['counters']['not_confirmed_natural_both']==1
    finally:db.close()


def test_plot_chain_must_agree_with_tree_identity(tmp_path):
    db=mod.sqlite3.connect(':memory:')
    try:
        t=tmp_path/'RI_TREE.zip';t.write_bytes(fake_tree('RI'))
        mod.parse_selected_tree(t,'RI_TREE.csv',db,{'316'})
        plots={'p1':{'previous':'','measure':2014.0,'invyr':2015},
               'p2':{'previous':'other','measure':2020.0,'invyr':2020}}
        x=mod.summarize_pairs(db,plots,{},['316'])['species'][0]
        assert x['n_growth_pairs']==0 and x['counters']['plot_chain_not_identical']==2
    finally:db.close()
