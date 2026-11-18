"""No PA/MI outcomes opened: pre-holdout VA/WI frozen predictor controls."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_PA_MI_transfer_model_freeze_v1 as m
import fia_shared_vs_regional_growth_core_v1 as core


def mock_source_growth():
    rng=np.random.default_rng(20261118)
    old=[];new=[];out=[]
    for sp in m.PRIMARY:
      for state,prefix in (("VA","51"),("WI","55")):
        for county in range(1,7):
          fips=f"{prefix}{county:03d}"
          band=county%2
          for j in range(12):
            event=f"{sp}-{state}-{county}-{j}"
            chain=f"{state}-{county}-{j}"
            original={"species_code":sp,"state":state,"county_fips":fips,
              "plot_chain_id":chain,"interval_id":event,"interval_end_year":2010,
              "temperature_anomaly_c":float(.2+2*band),
              "precipitation_anomaly_mm":float(20+200*band)}
            rec=dict(original)
            rec["temperature_anomaly_c"]+=float(.1+rng.uniform(-.04,.04))
            rec["precipitation_anomaly_mm"]+=float(rng.uniform(-12,12))
            old.append(original);new.append(rec)
            sample={
              "sp":sp,"state":state,"plot":event,"county":fips,
              "plot_chain_sha256":hashlib.sha256(chain.encode()).hexdigest(),
              "year_centered":float(rng.normal(.1,.25)),
              "interval":float(rng.uniform(4,9)),
              "ln_dia10":float(rng.normal(.2,.7)),
              "age60":float(rng.uniform(.3,2)),
              "ba100":float(rng.uniform(.3,2.5)),
              "tanom3":original["temperature_anomaly_c"]/3,
              "panom200":original["precipitation_anomaly_mm"]/200,
            }
            sample["growth"]=float(.02+.006*sample["ba100"]+
                .004*sample["tanom3"]+.003*(state=="WI")+
                rng.normal(0,.005))
            out.append(sample)
    return pd.DataFrame(out),pd.DataFrame(old),pd.DataFrame(new)


def v5_report():
    return {"source_species":[{"species_code":sp,"both_holdout_states_source_eligible":True}
                              for sp in m.PRIMARY]}


def test_exact_model_and_hypothesis_freeze():
    assert m.PROGRAM=="fia_PA_MI_external_transfer_training_parameters_frozen_v1"
    assert m.TRANSFER_BRANCH=={"PA":"VA","MI":"WI"}
    assert m.PRIMARY==("129","316","802","833","837")
    assert len(m.FEATURES["baseline"])==7
    assert len(m.FEATURES["stationary_climate"])==11
    assert len(m.FEATURES["state_varying_climate"])==15
    assert m.V5_RUN==44296141877
    assert m.V5_SOURCE_ARTIFACT==14423482128


def test_old_source_to_same_event_new_noaa_join_no_growth_response_leak(monkeypatch):
    grow,old,new=mock_source_growth()
    monkeypatch.setattr(m,"EXPECTED_OLD_SOURCE_ROWS",len(old))
    q=m.join_development_growth(grow,old,new)
    assert len(q)==len(grow)
    assert np.allclose(q.tanom3*3,q.T_new)
    assert np.allclose(q.panom200*200,q.P_new)
    assert not np.allclose(q.tanom3*3,grow.tanom3*3)
    assert all(isinstance(z,tuple) and len(z)==3 for z in q.cell)
    assert set(q.state)=={"VA","WI"}


def test_growing_outcome_from_PA_MI_or_inconsistent_existing_county_refused(monkeypatch):
    grow,old,new=mock_source_growth()
    monkeypatch.setattr(m,"EXPECTED_OLD_SOURCE_ROWS",len(old))
    corrupt=grow.copy()
    corrupt.loc[corrupt.index[0],"county"]="51099"
    with pytest.raises(ValueError,match="growth county"):
        m.join_development_growth(corrupt,old,new)
    invalid=grow.copy()
    invalid.loc[invalid.index[0],"panom200"]+=1
    with pytest.raises(ValueError,match="historic outcome predictor"):
        m.join_development_growth(invalid,old,new)


def test_unique_taxon_interval_and_plot_root_are_required(monkeypatch):
    grow,old,new=mock_source_growth()
    monkeypatch.setattr(m,"EXPECTED_OLD_SOURCE_ROWS",len(old))
    v=new.copy();v.loc[v.index[0],"plot_chain_id"]="IMPOSTOR"
    with pytest.raises(ValueError,match="original past-to-new sampled"):
        m.join_development_growth(grow,old,v)
    duplicate=pd.concat([new,new.head(1)],ignore_index=True)
    with pytest.raises(ValueError,match="duplicate old/new"):
        m.join_development_growth(grow,old,duplicate)


def test_train_source_cells_ignore_external_and_preserve_grid():
    _,old,new=mock_source_growth()
    cells=m.qualified_train_cells(new,"129")
    assert len(cells)==2
    assert cells=={(0,0,4),(2,2,4)}
    with_PA=pd.concat([new,pd.DataFrame([{
        "species_code":"129","state":"PA","county_fips":"42001",
        "plot_chain_id":"NEW","interval_id":"HOLDOUT",
        "interval_end_year":2010,"temperature_anomaly_c":50.,
        "precipitation_anomaly_mm":5000.}])],ignore_index=True)
    assert m.qualified_train_cells(with_PA,"129")==cells


def test_external_surrogate_branch_mapping_matches_existing_design():
    df=pd.DataFrame({
       "state":["PA","MI"],
       "year_centered":[0.,.1],"interval":[5.,6.],
       "ln_dia10":[.5,.4],"age60":[.4,.6],
       "ba100":[.5,.7],"tanom3":[.1,.2],"panom200":[.2,-.3]})
    expected=df.copy();expected["state"]=["VA","WI"]
    for model in core.MODELS:
        assert np.allclose(m.surrogate_design(df,model),core.design(expected,model))
    invalid=df.copy();invalid.loc[0,"state"]="RI"
    with pytest.raises(ValueError,match="PA/MI"):
        m.surrogate_design(invalid,"baseline")


def test_fit_five_original_dev_taxa_before_any_holdout_response(monkeypatch):
    g,old,new=mock_source_growth()
    monkeypatch.setattr(m,"EXPECTED_OLD_SOURCE_ROWS",len(old))
    monkeypatch.setattr(m,"EXPECTED_GROWTH_ROWS",len(g))
    monkeypatch.setattr(m,"MIN_TRAIN_COUNTIES",3)
    monkeypatch.setattr(m,"MIN_TRAIN_GROWTH_PAIRS",30)
    result=m.freeze(g,old,new,v5_report())
    assert result["n_primary_models_frozen"]==5
    assert len(result["species"])==5
    assert result["new_external_growth_or_survival_outcome_opened"] is False
    assert result["external_RMSE_or_ecological_effect_estimated"] is False
    assert result["PA_MI_counties_and_responses_not_used_to_fit_any_coefficients"]
    assert all(set(s["fixed_model_coefficients"])==set(core.MODELS) for s in result["species"])
    assert all(len(s["fixed_model_coefficients"]["state_varying_climate"])==15 for s in result["species"])


def test_source_not_eligible_never_marked_frozen_model(monkeypatch):
    g,old,new=mock_source_growth()
    monkeypatch.setattr(m,"EXPECTED_OLD_SOURCE_ROWS",len(old))
    monkeypatch.setattr(m,"EXPECTED_GROWTH_ROWS",len(g))
    monkeypatch.setattr(m,"MIN_TRAIN_COUNTIES",3)
    monkeypatch.setattr(m,"MIN_TRAIN_GROWTH_PAIRS",30)
    panel=v5_report()
    panel["source_species"][0]["both_holdout_states_source_eligible"]=False
    report=m.freeze(g,old,new,panel)
    assert report["n_primary_models_frozen"]==4
    assert report["species"][0]["status"]=="cannot_freeze_unqualified_external_transfer"


def test_tampered_first_open_source_is_rejected(tmp_path):
    for name in ("RI_VA_WI_original_IDs_rebased_NOAA_20261105_v5.csv",
                 "PA_MI_source_receipt_v5.json","PA_MI_same_NOAA_source_support_v5.json"):
        (tmp_path/name).write_text("tampered")
    with pytest.raises(ValueError,match="SHA mismatch"):
        m.validate_v5(tmp_path)
