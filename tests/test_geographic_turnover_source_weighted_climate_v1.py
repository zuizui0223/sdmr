import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

p=Path(__file__).parents[1]/'experiments'/'geographic_turnover_source_weighted_climate_v1.py'
spec=importlib.util.spec_from_file_location('weighted',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def example():
    return pd.DataFrame({
        'region':['A','A','B','B'],
        'cell_id':['1','2','3','4'],
        'temperature':[1.,2.,3.,4.],
        'moisture':[100.,200.,300.,400.],
        'n_focal_records_diagnostic':[2,0,None,None],
        'n_independent_target_group_records_diagnostic':[1,1,None,None]
    })


def test_missing_focal_not_relabelled_zero():
    v=m.study(example(),source_sha256='sha')
    assert v['n_climate_regions']==2
    assert v['n_regions_with_both_record_sources']==1
    b=next(z for z in v['windows'] if z['region']=='B')
    assert b['source_complete'] is False
    assert 'source_climate_means' not in b


def test_complete_means_and_both_comparator_types():
    a=example().loc[:1].copy()
    v=m.study(a,source_sha256='fixture')['windows'][0]
    assert v['source_complete']
    assert v['n_cells_focal_positive']==1
    assert v['source_climate_means']['equal_area_available_cells']['temperature']==1.5
    assert v['source_climate_means']['focal_record_weighted']['temperature']==1
    assert v['source_climate_means']['independent_sentinel_record_weighted']['temperature']==1.5
    assert v['focal_minus_sentinel']['moisture']==-50


def test_nonfinite_climate_value_rejected():
    a=example().loc[:1].copy()
    a.loc[0,'temperature']=np.nan
    with pytest.raises(ValueError,match='nonfinite'):
        m.study(a,source_sha256='fixture')


def test_source_id_duplicates_rejected():
    a=example().loc[:1].copy()
    a=pd.concat([a,a.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match='duplicate'):
        m.study(a,source_sha256='fixture')
