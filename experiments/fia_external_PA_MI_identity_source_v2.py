"""FIA PA/MI external source-only identity first opening without NOAA dependency.

This *distinct successor* preserves the historical 2026-11-18 v1 404 STOP.
At a fixed, previously unopened-state panel PA+MI, archive full PLOT/COND/TREE
source ZIP bytes and parse ONLY prior-visit SPCD, plot-chain history, county,
PLOT survey dates, and COND CSV *header*. NEVER open TREE DIA, STATUSCD,
individual demographics, growth, mortality or modeled environmental effects.
Existing VA/WI climate model and the older NOAA 20261006 remain untouched.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import fia_external_PA_MI_first_source_v1 as prior
import fia_joint_support_gate_v1 as joint
import fia_joint_source_only_v1 as reader

PROGRAM = "fia_PA_MI_unopened_holdout_identity_only_v2"
TRAIN_SRC_CSV_SHA = prior.SOURCE_CSV_SHA
TRAIN_SRC_RECEIPT_SHA = prior.SOURCE_RECEIPT_SHA
STATES = prior.STATES
SPECIES = prior.PRIOR_13
PRIORITY = prior.PRIOR_5
DATE_BIN_ORIGIN=1990
DATE_BIN_WIDTH=5
MIN_GAP_MONTHS=1
MAX_GAP_MONTHS=252
MAX_END_YEAR=2025
MIN_STATE_COUNTIES=5
MIN_STATE_PLOT_CHAINS=25
MIN_SHARED_COHORTS=2
MIN_CELL_COUNTIES=2
MIN_CELL_PLOTS=5
COLUMNS=("species_code","state","county_fips","plot_chain_id",
         "interval_id","prior_visit_year","prior_visit_month",
         "current_visit_year","current_visit_month","interval_end_year",
         "remeasurement_months")
ORIGINAL_V1_SOURCE_ONLY_RUN=44236792668
ORIGINAL_V1_STOP_ARTIFACT=14397208729


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_contract(cfg:dict)->None:
    expected={
      "program":PROGRAM,
      "holdout_states":list(STATES),
      "holdout_fips":prior.FIPS,
      "training_states":list(prior.TRAIN_STATES),
      "species_13":list(SPECIES),
      "priority_5":list(PRIORITY),
      "historical_first_source_stop_run":ORIGINAL_V1_SOURCE_ONLY_RUN,
      "old_NOAA_20261006_unavailable_not_replaced":True,
      "source_only_no_NOAA_or_TREE_outcome_values_read":True,
      "fixed_first_two_state_geographic_holdout":True,
      "original_training_run":43711159676,
      "original_training_artifact":14160283759,
      "original_training_csv_sha256":TRAIN_SRC_CSV_SHA,
      "original_training_receipt_sha256":TRAIN_SRC_RECEIPT_SHA,
      "minimum_holdout_state_counties":MIN_STATE_COUNTIES,
      "minimum_holdout_state_plot_chains":MIN_STATE_PLOT_CHAINS,
      "minimum_shared_five_year_periods":MIN_SHARED_COHORTS,
      "minimum_cohort_bin_counties":MIN_CELL_COUNTIES,
      "minimum_cohort_bin_plots":MIN_CELL_PLOTS,
      "no_same_cohort_species_promotion":True,
      "Product_A_M5_unchanged_and_Product_B_blocked":True,
    }
    for k,v in expected.items():
        if cfg.get(k)!=v:raise ValueError("external v2 identity-only contract changed: "+k)


def collect_candidate_plot_intervals(plots:dict,roots:dict,unstable:set)->tuple[dict,dict]:
    """Before tree status, county and remeasurement window strictly physical."""
    out={}
    c=Counter()
    for current,(previous,county,end) in plots.items():
        if not previous:continue
        c["n_current_visits_with_prior_PLOT_key"]+=1
        old=plots.get(previous)
        if old is None:
            c["previous_PLOT_not_present"]+=1;continue
        if roots[current] in unstable or roots[previous] in unstable:
            c["unstable_or_unknown_whole_PLOT_chain"]+=1;continue
        prior_county,start=old[1],old[2]
        if not county or not start or not end or prior_county!=county:
            c["missing_date_or_county_change"]+=1;continue
        gap=(end[0]*12+end[1])-(start[0]*12+start[1])
        if gap<MIN_GAP_MONTHS or gap>MAX_GAP_MONTHS:
            c["nonforward_or_more_than_21y_revisit"]+=1;continue
        if not 1991<=end[0]<=MAX_END_YEAR:
            c["current_visit_outside_original_NOAA_reanalysis_horizon"]+=1;continue
        out[current]=(previous,county,roots[current],start,end,gap)
    c["n_eligible_source_revisit_intervals_no_climate_join"]=len(out)
    return out,dict(c)


def first_prior_species_source_rows(state:str, eligible:dict, zipfile:Path, member:str)->tuple[list[dict],dict]:
    if state not in STATES:raise ValueError("not fixed external geographic state")
    previous={prior for prior,_,_,_,_,_ in eligible.values()}
    species_per_prior,counts=reader.read_tree_species_only(zipfile,member,previous)
    out=[]
    for current,(prior,county,chain,start,end,gap) in eligible.items():
        for sp in sorted(species_per_prior.get(prior,set()),key=int):
            out.append({"species_code":sp,"state":state,"county_fips":county,
                        "plot_chain_id":chain,"interval_id":current,
                        "prior_visit_year":start[0],"prior_visit_month":start[1],
                        "current_visit_year":end[0],"current_visit_month":end[1],
                        "interval_end_year":end[0],"remeasurement_months":gap})
    return out,{"n_prior_visited_plots_with_any_fixed_species":
                len(species_per_prior),"TREE_SPCD_PLT_CN_only":counts}


def bin_year(row:dict)->int:
    return (int(row["interval_end_year"])-DATE_BIN_ORIGIN)//DATE_BIN_WIDTH


def cohort_source_gate(old_training:list[dict], holdout:list[dict])->dict:
    """Compares only available PLOT *time* cohorts. NOT climate support."""
    if set(z["state"] for z in old_training)!={"RI","VA","WI"}:
        raise ValueError("original training states are unavailable")
    if set(z["state"] for z in holdout)-set(STATES):
        raise ValueError("unexpected holdout region in independent source")
    outputs=[]
    for sp in SPECIES:
        qualified={}
        for state in ("VA","WI"):
            buckets=defaultdict(lambda:{"county":set(),"plot":set()})
            for row in old_training:
                if row["species_code"]!=sp or row["state"]!=state:continue
                o=buckets[bin_year(row)]
                o["county"].add(row["county_fips"])
                o["plot"].add((row["county_fips"],row["plot_chain_id"]))
            qualified[state]={year for year,v in buckets.items()
                  if len(v["county"])>=MIN_CELL_COUNTIES
                  and len(v["plot"])>=MIN_CELL_PLOTS}
        shared=qualified["VA"]&qualified["WI"]
        by_state={}
        for state in STATES:
            relevant=[x for x in holdout if x["species_code"]==sp and x["state"]==state]
            county={x["county_fips"] for x in relevant}
            plots={(x["county_fips"],x["plot_chain_id"]) for x in relevant}
            plot_in={(x["county_fips"],x["plot_chain_id"]) for x in relevant if bin_year(x) in shared}
            available_periods=sorted({bin_year(x) for x in relevant})
            share=len(plot_in)/len(plots) if plots else None
            reasons=[]
            if len(county)<MIN_STATE_COUNTIES:reasons.append("too_few_external_FIA_counties")
            if len(plots)<MIN_STATE_PLOT_CHAINS:reasons.append("too_few_external_FIA_plot_chains")
            if len(shared)<MIN_SHARED_COHORTS:reasons.append("no_two_shared_training_5y_cohorts")
            if len({bin_year(x) for x in relevant if bin_year(x) in shared})<MIN_SHARED_COHORTS:
                reasons.append("few_external_5y_measurement_periods_in_training_cohort")
            by_state[state]={
                "n_prior_species_source_intervals":len(relevant),
                "n_distinct_counties":len(county),
                "n_distinct_plot_chains":len(plots),
                "n_year_cohorts_observed":len(available_periods),
                "n_source_plot_chains_in_training_cohort_only":len(plot_in),
                "source_time_cohort_plot_fraction":share,
                "identity_and_calendar_preflight_ready":not reasons,
                "reasons":reasons}
        outputs.append({
            "species_code":sp,"previously_frozen_priority":sp in PRIORITY,
            "training_VA_WI_shared_five_year_cohorts":sorted(shared),
            "training_5y_bins_determined_without_PA_MI":True,
            "holdout_states":by_state,
            "both_holdout_states_identity_time_ready":all(x["identity_and_calendar_preflight_ready"]
                                                          for x in by_state.values())
        })
    return {
       "program":PROGRAM,"status":"source_only_identity_calendar_readiness_no_climate",
       "source_species_denominator":len(SPECIES),
       "primary_species":list(PRIORITY),
       "species":outputs,
       "n_primary_both_holdouts_identity_time_ready":sum(x["previously_frozen_priority"] and
              x["both_holdout_states_identity_time_ready"] for x in outputs),
       "n_all_species_both_holdouts_identity_time_ready":sum(
              x["both_holdout_states_identity_time_ready"] for x in outputs),
       "NOAA_PA_MI_monthly_exposure_available":False,
       "temperature_precipitation_joint_common_support_evaluated":False,
       "n_PA_MI_tree_growth_mortality_outcomes_opened":0,
       "n_independent_biological_effect_tests":0,
       "no_demographic_or_causal_niche_inference":True,
       "NEON_not_required":True,
       "product_A_M5_unchanged_product_B_blocked":True,
       "biological_promotion_authorized":False}


def run(out:Path,train_dir:Path,train_cfg_path:Path,source_cfg_path:Path,fetcher=None)->dict:
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(source_cfg_path.read_text())
    verify_contract(cfg)
    oldcfg=json.loads(train_cfg_path.read_text())
    joint.verify_config(oldcfg)
    trainfile=train_dir/"fia_new_cohort_joint_source_only_county_stable_v2.csv"
    trainreceipt=train_dir/"derived_receipt.json"
    if sha(trainfile)!=TRAIN_SRC_CSV_SHA or sha(trainreceipt)!=TRAIN_SRC_RECEIPT_SHA:
        raise ValueError("historic training source-only first-read SHA mismatch")
    train=joint.read_source_only_csv(trainfile,trainreceipt,oldcfg)
    if len(train)!=89616:raise ValueError("historic original taxon/plot/time denominator drift")
    audit={"program":PROGRAM,"previous_failed_v1_run_preserved":ORIGINAL_V1_SOURCE_ONLY_RUN,
           "reason_for_successor":"NOAA 20261006 raw URL 404 before opening PA or MI FIA source",
           "states":[], "n_original_training_source_intervals":len(train),
           "status":"not_available_before_first_identity_read",
           "tree_DIA_STATUSCD_growth_mortality_not_read":True}
    try:
        rows=[]
        for state in STATES:
            state_audit={"state":state,"source_files":{},"status":"source_unavailable"}
            audit["states"].append(state_audit)
            parts={}
            for table in ("PLOT","COND","TREE"):
                path,meta=prior.fetch_fia_zip(state,table,out,fetcher=fetcher)
                if sha(path)!=meta["zip_sha256"]:raise ValueError("archive bytes changed before source-only opening")
                state_audit["source_files"][table]=meta
                parts[table]=(path,meta["csv_member"])
            plots,roots,plotqc=prior.plot_source(*parts["PLOT"],state)
            state_audit["PLOT_metadata"]=plotqc["counts"]
            state_audit["COND_header_required_fields"]=prior.inspect_cond_source_header(*parts["COND"])
            eligible,reasons=collect_candidate_plot_intervals(plots,roots,plotqc["unstable_plot_chains"])
            extracted,treeqc=first_prior_species_source_rows(state,eligible,*parts["TREE"])
            state_audit["plot_remeasurement_eligibility"]=reasons
            state_audit["tree_prior_species_only"]=treeqc
            state_audit["n_source_identity_time_intervals"]=len(extracted)
            state_audit["status"]="source_identity_only_ready"
            rows.extend(extracted)
        if not rows or set(x["state"] for x in rows)!=set(STATES):
            raise ValueError("one or both external source state panels have no eligible prior-species plot interval")
        unique=set()
        stable={}
        for row in rows:
            key=(row["species_code"],row["state"],row["interval_id"])
            if key in unique:raise ValueError("duplicate species x source interval identity")
            unique.add(key)
            place=(row["state"],row["plot_chain_id"])
            if place in stable and stable[place]!=row["county_fips"]:
                raise ValueError("whole-chain county drift across interval source")
            stable[place]=row["county_fips"]
        outfile=out/"PA_MI_source_only_prior_species_plot_intervals_v2.csv"
        with outfile.open("w",encoding="utf-8",newline="") as fh:
            writer=csv.DictWriter(fh,fieldnames=COLUMNS,lineterminator="\n")
            writer.writeheader()
            writer.writerows(sorted(rows,key=lambda x:(
                int(x["species_code"]),x["state"],x["county_fips"],
                x["plot_chain_id"],x["interval_id"])))
        result=cohort_source_gate(train,rows)
        result["holdout_prior_species_plot_intervals"]=len(rows)
        result["holdout_derived_source_CSV_sha256"]=sha(outfile)
        result["original_training_source_CSV_sha256"]=TRAIN_SRC_CSV_SHA
        result["holdout_state_panels_present"]=sorted({z["state"] for z in rows})
        audit["status"]="source_identity_only_ready_no_climate_join"
        audit["holdout_derived_csv_sha256"]=sha(outfile)
        audit["holdout_identity_source_rows"]=len(rows)
        (out/"PA_MI_identity_only_cohort_preflight_v2.json").write_text(
            json.dumps(result,sort_keys=True,indent=2)+"\n")
    except Exception as exc:
        audit["status"]="identity_source_failed_closed_before_biological_outcomes"
        audit["failure_class"]=type(exc).__name__
        audit["failure_reason"]=str(exc)[:330]
        result={"program":PROGRAM,"status":"identity_source_failed_closed_before_biological_outcomes",
                "n_prior_tree_source_plot_intervals_unknown_not_zero":True,
                "no_biological_outcome_opened":True,
                "n_independent_biological_effect_tests":0,
                "biological_promotion_authorized":False}
        (out/"PA_MI_identity_only_cohort_preflight_v2.json").write_text(
            json.dumps(result,sort_keys=True,indent=2)+"\n")
        (out/"PA_MI_source_only_prior_species_plot_intervals_v2.csv").unlink(missing_ok=True)
    (out/"PA_MI_identity_source_receipt_v2.json").write_text(
        json.dumps(audit,sort_keys=True,indent=2)+"\n")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--training-source",required=True,type=Path)
    p.add_argument("--training-config",type=Path,default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    p.add_argument("--source-config",type=Path,default=Path("configs/fia_PA_MI_identity_only_v2.json"))
    a=p.parse_args()
    result=run(a.out,a.training_source,a.training_config,a.source_config)
    print("PA MI SOURCE-ONLY IDENTITY:",result["status"],
          "priority source-time cohort readiness",
          result.get("n_primary_both_holdouts_identity_time_ready"),
          "of 5, NO demographic outcome")
    if result["status"]!="source_only_identity_calendar_readiness_no_climate":
        raise SystemExit(2)


if __name__=="__main__":
    main()
