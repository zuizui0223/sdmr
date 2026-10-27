"""Do not choose observed outcome by source success; no byte mismatch tolerated."""
from pathlib import Path
import importlib.util
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v4',ROOT/'experiments/fia_climate_density_one_snapshot_v4.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_source_stop_has_no_demographic_fit():
    old={'n_source_ready':0,'states':[{'state':s,'status':'source_stop'} for s in m.gate.STATES]}
    result=m.analyze_frozen_source(old,{}, {}, Path('/tmp'))
    assert result['status']=='source_stop_no_biological_outcome_opened'
    assert result['n_fitted_species']==0
    assert 'species' not in result


def test_fixed_source_and_model_endpoints_before_outcome():
    assert m.gate.STATES==('RI','VA','WI')
    assert len(m.gate.SPECIES)==13
    assert m.analysis.COUNTY_CV_FOLDS==5
    assert m.analysis.MIN_SPECIES_OBSERVATIONS==500
    assert m.analysis.PRIMARY_MODEL=='common_temperature_precipitation_x_basal_area'


def test_climate_state_source_only_after_noaa_receipt(tmp_path):
    bad=tmp_path/'rec.json';bad.write_text('{"study":"not_same_NOAA"}')
    data=tmp_path/'c.csv';data.write_text('')
    with pytest.raises(ValueError,match='NOAA climate source changed'):
        m.run(tmp_path/'out',data,bad)
