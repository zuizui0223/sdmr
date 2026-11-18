"""Freeze VA/WI trained predictors for PA/MI before opening external response.

Reads only previously consumed 170994 VA/WI selected survivor-growth rows
and the VERIFIED same-NOAA-edition v5 source records. Reproduce original
old-growth to old-source lookup, then replace ONLY county climate exposure
with 20261105 event-verified source values; never use PA/MI growth or status.

Models: baseline, shared climate slopes, WI-specific climate slopes. For
out-of-region prediction, PA<-VA and MI<-WI *surrogate branches*, not fitted
PA/MI parameters. Freeze full coefficients, source cells and role mapping
without scoring any external outcome. Not causal niche or physiology.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import fia_density_vs_county_climate_replay_v1 as previous
import fia_shared_vs_regional_growth_core_v1 as models
import fia_joint_support_gate_v1 as support
import fia_PA_MI_NOAA_event_identity_v5 as source

PROGRAM="fia_PA_MI_external_transfer_training_parameters_frozen_v1"
V5_RUN=44296141877
V5_SOURCE_ARTIFACT=14423482128
V5_TRAIN_SHA="e3c872f5b0f4fce7e97bef5f172a631d0f09f28ced663d8bb6580a5ab894c11c"
V5_RECEIPT_SHA="7802b1ed30486b23c13cee27c3141d99539d1ff4237cf1e4435661711c4eae67"
V5_SUPPORT_SHA="c9c485be4a11e2c04ac12c58738feac02ba3cb4e33b9339a82a31dff5a8d6626"
PRIMARY=("129","316","802","833","837")
TRAIN=("VA","WI")
HOLDOUT=("PA","MI")
TRANSFER_BRANCH={"PA":"VA","MI":"WI"}
FEATURES={
 "baseline":["intercept","branch_WI","year_centered","interval","ln_dia10","age60","ba100"],
 "stationary_climate":["intercept","branch_WI","year_centered","interval","ln_dia10","age60","ba100",
                       "tanom3","panom200","ba_x_tanom3","ba_x_panom200"],
 "state_varying_climate":["intercept","branch_WI","year_centered","interval","ln_dia10","age60","ba100",
                         "tanom3","panom200","ba_x_tanom3","ba_x_panom200",
                         "branch_WI_x_tanom3","branch_WI_x_panom200",
                         "branch_WI_x_ba_x_tanom3","branch_WI_x_ba_x_panom200"]
}
EXPECTED_OLD_SOURCE_ROWS=88145
EXPECTED_GROWTH_ROWS=170994
MIN_TRAIN_COUNTIES=20
MIN_TRAIN_GROWTH_PAIRS=500
MIN_QUALIFIED_SHARED_CELLS=2
MIN_HOLDOUT_SOURCE_COUNTIES=5
MIN_HOLDOUT_SOURCE_PLOTS=25
MIN_HOLDOUT_SOURCE_COVERAGE=.20


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_v5(v5_dir:Path)->tuple[pd.DataFrame,dict]:
    files={
      "RI_VA_WI_original_IDs_rebased_NOAA_20261105_v5.csv":V5_TRAIN_SHA,
      "PA_MI_source_receipt_v5.json":V5_RECEIPT_SHA,
      "PA_MI_same_NOAA_source_support_v5.json":V5_SUPPORT_SHA
    }
    for name,digest in files.items():
        if sha(v5_dir/name)!=digest:
            raise ValueError("first source-only v5 result SHA mismatch: "+name)
    proof=json.loads((v5_dir/"PA_MI_same_NOAA_source_support_v5.json").read_text())
    receipt=json.loads((v5_dir/"PA_MI_source_receipt_v5.json").read_text())
    if (proof["status"]!="same_20261105_NOAA_v5_all_old_sampled_intervals_verified" or
        not proof["all_original_89616_source_rows_preserved"] or
        proof["source_species_denominator"]!=13 or
        proof["n_original_training_source_rebased_rows"]!=89616 or
        proof["n_PA_MI_source_only_holdout_rows"]!=83046 or
        receipt["status"]!="all_original_event_and_old_NOAA_source_verified_new_editions"):
        raise ValueError("not first-open validated complete five-state source frame")
    typed={k:str for k in ("species_code","state","county_fips","plot_chain_id","interval_id")}
    rebased=pd.read_csv(v5_dir/"RI_VA_WI_original_IDs_rebased_NOAA_20261105_v5.csv",
                         dtype=typed,low_memory=False)
    if len(rebased)!=89616 or set(rebased.state)!={"RI","VA","WI"}:
        raise ValueError("rebased original source denominator changed")
    return rebased,proof


def join_development_growth(growth:pd.DataFrame,old_src:pd.DataFrame,
                            rebased:pd.DataFrame)->pd.DataFrame:
    """No new response readings: old and new EXACT original site rows."""
    keys=["species_code","state","interval_id"]
    sub=rebased[rebased.state.isin(TRAIN)].copy()
    if len(sub)!=EXPECTED_OLD_SOURCE_ROWS or set(sub.state)!=set(TRAIN):
        raise ValueError("v5 VA/WI original source frame changed")
    if old_src.duplicated(keys).any() or sub.duplicated(keys).any():
        raise ValueError("duplicate old/new original taxon-state-plot-interval keys")
    old_check=old_src.merge(sub,on=keys,how="outer",suffixes=("_old","_new"),
                            indicator=True,validate="one_to_one")
    if len(old_check)!=EXPECTED_OLD_SOURCE_ROWS or not (old_check["_merge"]=="both").all():
        raise ValueError("previously opened VA/WI source not conserved in NOAA v5")
    for name in ("county_fips","plot_chain_id","interval_end_year"):
        if not (old_check[name+"_old"].to_numpy()==old_check[name+"_new"].to_numpy()).all():
            raise ValueError("original past-to-new sampled PLOT identity mismatch: "+name)
    # Compare all ORIGINAL old climate source observations BEFORE replacing
    # numerical predictor columns; no outcome-dependent sample trimming.
    for name in ("temperature_anomaly_c","precipitation_anomaly_mm"):
        if not (np.isfinite(old_check[name+"_old"].to_numpy(float)).all() and
                np.isfinite(old_check[name+"_new"].to_numpy(float)).all()):
            raise ValueError("nonfinite old/new source climate values")
    train_new=sub.rename(columns={
        "species_code":"sp","interval_id":"plot",
        "temperature_anomaly_c":"T_new","precipitation_anomaly_mm":"P_new",
        "county_fips":"county_new","plot_chain_id":"chain_new"})
    if train_new.duplicated(["sp","state","plot"]).any():
        raise ValueError("duplicate new training event ID")
    x=growth.merge(train_new[["sp","state","plot","county_new","chain_new",
                              "T_new","P_new","interval_end_year"]],
                   on=["sp","state","plot"],how="left",validate="many_to_one",
                   indicator=True)
    if len(x)!=len(growth) or not (x["_merge"]=="both").all():
        raise ValueError("growth joined to neither/multiple rebased source events")
    if not (x.county==x.county_new).all():
        raise ValueError("growth county does not match new verified source")
    hashed=x.chain_new.map(lambda s:hashlib.sha256(s.encode()).hexdigest())
    if not (hashed==x.plot_chain_sha256).all():
        raise ValueError("original selected plot-chain identity drift")
    # Old response row climate anomaly must match the FIRST-OPEN original
    # source, independent of any re-estimated/new region climate.
    old_by_event=old_src.rename(columns={
        "species_code":"sp","interval_id":"plot",
        "temperature_anomaly_c":"T_old","precipitation_anomaly_mm":"P_old"})
    chk=x.merge(old_by_event[["sp","state","plot","T_old","P_old"]],
                on=["sp","state","plot"],validate="many_to_one",how="left")
    if (chk["T_old"].isna().any() or
        not np.allclose(chk.tanom3.to_numpy(float)*3,chk.T_old.to_numpy(float),atol=1e-5,rtol=0) or
        not np.allclose(chk.panom200.to_numpy(float)*200,chk.P_old.to_numpy(float),atol=1e-4,rtol=0)):
        raise ValueError("historic outcome predictor climate/source identity mismatch")
    if chk.growth.isna().any() or not np.isfinite(chk.growth.to_numpy(float)).all():
        raise ValueError("invalid development-only survivor growth")
    chk["tanom3"]=chk.T_new.to_numpy(float)/3
    chk["panom200"]=chk.P_new.to_numpy(float)/200
    chk["cell"]=list(zip(np.floor(chk.T_new.to_numpy(float)).astype(int),
                         np.floor(chk.P_new.to_numpy(float)/100).astype(int),
                         np.floor((chk.interval_end_year.to_numpy(float)-1990)/5).astype(int)))
    return chk


def qualified_train_cells(sub:pd.DataFrame, sp:str)->set[tuple[int,int,int]]:
    qualified={}
    for state in TRAIN:
        b=sub[(sub.species_code==sp)&(sub.state==state)]
        counter=defaultdict(lambda:{"county":set(),"plot":set()})
        for q in b.itertuples(index=False):
            cell=(math.floor(q.temperature_anomaly_c),
                  math.floor(q.precipitation_anomaly_mm/100),
                  (int(q.interval_end_year)-1990)//5)
            a=counter[cell]
            a["county"].add(q.county_fips)
            a["plot"].add((q.county_fips,q.plot_chain_id))
        qualified[state]={cell for cell,seen in counter.items() if
                           len(seen["county"])>=2 and len(seen["plot"])>=5}
    return qualified["VA"] & qualified["WI"]


def surrogate_design(holdout_covariates:pd.DataFrame,kind:str)->np.ndarray:
    """This will be used only AFTER a later separately frozen outcome opening."""
    if set(holdout_covariates.state)-set(HOLDOUT) or holdout_covariates.empty:
        raise ValueError("external surrogate design requires only PA/MI rows")
    copied=holdout_covariates.copy()
    copied["state"]=copied.state.map(TRANSFER_BRANCH)
    return models.design(copied,kind)


def freeze(growth:pd.DataFrame,old_src:pd.DataFrame,rebased:pd.DataFrame,
           v5_report:dict)->dict:
    if set(growth.sp)!=set(PRIMARY) or set(growth.state)!=set(TRAIN) or len(growth)!=EXPECTED_GROWTH_ROWS:
        raise ValueError("frozen five-taxon VA/WI biological development cohort changed")
    training=join_development_growth(growth,old_src,rebased)
    original_source=rebased[rebased.state.isin(TRAIN)]
    results=[]
    for sp in PRIMARY:
        cells=qualified_train_cells(original_source,sp)
        eligible=training.loc[(training.sp==sp)&training.cell.map(lambda z:z in cells)]
        reasons=[]
        if len(cells)<MIN_QUALIFIED_SHARED_CELLS:
            reasons.append("few_training_shared_climate_time_cells")
        for state in TRAIN:
            part=eligible.loc[eligible.state==state]
            if len(part)<MIN_TRAIN_GROWTH_PAIRS or part.county.nunique()<MIN_TRAIN_COUNTIES:
                reasons.append(state+":inadequate_old_development_growth_or_county_support")
        old_source_status=next(z for z in v5_report["source_species"] if z["species_code"]==sp)
        if not old_source_status["both_holdout_states_source_eligible"]:
            reasons.append("PA_or_MI_source_support_unavailable")
        item={"species_code":sp,
              "prior_holdout_PA_MI_source_ready":old_source_status["both_holdout_states_source_eligible"],
              "qualified_VA_WI_train_source_climate_cells":[list(z) for z in sorted(cells)],
              "n_qualified_training_joint_time_cells":len(cells),
              "n_old_selected_survivor_growth_rows_used":len(eligible),
              "n_old_growth_rows_by_state":{s:len(eligible.loc[eligible.state==s]) for s in TRAIN},
              "n_old_counties_by_state":{s:int(eligible.loc[eligible.state==s].county.nunique()) for s in TRAIN},
              "reasons":reasons,"status":"frozen_training_parameters_for_external_use" if not reasons
                        else "cannot_freeze_unqualified_external_transfer"}
        if not reasons:
            betas={}
            for m in models.MODELS:
                x=models.design(eligible,m)
                beta,_=models.fit_county_equal_region_equal(x,eligible.growth.to_numpy(float),eligible)
                if len(beta)!=len(FEATURES[m]):
                    raise ValueError("frozen source model column contract changed")
                betas[m]={k:float(v) for k,v in zip(FEATURES[m],beta)}
            item["fixed_model_coefficients"]=betas
            item["no_PA_MI_response_used_to_choose_model"]=True
        results.append(item)
    return {
      "program":PROGRAM,"status":"development_training_coefficients_before_external_response",
      "prior_fia_source_run":previous.SOURCE_RUN,
      "prior_fia_growth_input_SHA256":previous.INPUT_SHA256,
      "first_same_edition_source_run":V5_RUN,
      "first_same_edition_source_artifact":V5_SOURCE_ARTIFACT,
      "first_same_edition_training_CSV_SHA256":V5_TRAIN_SHA,
      "old_growth_selected_survivor_rows_considered":len(growth),
      "original_training_source_rows_rebased":len(rebased),
      "source_only_PA_MI_holdout_rows":83046,
      "fixed_species_priority":list(PRIMARY),
      "n_primary_models_frozen":sum(x["status"]=="frozen_training_parameters_for_external_use" for x in results),
      "models":list(models.MODELS),
      "model_features_in_fixed_order":FEATURES,
      "frozen_external_surrogate_branch_PA_to_VA_MI_to_WI":TRANSFER_BRANCH,
      "training_counties_equal_within_state_states_equal":True,
      "PA_MI_counties_and_responses_not_used_to_fit_any_coefficients":True,
      "new_external_growth_or_survival_outcome_opened":False,
      "external_RMSE_or_ecological_effect_estimated":False,
      "survivor_growth_training_not_population_mortality":True,
      "prior_response_still_postdevelopment_and_not_causal":True,
      "inference_target_future":"external common vs surrogate-regional climate slopes after release-consistent source supports",
      "predeclared_practical_RMSE_gain_threshold_percent":1.0,
      "no_biological_promotion_authorized":True,
      "species":results}


def run(growth_dir:Path,v5_dir:Path)->dict:
    g,old_src,report=previous.prepare_inputs(growth_dir)
    rebased,source_report=validate_v5(v5_dir)
    return freeze(g,old_src,rebased,source_report)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--old-growth-archive",type=Path,required=True)
    p.add_argument("--same-edition-v5-source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(a.old_growth_archive,a.same_edition_v5_source)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("external PA MI predictor freeze, primary species",result["n_primary_models_frozen"],"/5",
          "external growth outcomes NONE")


if __name__=="__main__":
    main()
