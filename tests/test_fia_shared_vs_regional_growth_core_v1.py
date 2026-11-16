"""Synthetic-only validation for VA/WI shared vs state-varying growth models."""
import sys
import math
import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_shared_vs_regional_growth_core_v1 as mod


def config():
    return json.loads((ROOT/"configs/fia_joint_climate_support_gate_v1.json").read_text())


def source_and_growth(with_regional=False):
    rng=np.random.default_rng(8453)
    source=[]
    outcomes=[]
    for state,prefix in (("VA","51"),("WI","55")):
        for county in range(1,61):
            fips=f"{prefix}{county:03d}"
            for j in range(20):
                plot=f"{state}_{county}_{j}"
                year=2012 if j%2==0 else 2017
                t=0.4+(county%3)*1.0+0.005*j
                p=30+(county%4)*100+0.03*j
                ba=0.3+0.11*(county%5)+0.02*(j%3)
                source.append({"species_code":"129","state":state,
                   "county_fips":fips,"plot_chain_id":plot,"interval_id":plot,
                   "interval_end_year":year,"temperature_anomaly_c":t,
                   "precipitation_anomaly_mm":p})
                scaled_t=t/3
                scaled_p=p/200
                logdia=math.log((5.5 + j*0.7)/10)
                age=0.4+j*0.025
                duration=4.2+0.3*(j%3)
                yr=(year-2005)/20
                w=1 if state=="WI" else 0
                growth=(0.02+0.005*w+0.003*age+0.01*logdia+0.004*ba+
                    0.018*scaled_t-0.007*scaled_p+0.002*ba*scaled_t-
                    0.003*ba*scaled_p+0.001*yr+0.0005*duration)
                if with_regional:
                    growth+=w*0.04*scaled_t
                growth+=rng.normal(0,0.003)
                outcomes.append({"sp":"129","state":state,"plot":plot,
                    "county":fips,"year_centered":yr,"interval":duration,
                    "ln_dia10":logdia,"age60":age,"ba100":ba,
                    "tanom3":scaled_t,"panom200":scaled_p,"growth":growth})
    return source,pd.DataFrame(outcomes)


def test_design_models_are_frozen_and_nested():
    source,growth=source_and_growth()
    assert mod.design(growth,"baseline").shape==(len(growth),7)
    assert mod.design(growth,"stationary_climate").shape==(len(growth),11)
    assert mod.design(growth,"state_varying_climate").shape==(len(growth),15)
    with pytest.raises(ValueError,match="unknown frozen"):
        mod.design(growth,"regional_nonlinear")


def test_source_join_rejects_missing_prior_visit_or_climate_mismatch():
    source,df=source_and_growth()
    verified=mod.attach_source_to_growth(df.head(3),source)
    assert len(verified)==3
    assert (verified.county_fold>=0).all()
    wrong=df.head(3).copy()
    wrong.loc[wrong.index[0],"tanom3"]+=1
    with pytest.raises(ValueError,match="NOAA source"):
        mod.attach_source_to_growth(wrong,source)
    with pytest.raises(ValueError,match="no prior-visit"):
        mod.attach_source_to_growth(df.head(3),source[3:])


def test_source_only_screen_preserves_full_species_denominator():
    source,growth=source_and_growth()
    out=mod.evaluate(growth,source,config())
    assert out["n_declared_species"]==13
    sp=next(x for x in out["species"] if x["species_code"]=="129")
    assert sp["n_available_folds"]==5,sp
    assert sp["status"]=="exploratory_five_fold_county_holdout_completed"
    assert out["n_primary_complete"]==1
    assert out["does_not_test_survival_or_population_mortality"] is True
    assert not out["biological_promotion_authorized"]
    rest=[x for x in out["species"] if x["species_code"]!="129"]
    assert len(rest)==12
    assert all(x["status"] in ("secondary_not_modelled_primary_five_fixed",
                                "full_denominator_not_evaluable_no_success_claim") for x in rest)


def test_known_regional_response_produces_holdout_region_model_gain():
    source,growth=source_and_growth(with_regional=True)
    x=mod.evaluate(growth,source,config())
    sp=next(x for x in x["species"] if x["species_code"]=="129")
    assert sp["n_available_folds"]==5
    assert sp["state_varying_vs_shared_rmse_gain_percent"]>1.0
    assert sp["state_varying_gain_county_bootstrap_95pct_interval"][0]>0


def test_stationary_world_does_not_need_large_regional_gain():
    source,growth=source_and_growth(with_regional=False)
    sp=next(x for x in mod.evaluate(growth,source,config())["species"] if x["species_code"]=="129")
    assert sp["n_available_folds"]==5
    assert sp["state_varying_vs_shared_rmse_gain_percent"]<1.0


def test_source_only_county_holdout_selection_ignores_responses():
    source,growth=source_and_growth()
    cells=mod.split_source_cells(source,config(),"129",0)
    changed=growth.copy();changed["growth"]+=1000
    assert cells==mod.split_source_cells(source,config(),"129",0)
    assert len(cells)>=2


def test_RI_growth_does_not_enter_VA_WI_comparison():
    source,growth=source_and_growth()
    extra=growth.head(1).copy();extra.loc[extra.index[0],"state"]="RI"
    with pytest.raises(ValueError,match="RI growth"):
        mod.evaluate(pd.concat([growth,extra],ignore_index=True),source,config())


def test_county_equal_state_equal_score_not_individual_weighted():
    rows=[
       {"state":"VA","county_fips":"51001","baseline_mse":10., "stationary_climate_mse":1., "state_varying_climate_mse":4.},
       {"state":"VA","county_fips":"51003","baseline_mse":10., "stationary_climate_mse":9., "state_varying_climate_mse":4.},
       {"state":"WI","county_fips":"55001","baseline_mse":10., "stationary_climate_mse":4., "state_varying_climate_mse":1.},
       {"state":"WI","county_fips":"55003","baseline_mse":10., "stationary_climate_mse":4., "state_varying_climate_mse":1.},
    ]
    assert mod.rmse_county_equal_state_equal(rows,"stationary_climate")==pytest.approx(math.sqrt(4.5))
    assert mod.rmse_county_equal_state_equal(rows,"state_varying_climate")==pytest.approx(math.sqrt(2.5))
    a=mod.summarize_county_risk(rows,"129")
    assert a["state_varying_vs_shared_rmse_gain_percent"]>0
    assert len(a["state_varying_gain_county_bootstrap_95pct_interval"])==2
