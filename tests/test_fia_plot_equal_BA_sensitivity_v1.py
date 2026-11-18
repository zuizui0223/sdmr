"""Synthetic plot-chain weighting and postoutcome no-promotion controls."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
sys.path.insert(0,str(ROOT/"tests"))
import fia_plot_equal_BA_sensitivity_v1 as m
import fia_density_vs_county_climate_replay_v1 as prior
import fia_county_within_basal_area_audit_v1 as original
from test_fia_county_within_basal_area_audit_v1 import make_synthetic


def test_tree_rich_plot_not_overweighted():
    records=[]
    for state,prefix in (("VA","51"),("WI","55")):
        for county in range(1,3):
            for plot,n in (("large",10),("small",1)):
                for i in range(n):
                    records.append({"state":state,"county":f"{prefix}{county:03d}",
                                    "plot_chain_sha256":f"{state}{county}{plot}","growth":float(i)})
    x=pd.DataFrame(records)
    w=m.sqrt_plot_weights(x)**2
    x["weight"]=w
    assert x.groupby("state")["weight"].sum().to_dict()==pytest.approx({"VA":.5,"WI":.5})
    assert all(v==pytest.approx(.125)
               for v in x.groupby(["state","county","plot_chain_sha256"]).weight.sum())
    assert x.groupby(["state","county"]).weight.sum().tolist()==pytest.approx([.25]*4)


def test_plot_equal_county_scoring_averages_plots_before_counties():
    x=pd.DataFrame({"state":["VA","VA","VA"],
       "county":["51001"]*3,
       "plot_chain_sha256":["p1","p1","p2"],
       "growth":[1.,3.,2.]})
    result=m.heldout_plot_equal_county_mse(x,np.zeros(3))
    assert len(result)==1
    assert float(result.iloc[0])==pytest.approx((5.+4.)/2)
    assert float(result.iloc[0])!=pytest.approx((1.+9.+4.)/3)
    with pytest.raises(ValueError,match="grain"):
        m.heldout_plot_equal_county_mse(x,np.zeros(2))


def test_known_within_county_synthetic_growth_signal(monkeypatch):
    growth,source=make_synthetic()
    observed,src=prior.source_and_growth_cells(growth,source)
    df=original.add_predictors(observed)
    monkeypatch.setattr(m,"SPECIES",("129",))
    ledger=m.county_ledger(df,src)
    assert len(ledger)>=60
    assert len({x["county_fips"] for x in ledger})==len(ledger)
    result=m.species_summary(ledger,"129")
    assert result["relative_gain_percent"]["within_increment_conditional_on_county_mean"]>1.0
    assert result["within_gain_postfit_county_bootstrap95"][0]>0
    assert result["postfit_resampling_retrains_models"] is False


def test_plot_equal_comparison_rejects_nonfrozen_family_or_missing_state():
    growth,_=make_synthetic(6)
    df=original.add_predictors(growth)
    assert m.fit(df,"original_basal_area").shape[0]==7
    assert m.fit(df,"between_and_within").shape[0]==8
    with pytest.raises(ValueError,match="unknown fixed"):
        m.fit(df,"unregistered_climate_mechanism")
    with pytest.raises(ValueError,match="missing state"):
        m.score([{"state":"VA","county_fips":"51001","within_county_basal_area_mse":.001}],
                "within_county_basal_area")


def test_tampered_original_frozen_source_fails(tmp_path):
    for name in ("primary_five_conditional_growth_inputs_v1.csv",
                 "new_source_only_taxon_plot_intervals.csv",
                 "VA_WI_growth_result_v1.json"):
        (tmp_path/name).write_text("not original data")
    with pytest.raises(ValueError,match="identity mismatch"):
        prior.prepare_inputs(tmp_path)


def test_only_previously_selected_taxa_and_source_identity():
    assert m.PROGRAM=="fia_BA_within_county_equal_plot_sensitivity_v1"
    assert m.SPECIES==("129","316","802","833","837")
    assert m.BOOTSTRAP==999
    assert m.STATES==("VA","WI")
    assert prior.SOURCE_RUN==43886130089
    assert len(prior.INPUT_SHA256)==64
