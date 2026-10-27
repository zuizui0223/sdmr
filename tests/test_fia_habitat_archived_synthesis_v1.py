"""Frozen FIA habitat aggregate, re-derivation and non-promotion boundaries."""
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('habitat_archive', ROOT/'experiments/fia_habitat_archived_synthesis_v1.py')
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
SRC=ROOT/'evidence/fia_habitat_structure_extension_v1/aggregate.json'


def test_frozen_source_and_entire_denominator():
    source=mod.verify_source(SRC)
    assert len(source['states'])==3
    assert all(len(st['species'])==13 for st in source['states'])
    assert source['raw_tree_zip_source_hashes_verified'] is True
    assert source['no_causal_moisture_limitation_or_growth_process_claim'] is True


def test_archive_hash_change_stops(tmp_path):
    copy=tmp_path/'aggregate.json'
    copy.write_bytes(SRC.read_bytes()+b' ')
    with pytest.raises(ValueError,match='SHA-256'):
        mod.verify_source(copy)


def test_underpowered_groups_are_not_filled():
    states=[]
    for st in mod.STATES:
        states.append({'state':st,'species':[{'spcd':'316','size_age_density':{
            '5-<10|40-<80|60-<120':{'n':9 if st=='RI' else 500,'mean_growth':0.02},
            '10-<20|40-<80|60-<120':{'n':15,'mean_growth':0.01},
        }}]})
    rows=mod.eligible_rows(states,'316','size_age_density',10)
    assert len(rows)==1 and rows[0]['stratum'].startswith('10-<20')
    assert mod.eligible_rows(states,'316','size_age_density',20)==[]
    assert mod.standardized([])['WI_minus_RI'] is None


def test_three_standardizations_retain_direction_for_symmetric_strata():
    rows=[{'stratum':'a','counts':[10,10,500], 'means':[.01,.02,.03]},
          {'stratum':'b','counts':[20,20,20], 'means':[.02,.03,.04]}]
    for weight in ('pooled','equal','balanced_min'):
        r=mod.standardized(rows,weight)
        assert r['n_common_strata']==2 and r['WI_gt_RI'] is True
        assert r['WI_minus_RI']==pytest.approx(.02)


def test_archive_reruns_original_baselines_without_refitting():
    source=mod.verify_source(SRC)
    mod._assert_old_metrics(source)
    obj=mod.summarize(source)
    a=obj['regional_sensitivity']['size_age_density'][0]
    b=obj['regional_sensitivity']['size_age_physio'][0]
    assert a['eligible_species']==12 and a['WI_greater_RI_pooled']==10
    assert a['n_shared_strata']==76 and a['n_shared_strata_WI_gt_RI']==63
    assert b['eligible_species']==13 and b['WI_greater_RI_pooled']==11
    assert obj['physiography']['n_eligible_species_state']==21
    assert obj['physiography']['species_with_sign_reversal_VA_WI']==4


def test_stricter_threshold_decreases_availability_and_retains_sensitivity_labels():
    result=mod.summarize(mod.verify_source(SRC))
    for group in ('size_age_density','size_age_physio'):
        scenarios=result['regional_sensitivity'][group]
        assert [x['min_n_per_state_stratum'] for x in scenarios]==list(mod.THRESHOLDS)
        assert all(a['eligible_species']>=b['eligible_species'] for a,b in zip(scenarios,scenarios[1:]))
        for scenario in scenarios:
            assert scenario['WI_greater_RI_pooled']<=scenario['eligible_species']
            assert scenario['WI_greater_RI_balanced_min']<=scenario['eligible_species']
            assert scenario['n_shared_strata_WI_gt_RI']<=scenario['n_shared_strata']


def test_no_rhode_island_mesic_xeric_support():
    x=mod.summarize(mod.verify_source(SRC))['physiography']
    assert x['region_counts']['RI']=={'estimable':0,'positive':0}
    assert x['species_observed_in_VA_and_WI']==9
    assert x['species_with_sign_reversal_VA_WI']==4
    assert x['region_counts']['VA']=={'estimable':11,'positive':6}
    assert x['region_counts']['WI']=={'estimable':10,'positive':6}


def test_within_state_density_gradient_contrasts_are_recomputed():
    source=mod.verify_source(SRC)
    d=mod.matched_density_gradient(source['states'],minimum=10)
    a,b,c=d['contrast_groups']
    assert (a['n_species_states_higher_density_growth_lower'],a['n_species_states'])==(27,27)
    assert (b['n_species_states_higher_density_growth_lower'],b['n_species_states'])==(33,33)
    assert (c['n_species_states_higher_density_growth_lower'],c['n_species_states'])==(27,27)
    assert (a['n_strata_higher_density_growth_lower'],a['n_matched_strata'])==(225,244)
    assert (b['n_strata_higher_density_growth_lower'],b['n_matched_strata'])==(337,385)
    assert d['three_density_classes']['n_strict_monotone_decreases']==184
    assert d['three_density_classes']['n_strata_with_all_three']==205


def test_denser_strata_support_does_not_invent_independent_experiments():
    x=mod.summarize(mod.verify_source(SRC))
    d=x['within_state_density_gradient_sensitivity']
    assert [r['minimum_live_to_live_pairs_per_density_group'] for r in d]==list(mod.THRESHOLDS)
    assert [r['three_density_classes']['n_strata_with_all_three'] for r in d]==[205,140,118,83,43]
    assert [r['three_density_classes']['n_strict_monotone_decreases'] for r in d]==[184,130,112,81,43]
    assert all(q['n_strata_higher_density_growth_lower']<=q['n_matched_strata']
               for z in d for q in z['contrast_groups'])


def test_synthetic_density_strata_strictly_compares_source_classes():
    states=[]
    for st in mod.STATES:
        classes={'1-<5|40-<80|0-<60|mesic':{'n':20,'mean_growth':.025},
                 '1-<5|40-<80|60-<120|mesic':{'n':25,'mean_growth':.015},
                 '1-<5|40-<80|120+|mesic':{'n':28,'mean_growth':.009}}
        states.append({'state':st,'species':[{'spcd':'316','size_age_density_physio':classes}]})
    z=mod.matched_density_gradient(states,minimum=10)
    assert z['three_density_classes']['n_strict_monotone_decreases']==3
    assert all(c['n_species_states_higher_density_growth_lower']==3 for c in z['contrast_groups'])
    assert mod.matched_density_gradient(states,minimum=30)['three_density_classes']['n_strata_with_all_three']==0
