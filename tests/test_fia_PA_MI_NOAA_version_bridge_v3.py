"""NOAA 20261105 source-only bridge refuses historical climate revision."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_PA_MI_NOAA_version_bridge_v3 as m
import fia_noaa_county_climate_source_v1 as noaa


def cfg():
    return json.loads((ROOT/"configs/fia_PA_MI_NOAA_version_bridge_v3.json").read_text())


def old_panel():
    return {
      ("44001",2005,4):(11.0,45.0),
      ("51001",2005,4):(12.0,46.0),
      ("55001",2005,4):(13.0,47.0),
    }


def test_contract_cannot_change_unseen_states_or_climate_version():
    obj=cfg()
    m.verify_contract(obj)
    assert m.HOLDOUT_STATES==("PA","MI")
    assert m.NOAA_SOURCE_DATE=="20261105"
    assert m.ORIGINAL_TRAIN_CSV_SHA.startswith("44b328")
    assert m.NCEI_ORDINAL_TO_FIPS=={"37":"44","44":"51","47":"55","36":"42","20":"26"}
    for key,bad in (
       ("noaa_release","20261006"),
       ("previous_source_v2_CSV_sha256","0"*64),
       ("ordinal_to_FIPS",{"20":"42","36":"26"}),
       ("holdout_states",["VA","MI"]),
       ("refuse_mixed_NOAA_versions_if_historical_values_change",False),
       ("all_prior_FIA_growth_results_sealed",False)):
        x=copy.deepcopy(obj)
        x[key]=bad
        with pytest.raises(ValueError,match="contract not frozen"):
            m.verify_contract(x)


def test_noaa_historical_source_identical_authorizes_only_climate_comparison():
    original=old_panel()
    newly={**original,("26001",2005,4):(20.,120.),("42001",2005,4):(10.,60.)}
    result=m.compare_versions(original,newly)
    assert result["old_source_months_compared"]==3
    assert result["historical_1991_2025_original_3state_monthly_values_exactly_unchanged"]
    assert all(z["unchanged_at_six_decimal_normalization"] for z in result["states"].values())
    assert result["do_not_combine_mismatched_source_versions"]


def test_one_changed_historical_month_forbids_mixed_version_claim():
    original=old_panel()
    new=copy.deepcopy(original)
    new[("51001",2005,4)]=(12.000001,46.)
    diff=m.compare_versions(original,new)
    assert not diff["historical_1991_2025_original_3state_monthly_values_exactly_unchanged"]
    assert diff["states"]["VA"]["n_changed_temperature_months"]==1
    assert diff["states"]["VA"]["max_abs_temperature_revision_C"]>0
    assert diff["states"]["RI"]["unchanged_at_six_decimal_normalization"]
    # A missing month is not a zero anomaly, and also forbids promotion.
    del new[("44001",2005,4)]
    miss=m.compare_versions(original,new)
    assert miss["states"]["RI"]["n_missing_original_months_in_new_source"]==1
    assert not miss["historical_1991_2025_original_3state_monthly_values_exactly_unchanged"]


def test_holdout_exposure_uses_both_measurement_dates_and_baseline():
    climate={}
    for prefix in ("26","42"):
        fips=prefix+"001"
        for yr in range(1991,2026):
            for mo in range(4,10):
                climate[(fips,yr,mo)]=(15.,2.)
    src=[]
    for state,fips in (("PA","42001"),("MI","26001")):
        src.append({"species_code":"129","state":state,"county_fips":fips,
           "plot_chain_id":state+"-chain", "interval_id":state+"-current",
           "prior_visit_year":2002,"prior_visit_month":7,
           "current_visit_year":2010,"current_visit_month":7,
           "interval_end_year":2010,"remeasurement_months":96})
    out,qc=m.build_new_external_climate(src,climate)
    assert len(out)==2
    assert {z["state"] for z in out}=={"PA","MI"}
    assert all(z["temperature_anomaly_c"]==pytest.approx(0.) for z in out)
    assert all(z["precipitation_anomaly_mm"]==pytest.approx(0.) for z in out)
    assert qc["PA"]["climate_anomaly_eligible_source_taxon_plot_interval"]==1


def test_missing_intervening_climate_excludes_not_imputes():
    climate={}
    fips="42001"
    for yr in range(1991,2026):
        for mo in range(4,10):
            climate[(fips,yr,mo)]=(12.,3.)
    del climate[(fips,2021,8)]
    row={"species_code":"129","state":"PA","county_fips":fips,
         "plot_chain_id":"a","interval_id":"b",
         "prior_visit_year":2020,"prior_visit_month":7,
         "current_visit_year":2023,"current_visit_month":7,
         "interval_end_year":2023,"remeasurement_months":36}
    out,logs=m.build_new_external_climate([row],climate)
    assert not out
    assert logs["PA"]["incomplete_intervening_growing_months"]==1


def test_wrong_frozen_pa_mi_identity_source_bytes_are_not_accepted(tmp_path):
    for name in ("PA_MI_source_only_prior_species_plot_intervals_v2.csv",
                 "PA_MI_identity_source_receipt_v2.json",
                 "PA_MI_identity_only_cohort_preflight_v2.json"):
        (tmp_path/name).write_text("NOT THE FIRST-OPEN SOURCE")
    with pytest.raises(ValueError,match="v2 SHA mismatch"):
        m.source_v2_records(tmp_path)


def test_wrong_original_NOAA_cannot_initiate_network(tmp_path):
    a=tmp_path/"wrong.csv"
    a.write_text("bad,climate")
    with pytest.raises(ValueError,match="original 20261006"):
        m.load_original_climate(a)


def test_noaa_ordinal_state_codes_still_distinct_from_fips():
    conf={"source_variables":{"temperature":{"element":"02"}},
          "ncei_ordinal_state_to_fips_state":m.NCEI_ORDINAL_TO_FIPS,
          "growing_season_months":[4,5,6,7,8,9],
          "year_start":1991,"year_end":2025}
    text=(("20001022010 "+" ".join(["50.0"]*12)+"\n")
          +("36001022010 "+" ".join(["50.0"]*12)+"\n"))
    data,metadata=noaa.parse_climdiv_county(text.encode(),"temperature",conf)
    assert ("26001",2010,4) in data and ("42001",2010,4) in data
    assert len(data)==12
    assert metadata["n_distinct_counties"]==2


def test_frozen_outcome_boundary_and_known_source_versions():
    assert m.V2_SOURCE_SHA=="70cf6e8db95c864d80e684ed7292606d6a8df64d71e8bd952ae1a1a2adc4d1c2"
    assert m.V2_RECEIPT_SHA=="1392858a521f466e0b39892202883cec4a645f39dad6b5ab7e5d2afa534b5e3c"
    assert m.OLD_NOAA_SHA=="623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8"
    assert all(x not in m.SOURCE_FIELDS for x in ("DIA","STATUSCD","growth","mortality"))
