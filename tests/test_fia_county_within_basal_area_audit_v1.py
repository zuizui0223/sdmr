"""Synthetic-only guardrails for frozen county within-vs-between basal-area audit."""
from __future__ import annotations
import hashlib
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"experiments"))
import fia_county_within_basal_area_audit_v1 as m
import fia_density_vs_county_climate_replay_v1 as prior


def make_synthetic(n_counties=40,n_plots=12):
    rng=np.random.default_rng(20261117)
    source=[];outcome=[]
    for state,prefix in (("VA","51"),("WI","55")):
        for county in range(1,n_counties+1):
            fips=f"{prefix}{county:03d}"
            for plot in range(n_plots):
                pid=f"{state}-{county}-{plot}"
                year=2010 if plot%2 else 2015
                t=0.2+2*(county%2)+0.003*plot
                p=50+200*(county%2)+0.02*plot
                stand=0.4+(county%7)*0.13+0.06*plot+rng.normal(0,.13)
                age=.4+.05*(plot%7)+rng.normal(0,.005)
                logdiam=math.log((5+plot*.4)/10)
                duration=4.1+0.1*(plot%5)
                yr=(year-2005)/20
                response=(.025 + .005*(state=="WI") -
                    .015*stand + .0012*age + .003*logdiam +
                    .0004*yr + .0002*duration + rng.normal(0,.002))
                source.append({"species_code":"129","state":state,"county_fips":fips,
                               "plot_chain_id":pid,"interval_id":pid,
                               "interval_end_year":year,"temperature_anomaly_c":t,
                               "precipitation_anomaly_mm":p})
                outcome.append({"sp":"129","state":state,"county":fips,"plot":pid,
                                "plot_chain_sha256":hashlib.sha256(pid.encode()).hexdigest(),
                                "year_centered":yr,"interval":duration,
                                "ln_dia10":logdiam,"age60":age,"ba100":stand,
                                "tanom3":t/3,"panom200":p/200,"growth":response})
    return pd.DataFrame(outcome),pd.DataFrame(source)


def test_county_mean_is_unique_plot_weighted_not_tree_weighted():
    df=pd.DataFrame([
        {"sp":"129","state":"VA","county":"51001","plot_chain_sha256":"p1","ba100":2.},
        {"sp":"129","state":"VA","county":"51001","plot_chain_sha256":"p1","ba100":2.},
        {"sp":"129","state":"VA","county":"51001","plot_chain_sha256":"p2","ba100":10.}])
    x=m.add_predictors(df)
    assert len(x)==len(df)
    assert x.county_mean_BA.tolist()==pytest.approx([6,6,6])
    assert x.within_county_BA.tolist()==pytest.approx([-4,-4,4])
    assert np.allclose(x.ba100,x.county_mean_BA+x.within_county_BA)


def test_fixed_nested_design_width_and_invalid_family():
    growth, source=make_synthetic(6)
    a=m.add_predictors(growth)
    assert m.design(a,"without_density").shape[1]==6
    assert m.design(a,"original_basal_area").shape[1]==7
    assert m.design(a,"county_mean_basal_area").shape[1]==7
    assert m.design(a,"within_county_basal_area").shape[1]==7
    assert m.design(a,"between_and_within").shape[1]==8
    with pytest.raises(ValueError,match="unknown fixed"):m.design(a,"nonlinear_niche_model")


def test_within_county_known_predictive_signal(monkeypatch):
    df,src=make_synthetic()
    monkeypatch.setattr(m,"SPECIES",("129",))
    decorated,source=prior.source_and_growth_cells(df,src)
    x=m.add_predictors(decorated)
    ledger=m.county_heldout_ledger(x,source)
    assert len({z["county_fips"] for z in ledger})==len(ledger)
    assert len(ledger)>=60
    values={name:m.score(ledger,name) for name in m.MODES}
    assert m.gain(values["county_mean_basal_area"],values["between_and_within"])>1.0
    assert m.gain(values["without_density"],values["original_basal_area"])>1.0
    assert m.gain(values["county_mean_basal_area"],values["between_and_within"])>m.gain(values["without_density"],values["county_mean_basal_area"])


def test_plot_level_between_within_variance_identity():
    df,_=make_synthetic(10)
    result=m.plot_level_BA_partition(df)
    assert result["between_and_within_variance_sum_verified"]
    assert 0<result["within_county_variance_fraction"]<1
    assert result["between_county_variance_fraction"]+result["within_county_variance_fraction"]==pytest.approx(1)


def test_country_equal_state_equal_mse_scoring():
    rows=[
       {"state":"VA","county_fips":"51001","original_basal_area_mse":4.},
       {"state":"VA","county_fips":"51003","original_basal_area_mse":1.},
       {"state":"WI","county_fips":"55001","original_basal_area_mse":9.}
    ]
    assert m.score(rows,"original_basal_area")==pytest.approx(math.sqrt((2.5+9)/2))
    with pytest.raises(ValueError,match="missing state"):
        m.score(rows[:2],"original_basal_area")


def test_original_growth_source_refusal_on_tampered_input(tmp_path):
    for name in ("primary_five_conditional_growth_inputs_v1.csv",
                 "new_source_only_taxon_plot_intervals.csv",
                 "VA_WI_growth_result_v1.json"):
        (tmp_path/name).write_text("tampered")
    with pytest.raises(ValueError,match="identity mismatch"):
        prior.prepare_inputs(tmp_path)


def test_posthoc_claim_ceiling_and_source_identity():
    assert m.PROGRAM=="fia_archived_within_county_basal_area_information_v1"
    assert m.BOOTSTRAP==999
    assert m.SPECIES==("129","316","802","833","837")
    assert prior.SOURCE_RUN==43886130089
    assert len(prior.INPUT_SHA256)==64
