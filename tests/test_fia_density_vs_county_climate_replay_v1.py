"""Frozen-response replay contract and basal-area knockout controls."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"experiments"))
import fia_density_vs_county_climate_replay_v1 as m


def sample_data():
    rng=np.random.default_rng(271828)
    src=[]
    out=[]
    for state,prefix in (("VA","51"),("WI","55")):
        for county in range(1,61):
            fips=f"{prefix}{county:03d}"
            for plot in range(8):
                plot_id=f"{state}-{county}-{plot}"
                temp=0.3+1.1*(county%3)+rng.uniform(-.1,.1)
                prec=20+200*(county%2)+rng.uniform(-1,1)
                year=2010
                ba=rng.uniform(0.3,2.3)
                ycenter=rng.uniform(-.15,.5)
                age=rng.uniform(0.3,1.4)
                logdiam=rng.uniform(-.75,.4)
                interval=rng.uniform(4.2,7.4)
                value=(0.02+0.005*(state=="WI")-0.012*ba+
                       0.001*ycenter+0.001*age+0.001*logdiam+
                       0.0005*interval + rng.normal(0,.0015))
                src.append({"species_code":"129","state":state,"county_fips":fips,
                            "plot_chain_id":plot_id,"interval_id":plot_id,
                            "interval_end_year":year,"temperature_anomaly_c":temp,
                            "precipitation_anomaly_mm":prec})
                out.append({"sp":"129","state":state,"county":fips,"plot":plot_id,
                            "year_centered":ycenter,"interval":interval,
                            "ln_dia10":logdiam,"age60":age,"ba100":ba,
                            "tanom3":temp/3,"panom200":prec/200,"growth":value})
    return pd.DataFrame(out),pd.DataFrame(src)


def test_model_family_is_fixed_and_nested():
    df,src=sample_data()
    assert m.design(df,"without_density").shape==(len(df),6)
    assert m.design(df,"baseline").shape==(len(df),7)
    assert m.design(df,"stationary_climate").shape==(len(df),11)
    with pytest.raises(ValueError,match="unknown fixed"):
        m.design(df,"nonlinear_forest")


def test_synthetic_density_signal_recovered_not_given_climate_causal_label():
    df,src=sample_data()
    y,s=m.source_and_growth_cells(df,src)
    counties=m.one_county_ledger(y,s,("129",))
    assert len(counties)>=80
    assert set(x["species_code"] for x in counties)=={"129"}
    result=m.summarize("129",counties)
    assert result["basal_area_incremental_rmse_gain_percent"]>1
    assert result["county_bootstrap_postfit_95pct_interval_basal_gain"][0]>0
    assert result["posthoc_drop_basal_area_not_preregistered"] is True
    assert result["county_bootstrap_uses_no_model_refits"] is True


def test_source_to_growth_join_refuses_unknown_prior_species():
    df,src=sample_data()
    df=df.head(3).copy()
    with pytest.raises(ValueError,match="missing prior-source"):
        m.source_and_growth_cells(df,src.iloc[3:].copy())


def test_county_score_equal_region_and_county():
    counties=[
       {"state":"VA","county_fips":"51001","without_density_mse":9.0,
        "baseline_mse":4.0,"stationary_climate_mse":5.0},
       {"state":"VA","county_fips":"51003","without_density_mse":1.0,
        "baseline_mse":1.0,"stationary_climate_mse":1.0},
       {"state":"WI","county_fips":"55001","without_density_mse":16.0,
        "baseline_mse":9.0,"stationary_climate_mse":9.0}]
    assert m.rmse(counties,"without_density")==pytest.approx(np.sqrt((5+16)/2))
    assert m.rmse(counties,"baseline")==pytest.approx(np.sqrt((2.5+9)/2))
    with pytest.raises(ValueError,match="missing state"):
        m.rmse(counties[:2],"baseline")


def test_bootstrap_reports_interval_and_single_county_sensitivity():
    counties=[]
    for state, p in (("VA","51"),("WI","55")):
        for i in range(6):
            counties.append({"state":state,"county_fips":f"{p}{i+1:03d}",
                 "without_density_mse":float(10+i),
                 "baseline_mse":float(7+i),
                 "stationary_climate_mse":float(7.5+i)})
    result=m.summarize("129",counties)
    assert result["n_distinct_counties"]==12
    assert result["basal_area_incremental_rmse_gain_percent"]>0
    assert result["county_bootstrap_postfit_95pct_interval_basal_gain"][0]>0
    assert result["leave_one_evaluation_county_out_basal_gain_min_max"][0]>0


def test_full_hash_closed_gate_even_for_syntactically_valid_but_wrong_files(tmp_path):
    for name in ("primary_five_conditional_growth_inputs_v1.csv",
                 "new_source_only_taxon_plot_intervals.csv",
                 "VA_WI_growth_result_v1.json"):
        (tmp_path/name).write_text("{}")
    with pytest.raises(ValueError,match="identity mismatch"):
        m.prepare_inputs(tmp_path)


def test_frozen_history_and_not_independent_confirmatory():
    assert m.SOURCE_RUN==43886130089
    assert m.SOURCE_ARTIFACT==14234926861
    assert m.PRIMARY==("129","316","802","833","837")
    assert m.BOOTSTRAP_DRAWS==1999
    assert m.MODELS==("without_density","baseline","stationary_climate")
    assert all(len(x)==64 for x in (m.ZIP_SHA256,m.INPUT_SHA256,m.SOURCE_SHA256,m.RESULT_SHA256))
