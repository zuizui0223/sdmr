"""Offline test for future source diagnostic, does not open any real ecology result."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).parents[1] / 'experiments' / 'geographic_turnover_native_windows_v1.py'
spec = importlib.util.spec_from_file_location('native_windows', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CFG = json.loads((Path(__file__).parents[1] / 'configs' / 'geographic_turnover_native_windows_v1.json').read_text())


def test_fixed_windows_and_native_status_provenance():
    m.validate_config(CFG)
    assert len(CFG['windows']) == 4
    assert len(set(w['region'] for w in CFG['windows'])) == 4
    assert all(w['focal_taxon'] not in CFG['target_group_names'] for w in CFG['windows'])


def test_grid_is_equal_area_fixed_and_distinct_spatial_blocks():
    pytest.importorskip('pyproj')
    for w in CFG['windows']:
        g = m.equal_area_grid(w, CFG['cell_side_km'])
        assert not g.empty
        assert len(g) == len(set(g.cell_id))
        assert all((g.longitude >= w['west']) & (g.longitude < w['east']))
        assert all((g.latitude >= w['south']) & (g.latitude < w['north']))
        assert len(set(g.spatial_block)) == 4
        r = g.iloc[:min(10,len(g))]
        pts = pd.DataFrame({'longitude':r.longitude,'latitude':r.latitude})
        assert m._coord_to_cell(pts,w,CFG['cell_side_km']).tolist() == r.cell_id.tolist()


def test_missing_uncertainty_not_silently_set_to_zero_and_dedup():
    raw = pd.DataFrame([
        {'gbifID': '1', 'species': 'Quercus robur', 'basisOfRecord':'HUMAN_OBSERVATION',
         'longitude': 10, 'latitude': 51, 'coordinateUncertaintyInMeters':100},
        {'gbifID':'1', 'species':'Quercus robur','basisOfRecord':'HUMAN_OBSERVATION',
         'longitude':10,'latitude':51, 'coordinateUncertaintyInMeters':100},
        {'gbifID':'2','species':'Quercus robur','basisOfRecord':'HUMAN_OBSERVATION',
         'longitude':10,'latitude':51, 'coordinateUncertaintyInMeters':None},
        {'gbifID':'3','species':'Quercus robur','basisOfRecord':'MATERIAL_SAMPLE',
         'longitude':10,'latitude':51,'coordinateUncertaintyInMeters':100},
    ])
    clean, qc = m.clean_gbif_records(raw, CFG, focal_name='Quercus robur')
    assert clean.gbifID.tolist() == ['1']
    assert qc['rejection_reasons'] == {'disallowed_basis_of_record':1,
                                       'missing_coordinates_or_reported_uncertainty':1,
                                       'missing_or_duplicate_gbif_id':1}


def test_incomplete_api_gate_is_not_treated_as_complete():
    class Stub:
        calls=0
        def __call__(self, key, **kwargs):
            self.calls+=1
            return SimpleNamespace(total_count=9000, query_sha256='sha')
    stub=Stub()
    matcher=lambda name,**kw: SimpleNamespace(taxon_key='GBIF_KEY',canonical_name=name,status='ACCEPTED',checklist_key=kw['checklist_key'])
    frame, entry=m._search_once(query_name='Quercus robur',window=CFG['windows'][0],config=CFG,
                                matcher=matcher,fetcher=stub)
    assert frame is None and entry['status'] == 'bulk_required_count_over_diagnostic_cap'
    assert stub.calls == 1


def test_truncated_api_is_never_accepted():
    def fetcher(*args,**kw):
        if kw.get('max_records') == 1:
            return SimpleNamespace(total_count=5,query_sha256='count')
        return SimpleNamespace(total_count=5,retrieved_count=4,truncated=True,query_sha256='full',records=pd.DataFrame())
    matcher=lambda name,**kw: SimpleNamespace(taxon_key='GBIF_KEY',canonical_name=name,status='ACCEPTED',checklist_key=kw['checklist_key'])
    frame,entry=m._search_once(query_name='Quercus robur',window=CFG['windows'][0],config=CFG,
                               matcher=matcher,fetcher=fetcher)
    assert frame is None
    assert entry['status'] == 'incomplete_search_archive'


def test_separate_raster_and_occurrence_source_failures_produce_no_macro_evidence():
    pytest.importorskip('pyproj')
    config={**CFG,'windows':CFG['windows'][:1]}
    matcher=lambda name,**kw: SimpleNamespace(taxon_key='key',canonical_name=name,status='ACCEPTED',checklist_key=kw['checklist_key'])
    def fetcher(*args,**kw):
        return SimpleNamespace(total_count=0,query_sha256='empty')
    def extractor(*args,**kwargs):
        raise RuntimeError('raster not available')
    result,grid=m.assemble(config,matcher=matcher,fetcher=fetcher,raster_extractor=extractor)
    assert result['macro_inference_blocked'] is True
    assert result['positive_biological_evidence'] is False
    assert grid.empty
    assert result['n_climate_complete_windows'] == 0
    assert result['windows'][0]['focal_source']['status']=='no_search_records'


def test_climate_cells_are_archived_without_seeing_occurrence_response():
    pytest.importorskip('pyproj')
    config={**CFG,'windows':CFG['windows'][:1]}
    matcher=lambda name,**kw: SimpleNamespace(taxon_key='key',canonical_name=name,status='ACCEPTED',checklist_key=kw['checklist_key'])
    def fetcher(*args,**kw):
        return SimpleNamespace(total_count=0,query_sha256='empty')
    def extractor(grid,layers,**kwargs):
        out=grid.copy()
        out['temperature']=np.arange(len(grid),dtype=float)
        out['moisture']=2 + np.arange(len(grid),dtype=float)
        provenance=pd.DataFrame([{'predictor':'temperature','uri':'unit_fixture'},{'predictor':'moisture','uri':'unit_fixture'}])
        return out,provenance
    result,grid=m.assemble(config,matcher=matcher,fetcher=fetcher,raster_extractor=extractor)
    assert result['n_climate_complete_windows']==1
    assert len(grid)>0
    assert result['positive_biological_evidence'] is False
    assert 'n_occ' not in grid.columns
