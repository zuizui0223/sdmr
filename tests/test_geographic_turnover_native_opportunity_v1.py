"""Reproducibility and exclusion conditions of *descriptive* climate opportunity."""
import importlib.util
from pathlib import Path
import pandas as pd
import pytest

p=Path(__file__).parents[1]/'experiments'/'geographic_turnover_opportunity_receipt_v1.py'
spec=importlib.util.spec_from_file_location('opportunity',p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _frame():
    values=[]
    regions=['quercus_DE_central','quercus_SE_south','pinus_ES_central','pinus_FI_central']
    temperatures=[[6,7,8,9],[5,6,7,8],[10,11,12,13],[2,3,4,5]]
    for r,temps in zip(regions,temperatures):
        for i,t in enumerate(temps):
            values.append(dict(region=r,cell_id=f'{r}:{i}',temperature=t,moisture=500+i*100))
    return pd.DataFrame(values)


def test_source_only_opportunity_and_disjoint_range():
    output=m.summarize(_frame(),source_sha='fixture_sha')
    assert output['no_biological_niche_shift_inference'] is True
    assert output['not_species_accessible_areas_M'] is True
    assert len(output['pairs'])==2
    pair=next(x for x in output['pairs'] if x['taxon']=='Pinus sylvestris')
    assert pair['temperature_raw_range_overlap_c']==0
    assert pair['areas']['pinus_ES_central']['n_25km_cells']==4


def test_missing_region_rejected_not_selected_posthoc():
    bad=_frame()
    bad=bad[bad.region!='pinus_FI_central']
    with pytest.raises(ValueError,match='no climate evidence'):
        m.summarize(bad,source_sha='fixture')


def test_duplicate_source_cell_rejected():
    bad=pd.concat([_frame(),_frame().iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match='duplicated'):
        m.summarize(bad,source_sha='fixture')
