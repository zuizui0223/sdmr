"""Independent contract checks for four-cell FIA physiographic moderation."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fia_moderation',ROOT/'experiments/fia_competition_moisture_interaction_v1.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SOURCE=ROOT/'evidence/fia_habitat_structure_extension_v1/aggregate.json'


def stub_source(group):
    states=[]
    for state in mod.STATES:
        species=[]
        for code in mod.SPECIES:
            species.append({'spcd':code,'size_age_density_physio':group if state=='VA' and code=='316' else {}})
        states.append({'state':state,'species':species})
    return {'states':states}


def four_classes(n=12, moisture_mod=0.01):
    return {
      '5-<10|40-<80|0-<60|xeric':{'n':n,'mean_growth':.04},
      '5-<10|40-<80|60-<120|xeric':{'n':n,'mean_growth':.01},
      '5-<10|40-<80|0-<60|mesic':{'n':n,'mean_growth':.04},
      '5-<10|40-<80|60-<120|mesic':{'n':n,'mean_growth':.01+moisture_mod}}


def test_did_sign_and_matching_four_complete_cells():
    d=mod.compute_panel(stub_source(four_classes()),min_per_cell=10)['density_pairs'][0]
    assert d['n_matched_four_cell_size_age_strata']==1
    assert d['n_strata_both_contexts_crowding_negative']==1
    assert d['n_mesic_weaker_strata']==1
    assert d['by_state']['RI']['eligible_species']==0
    assert d['by_state']['VA']['eligible_species']==1
    assert d['strata'][0]['mesic_minus_xeric_density_interaction']==pytest.approx(.01)
    assert d['n_species_states']==1


def test_negative_did_is_not_interpreted_as_a_positive_mesic_moderator():
    out=mod.compute_panel(stub_source(four_classes(moisture_mod=-.01)))['density_pairs'][0]
    assert out['n_mesic_weaker_strata']==0
    assert out['n_xeric_weaker_strata']==1
    assert out['strata'][0]['mesic_minus_xeric_density_interaction']==pytest.approx(-.01)


def test_no_missing_cell_or_low_sample_is_imputed():
    cells=four_classes()
    cells.pop('5-<10|40-<80|60-<120|mesic')
    assert mod.compute_panel(stub_source(cells))['density_pairs'][0]['n_matched_four_cell_size_age_strata']==0
    cells=four_classes()
    cells['5-<10|40-<80|60-<120|mesic']['n']=9
    assert mod.compute_panel(stub_source(cells))['density_pairs'][0]['n_matched_four_cell_size_age_strata']==0


def test_density_inequality_not_created_by_reweighting_dry_only():
    cells=four_classes(moisture_mod=-.01)
    cells['5-<10|40-<80|0-<60|xeric']['n']=8000
    cells['5-<10|40-<80|60-<120|mesic']['n']=11
    x=mod.compute_panel(stub_source(cells))['density_pairs'][0]['species_states'][0]
    assert x['min_four_cell_weighted_interaction']==pytest.approx(-.01)


def test_source_shas_and_taxa_frozen():
    obj=mod.load_verified_source(SOURCE)
    assert len(obj['states'])==3
    assert all(len(st['species'])==13 for st in obj['states'])


def test_source_mismatch_rejected(tmp_path):
    p=tmp_path/'changed.json';p.write_bytes(SOURCE.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='SHA-256'):
        mod.load_verified_source(p)


def test_actual_first_open_denominators_and_null_RI():
    obj=mod.summarize(mod.load_verified_source(SOURCE))
    z=obj['threshold_panels'][0]['density_pairs']
    assert [(r['n_matched_four_cell_size_age_strata'],r['n_strata_both_contexts_crowding_negative'],r['n_mesic_weaker_strata']) for r in z]==[(54,48,26),(94,79,43),(37,36,21)]
    assert [r['n_species_states'] for r in z]==[16,19,13]
    assert all(r['by_state']['RI']['eligible_species']==0 for r in z)
    assert obj['causal_climate_claim_authorized'] is False


def test_support_tightening_changes_denominators_without_promotion():
    obj=mod.summarize(mod.load_verified_source(SOURCE))
    for panel in obj['threshold_panels']:
        assert panel['minimum_per_each_of_four_cells'] in [10,20,30,50,100]
        for d in panel['density_pairs']:
            assert d['n_strata_both_contexts_crowding_negative']<=d['n_matched_four_cell_size_age_strata']
    assert [panel['density_pairs'][-1]['n_matched_four_cell_size_age_strata'] for panel in obj['threshold_panels']]==[37,20,13,8,2]


def test_exact_archived_summary_matches_output():
    observed=mod.summarize(mod.load_verified_source(SOURCE))
    frozen=json.loads((ROOT/'results/fia_density_physiography_moderation_v1.json').read_text())
    def compare(a,b):
      if isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:compare(a[k],b[k])
      elif isinstance(a,list):
        assert len(a)==len(b)
        for v,w in zip(a,b):compare(v,w)
      elif isinstance(a,(float,int)) and not isinstance(a,bool):
        assert a==pytest.approx(b,rel=1e-10,abs=1e-12)
      else: assert a==b
    compare(observed,frozen)


def test_cross_state_eight_cell_geometry_and_sign_sensitivity():
    src=mod.load_verified_source(SOURCE)
    out=mod.summarize(src)
    primary=out['matched_across_states_eight_cell_sensitivity'][0]['comparisons']
    assert [(x['n_same_size_age_eight_cell_comparisons'],x['n_opposite_moderation_sign']) for x in primary]==[(12,9),(27,11),(8,4)]
    assert [x['retrospective_magnitude_sensitivity'][2]['n_same_size_age_eight_cell_comparisons'] for x in primary]==[6,4,2]
    assert [x['retrospective_magnitude_sensitivity'][2]['n_opposite_moderation_sign'] for x in primary]==[5,2,1]
    assert all(x['n_species_in_comparison']>0 for x in primary)
    assert out['causal_climate_claim_authorized'] is False
