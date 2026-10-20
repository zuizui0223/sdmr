"""Archived source-v2 FIA results: exact no-refit audit and scientific ceilings."""
from pathlib import Path
import hashlib
import importlib.util
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'experiments/fia_stand_context_synthesis_v1.py'
s=importlib.util.spec_from_file_location('stand_synth',p)
mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)
DATA=ROOT/'evidence/fia_new_source_stand_context_v1/aggregate.json'


def test_authoritative_archived_only():
    raw=DATA.read_bytes()
    out=mod.inspect(json.loads(raw),byte_sha=hashlib.sha256(raw).hexdigest())
    assert out['n_species']==13
    assert out['n_total_measurement_pairs']==308097
    assert out['n_total_natural_stand_age_pairs']==295391
    assert out['contrast_primary_min_n10']['n_estimable_species']==13
    assert out['contrast_primary_min_n10']['n_species_WI_growth_higher']==12
    assert out['contrast_primary_min_n10']['n_matched_strata']==61
    assert out['contrast_primary_min_n10']['n_matched_strata_WI_higher']==53
    assert out['contrast_primary_min_n10']['n_species_direction_switch_after_real_measyear']==0
    assert out['no_species_physiological_climate_or_niche_evolution_inference']


def test_missing_or_replaced_input_denied():
    raw=DATA.read_bytes()
    with pytest.raises(ValueError,match='fingerprint'):
        mod.inspect(json.loads(raw),byte_sha='other')


def test_missing_stand_age_is_not_zero_growth():
    raw=DATA.read_bytes(); o=json.loads(raw)
    code='316'
    for st in o['states']:
        for spec in st['species']:
            if spec['spcd']==code:
                for cell in spec['size_age_strata'].values():
                    cell['n']=0;cell['mean_measyear_normalized']=None;cell['mean_invyr_normalized_same_pairs']=None
    x=mod.stratum_summary(o['states'],[code],o['names'],10)
    assert x['n_estimable_species']==0
    assert x['species'][0]['size_age_standardized_rates']['WI']['measyear'] is None


def test_minimum_eligibility_sensitivity_never_changes_frozen_denominator():
    o=json.loads(DATA.read_text())
    results={n:mod.stratum_summary(o['states'],mod.EXPECTED_CODES,o['names'],n) for n in (10,20,30,50,100)}
    assert [results[n]['n_estimable_species'] for n in (10,20,30,50,100)]==[13,10,7,6,5]
    assert [results[n]['n_species_WI_growth_higher'] for n in (10,20,30,50,100)]==[12,8,6,6,5]


def test_schema_hash_and_denominator_do_not_allow_silent_rescue():
    o=json.loads(DATA.read_text());o['plot_cond_source_receipt_sha256']='changed'
    with pytest.raises(ValueError,match='source drift'):
        mod.inspect(o,byte_sha=mod.EXPECTED_INPUT_SHA256)


def test_snapshot_reproduction_exact():
    raw=DATA.read_bytes();observed=mod.inspect(json.loads(raw),byte_sha=hashlib.sha256(raw).hexdigest())
    expected=json.loads((ROOT/'results/fia_new_source_stand_context_synthesis_v1.json').read_text())
    assert observed==expected
