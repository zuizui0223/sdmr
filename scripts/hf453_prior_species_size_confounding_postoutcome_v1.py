#!/usr/bin/env python3
"""HF453 prior-health+species+diameter confounding: post-outcome exploratory.

Never a new independent forest or causal process result. Source-frozen HF453
2021→2022 status and HF253 2019 prior covariates. The original first field
status result remains immutable, including missingness bounds and denominators.

Primary: 5 parent-tree GroupKFold OOF negative log-loss improvement from
adding prior CP (binary) to frozen prior-species, log DBH, baseline A/AU.
Secondary: species × 2019 DBH-bin × 2021 health standardized sharp-risk
difference, conditioned on fixed overlap and missingness rules.
No original CSV or any stem/tree ID leaves temporary runtime memory.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction as F
import json
import math
from pathlib import Path
import tempfile
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.exceptions import ConvergenceWarning

from hf253_hf453_original_tag_crosswalk_v2 import (
    fetch_HF253_provider_bytes,
    get_frozen_hf453,
    FROZEN_HF453_SHA,
    FROZEN_HF453_MD5,
    FROZEN_HF453_SIZE,
)

PROGRAM = "sdmr_hf453_prior_species_size_health_postoutcome_v1"
CONFIG_PATH = Path("configs/hf453_prior_species_size_postoutcome_v1.json")
ORIGINAL_HF253_SHA = "bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7"
ORIGINAL_HF253_BYTES = 12687409
YEAR_ORDER = ("2021", "2022")
ALIVE = {"A", "AU"}
DEAD = {"DC", "DS"}
UNKNOWN = {"DN", "", "NA"}
CP_GROUP = {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1}
MISSING = {"", "NA", "nan", "NaN"}
LOCK_TEXT = "\n".join([
    f"program={PROGRAM}",
    "role=post_HF453_Y_opening_exploration_not_independent_replication",
    f"HF453_original_sha256={FROZEN_HF453_SHA}",
    f"HF253_original_sha256={ORIGINAL_HF253_SHA}",
    "primary=2021_to_2022_source_coded_DC_DS_after_A_AU",
    "baseline=2019_sp_log1p_dbh_plus_2021_AU",
    "added_predictor=2021_prior_CP_binary_1_2_vs_3_4_5",
    "folds=GroupKFold_5_original_HF253_tree.id",
    "metric=parent_equal_OOF_log_loss_baseline_minus_plus_CP",
    "strata=2019_sp_x_four_dbh_bins_x_2021_AU",
    "min_strata_CP=10_primary_1_sensitivity",
    "missing_next_DN_not_auto_dead_or_alive",
    "no_original_microdata_archive_or_tree_ID_output=true",
    "no_causal_or_biome_transfer_claim=true",
    "M5_ProductA_unchanged_ProductB_blocked=true",
]) + "\n"


def validate_config(cfg: dict) -> None:
    if cfg.get("schema") != "sdmr.hf453_cp_prior_covariates_postoutcome_exploration.v1":
        raise ValueError("unfrozen_covariate_analysis_schema")
    if cfg.get("status") != "post_first_HF453_outcome_analysis_pre_new_covariate_opening":
        raise ValueError("covariate_preopen_status_changed")
    if cfg.get("role") != "POST_OUTCOME_EXPLORATORY_not_independent_confirmation":
        raise ValueError("scientific_status_not_postoutcome_exploration")
    a,b = cfg["source_HF453"],cfg["source_HF253"]
    if (a["raw_sha256"]!=FROZEN_HF453_SHA or a["md5"]!=FROZEN_HF453_MD5
            or a["bytes"]!=FROZEN_HF453_SIZE
            or a["expected_unique_stem_tags"]!=30808
            or [a[z] for z in (
                "expected_start_alive_2021","expected_known_dead_next",
                "expected_unknown_next","expected_CP_low_N","expected_CP_high_N"
            )]!=[21846,461,5,10452,11390]
            or b["raw_sha256"]!=ORIGINAL_HF253_SHA
            or b["bytes"]!=ORIGINAL_HF253_BYTES
            or b["expected_exact_stem_matches"]!=30808
            or b["expected_parent_tree_ids"]!=27688
            or b["prior_fields"]!=["stem.tag","stem.id","tree.id","sp","dbh"]):
        raise ValueError("original_source_or_first_response_frozen_receipt_changed")
    assert cfg["primary_interval"]==[2021,2022]
    status=cfg["status"]
    rules={
        "baseline_eligible":["A","AU"],
        "next_known_dead":["DC","DS"],
        "next_known_alive":["A","AU"],
        "next_unresolved":["DN","NA",""],
        "CP_lower":["1","2"],
        "CP_greater":["3","4","5"],
        "CP_unknown":["","NA"],
    }
    for k,v in rules.items():
        if status[k]!=v:
            raise ValueError("original_status_or_CP_contract_changed:"+k)
    prior=cfg["prior_covariates"]
    if (prior["prior_stem_diameter_cm"]!="dbh"
            or prior["original_species_code"]!="sp"
            or prior["valid_diameter_rule"]!="finite_gt_0_in_original_cm"
            or prior["baseline_health_2021"]!="A_versus_AU"
            or not prior["do_not_use_any_2019_source_status_or_later_2022_predictor"]
            or prior["size_bins_cm"]!={"small":"(0,10)",
                "medium":"[10,20)","large":"[20,40)",
                "very_large":"[40,infinity)"}):
        raise ValueError("prior_species_size_health_or_bin_contract_changed")
    info=cfg["primary_information_test"]
    if (info["n_splits"]!=5
            or info["n_model_min_per_class"]!=10
            or info["learner"]!="sklearn_LogisticRegression_L2_lbfgs_C1_max_iter1000"
            or info["split"]!="GroupKFold_K5_by_original_2019_tree.id_never_by_stem"
            or info["sample_weight"]!="inverse_count_of_eligible_stems_per_original_parent_tree"):
        raise ValueError("learner_or_parent_grouped_fold_protocol_changed")
    strat=cfg["secondary_stratification"]
    if (strat["primary_min_n_per_CP_in_each_stratum"]!=10
            or strat["sensitivity_min_n_per_CP_in_each_stratum"]!=1
            or strat["predeclared_groups"]!="exact_2019_sp_x_four_fixed_dbh_bins_x_2021_AU_health"):
        raise ValueError("overlap_or_strata_contract_changed")


def size_bin(dbh: float) -> str:
    if not math.isfinite(dbh) or dbh<=0:
        raise ValueError("not_positive_finite_2019_dbh")
    return "small" if dbh<10 else "medium" if dbh<20 else "large" if dbh<40 else "very_large"


def read_HF253_prior(stream, *, expected_rows:int=123218) -> tuple[dict, dict]:
    reader=csv.reader(stream)
    head=next(reader,None)
    if head and head[0].startswith("\xef\xbb\xbf"):
        head[0]=head[0][3:]
    cols=("stem.tag","stem.id","tree.id","sp","dbh")
    if not head or len(set(head))!=len(head) or any(c not in head for c in cols):
        raise ValueError("2019_species_dbh_source_columns_missing")
    ix=[head.index(v) for v in cols]
    data={}
    n=0
    invalid_key=0
    missing_sp=0
    missing_dbh=0
    for row in reader:
        n+=1
        if len(row)!=len(head):
            raise ValueError("2019_source_row_width_drift")
        tag,stemid,parent,sp,diam=(row[z] for z in ix)
        if tag in ("","NA"):continue
        if any(not v.isascii() or v!=v.strip() for v in (tag,stemid,parent)):
            invalid_key+=1
            continue
        if not stemid or not parent or stemid=="NA" or parent=="NA":
            invalid_key+=1
            continue
        if tag in data:
            raise ValueError("duplicate_original_2019_stem_tag")
        ok_sp=bool(sp and sp not in MISSING and sp.isascii() and sp==sp.strip())
        ok_dbh=False
        val=None
        if diam not in MISSING:
            try:
                val=float(diam)
                ok_dbh=math.isfinite(val) and val>0
            except ValueError:
                pass
        if not ok_sp:missing_sp+=1
        if not ok_dbh:missing_dbh+=1
        data[tag]={"parent":parent,"stem_id":stemid,
                   "sp":sp if ok_sp else None,
                   "dbh":val if ok_dbh else None}
    if n!=expected_rows or invalid_key!=0:
        raise ValueError("old_original_2019_source_identity_denominator_changed")
    return data,{"original_rows":n,"identity_rejected_rows":invalid_key,
                 "all_original_stem_tags":len(data),
                 "source_missing_species_rows":missing_sp,
                 "source_missing_diameter_rows":missing_dbh,
                 "species_diameter_are_2019_not_2021_values":True,
                 "original_2019_status_and_spatial_fields_never_used":True}


def read_HF453_first_interval(stream, *, expected_stems:int=30808)->dict:
    reader=csv.reader(stream)
    head=next(reader,None)
    if head and head[0].startswith("\xef\xbb\xbf"):head[0]=head[0][3:]
    cols=("StemTag","year","status","CP")
    if not head or len(set(head))!=len(head) or any(c not in head for c in cols):
        raise ValueError("original_HF453_status_or_CP_columns_missing")
    ix=[head.index(c) for c in cols]
    events={}
    n=0
    for row in reader:
        n+=1
        if len(row)!=len(head):
            raise ValueError("original_HF453_row_width_changed")
        tag,yr,stat,cp=(row[i] for i in ix)
        if yr not in ("2021","2022","2023","2024") or not tag.isascii():
            raise ValueError("HF453_source_identity_invalid")
        if yr not in YEAR_ORDER:
            continue
        if stat not in (ALIVE|DEAD|UNKNOWN):
            raise ValueError("unregistered_original_HF453_status")
        if yr=="2021" and cp not in (set(CP_GROUP)|{"","NA"}):
            raise ValueError("unregistered_start_CP")
        event=events.setdefault(tag,{})
        if yr in event:
            raise ValueError("duplicate_HF453_tag_year")
        event[yr]=(stat,cp if yr=="2021" else "")
    if n!=expected_stems*4 or len(events)!=expected_stems or any(len(e)!=2 for e in events.values()):
        raise ValueError("HF453_source_2021_2022_tag_frame_mismatch")
    return events


def build_risk_panel(HF453:dict,HF253:dict)->tuple[list[dict],dict]:
    if set(HF453)-set(HF253):
        raise ValueError("HF453_stem_unmatched_in_frozen_HF253")
    if len(HF453)!=30808:
        raise ValueError("HF453_original_risk_cohort_size_drift")
    parents={HF253[t]["parent"] for t in HF453}
    if len(parents)!=27688:
        raise ValueError("HF253_original_parent_ID_grain_drift")
    counter=Counter()
    data=[]
    for tag,record in HF453.items():
        baseline,cp=record["2021"];end,_=record["2022"]
        if baseline not in ALIVE:
            counter["baseline_not_alive_excluded"]+=1
            continue
        counter["baseline_alive"]+=1
        if end in DEAD:
            response="p";counter["next_known_dead"]+=1
        elif end in ALIVE:
            response="z";counter["next_known_alive"]+=1
        else:
            response="m";counter["next_unknown"]+=1
        if cp not in CP_GROUP:
            counter["start_CP_unknown"]+=1
            continue
        g=CP_GROUP[cp];counter["low_CP_N" if g==0 else "high_CP_N"]+=1
        prior=HF253[tag]
        if prior["sp"] is None:
            counter["eligible_prior_sp_missing"]+=1
        if prior["dbh"] is None:
            counter["eligible_prior_dbh_missing"]+=1
        if prior["sp"] is None or prior["dbh"] is None:
            counter["eligible_joint_prior_covariates_missing"]+=1
            continue
        data.append({
            "tag":tag,"parent":prior["parent"],
            "sp":prior["sp"],"dbh":prior["dbh"],
            "logdb":math.log1p(prior["dbh"]),
            "size_bin":size_bin(prior["dbh"]),
            "prior_unhealthy":int(baseline=="AU"),
            "cp_more":g,
            "response":response,
        })
    required={
        "baseline_alive":21846,"next_known_dead":461,
        "next_unknown":5,"low_CP_N":10452,"high_CP_N":11390,
        "start_CP_unknown":4,
    }
    for k,v in required.items():
        if counter[k]!=v:raise ValueError("frozen_original_field_result_denominator_changed:"+k)
    counter["n_complete_prior_covariates_in_both_CP"]=len(data)
    counter["n_original_parent_tree_IDs"]=len(parents)
    counter["n_distinct_prior_sp_in_complete_CP"]=len({z["sp"] for z in data})
    counter["n_complete_parent_tree_IDs"]=len({z["parent"] for z in data})
    counter["n_complete_known_next_status"]=sum(z["response"]!="m" for z in data)
    counter["n_complete_unknown_next_status"]=sum(z["response"]=="m" for z in data)
    return data,dict(sorted(counter.items()))


def sharp_stratified_standardization(records:list[dict], min_n:int)->dict:
    groups=defaultdict(lambda:{0:Counter(),1:Counter()})
    for row in records:
        key=(row["sp"],row["size_bin"],row["prior_unhealthy"])
        groups[key][row["cp_more"]][row["response"]]+=1
    eligible_n=0;excluded_n=0;included_strata=0;excluded_strata=0
    numerator_lo=F(0);numerator_hi=F(0)
    exposed=Counter()
    for row in groups.values():
        low,high=row[0],row[1]
        n0=sum(low.values());n1=sum(high.values())
        if n0<min_n or n1<min_n:
            excluded_n+=n0+n1;excluded_strata+=1
            continue
        included_strata+=1;eligible_n+=n0+n1
        lower=F(high["p"],n1)-F(low["p"]+low["m"],n0)
        upper=F(high["p"]+high["m"],n1)-F(low["p"],n0)
        numerator_lo+=(n0+n1)*lower
        numerator_hi+=(n0+n1)*upper
        exposed["low_N"]+=n0;exposed["high_N"]+=n1
        exposed["low_known_death"]+=low["p"]
        exposed["high_known_death"]+=high["p"]
        exposed["low_unknown"]+=low["m"]
        exposed["high_unknown"]+=high["m"]
    result={
        "status":"sharp_stratified_bounds_for_overlap_subset"
        if eligible_n else "no_joint_CP_overlap_for_fixed_strata",
        "minimum_original_CP_group_N_per_stratum":min_n,
        "n_original_strata":len(groups),
        "n_included_strata":included_strata,
        "n_excluded_strata":excluded_strata,
        "n_complete_prior_stems_all":len(records),
        "n_in_strata_with_both_CP_groups_eligible":eligible_n,
        "n_excluded_from_fixed_overlap":excluded_n,
        "original_exposure_ledger":dict(exposed),
        "sign":"unavailable","lower":None,"upper":None,
        "lower_pp":None,"upper_pp":None,
        "not_a_statistical_confidence_interval":True,
        "not_full_HF453_cohort_estimate":True,
        "not_causal":True,
    }
    if eligible_n:
        lo=numerator_lo/eligible_n;hi=numerator_hi/eligible_n
        result.update({
            "lower":str(lo),"upper":str(hi),
            "lower_pp":round(float(lo)*100,6),
            "upper_pp":round(float(hi)*100,6),
            "sign":("positive_for_all_unknown_outcomes" if lo>0 else
                    "negative_for_all_unknown_outcomes" if hi<0 else
                    "unresolved_including_zero"),
        })
    return result


def evaluate_parent_group_cv(records:list[dict],*,n_splits:int=5)->dict:
    # Keep unknown outcomes in the source ledger/stratified partial bounds,
    # but skip them for proper binary log-loss scoring.
    known=[r for r in records if r["response"]!="m"]
    if not known:
        return {"status":"unavailable_no_known_binary_status"}
    frame=pd.DataFrame(known).sort_values("tag").reset_index(drop=True)
    y=(frame["response"]=="p").to_numpy(dtype=int)
    groups=frame["parent"].to_numpy()
    nparents=frame["parent"].nunique()
    if nparents<n_splits or min(np.bincount(y))<10:
        return {"status":"unavailable_class_or_parent_diversity"}
    per_parent=frame.groupby("parent")["tag"].transform("size").to_numpy()
    weights=1/per_parent.astype(float)
    if not np.isclose(weights.sum(),nparents):
        raise AssertionError("equal-parent weighting error")
    X=frame[["sp","logdb","prior_unhealthy","cp_more"]].rename(columns={"sp":"species"})
    splitter=GroupKFold(n_splits=n_splits)
    scores=np.full((len(frame),2),np.nan,dtype=float)
    fold_reports=[]
    for fold,(tr,te) in enumerate(splitter.split(X,y,groups=groups)):
        if set(groups[tr])&set(groups[te]):
            raise AssertionError("a parent tree spans validation and training folds")
        if min(np.bincount(y[tr],minlength=2))<10:
            return {"status":"unavailable_frozen_fold_training_class_too_small"}
        for model_no,numerical in enumerate((
            ["logdb","prior_unhealthy"],
            ["logdb","prior_unhealthy","cp_more"],
        )):
            enc=ColumnTransformer(
                transformers=[
                    ("species",OneHotEncoder(handle_unknown="ignore"),["species"]),
                    ("numeric",StandardScaler(),numerical),
                ],
                remainder="drop",
            )
            mdl=Pipeline([
                ("preprocess",enc),
                ("logit",LogisticRegression(
                    C=1.0,solver="lbfgs",max_iter=1000,
                    class_weight=None,
                )),
            ])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                mdl.fit(X.iloc[tr],y[tr],
                        logit__sample_weight=weights[tr])
            if any(issubclass(w.category,ConvergenceWarning) for w in caught):
                return {"status":"STOP_frozen_logistic_not_converged"}
            scores[te,model_no]=mdl.predict_proba(X.iloc[te])[:,1]
        fold_reports.append({
            "fold":fold+1,
            "n_scored_stems":len(te),
            "n_scored_parent_trees":len(set(groups[te])),
            "n_known_death":int(y[te].sum()),
            "n_training_parent_tree_overlap":0,
        })
    if not np.isfinite(scores).all():
        raise AssertionError("not all original known-status records scored exactly once")
    clipped=np.clip(scores,1e-12,1-1e-12)
    logloss=-(y[:,None]*np.log(clipped)+(1-y[:,None])*np.log(1-clipped))
    brier=(scores-y[:,None])**2
    weighted_logloss=(weights[:,None]*logloss).sum(axis=0)/weights.sum()
    weighted_brier=(weights[:,None]*brier).sum(axis=0)/weights.sum()
    return {
        "status":"postoutcome_parent_grouped_OOF_description_only",
        "n_original_scored_stem_events":len(frame),
        "n_distinct_test_parent_trees":nparents,
        "n_2022_observed_dead_scored":int(y.sum()),
        "n_2022_observed_alive_scored":int((1-y).sum()),
        "n_folds":n_splits,
        "grouping":"original_2019_tree.id",
        "fold_reports":fold_reports,
        "mean_parent_equal_logloss_baseline":round(float(weighted_logloss[0]),10),
        "mean_parent_equal_logloss_plus_CP":round(float(weighted_logloss[1]),10),
        "delta_logloss_baseline_minus_plus_CP":round(float(weighted_logloss[0]-weighted_logloss[1]),10),
        "mean_parent_equal_brier_baseline":round(float(weighted_brier[0]),10),
        "mean_parent_equal_brier_plus_CP":round(float(weighted_brier[1]),10),
        "delta_brier_baseline_minus_plus_CP":round(float(weighted_brier[0]-weighted_brier[1]),10),
        "inter_model_comparison_only_after_HF453_original_Y_opening":True,
        "learner_agreement_or_increment_not_causal_process_identity":True,
        "no_biome_or_geographic_transfer_claim":True,
        "no_statistical_p_value_or_CI_claim":True,
    }


def run_exploration(cfg:dict)->dict:
    validate_config(cfg)
    with tempfile.TemporaryDirectory(prefix="sdmr_hf453_priorconfounder_") as root:
        f453=Path(root)/"original_HF453_not_retained.csv"
        f253=Path(root)/"original_HF253_not_retained.csv"
        a=get_frozen_hf453(f453)
        if a != {"sha256":FROZEN_HF453_SHA,"md5":FROZEN_HF453_MD5,
                 "n_bytes":FROZEN_HF453_SIZE}:
            raise ValueError("HF453_original_byte_identity_changed_before_postoutcome_test")
        b=fetch_HF253_provider_bytes(f253)
        if b["sha256"]!=ORIGINAL_HF253_SHA or b["bytes"]!=ORIGINAL_HF253_BYTES:
            raise ValueError("HF253_original_byte_identity_changed_before_postoutcome_test")
        with f253.open("r",encoding="latin-1",newline="") as s:
            prior,metadata=read_HF253_prior(s)
        with f453.open("r",encoding="latin-1",newline="") as s:
            original_risk=read_HF453_first_interval(s)
        records,eligibility=build_risk_panel(original_risk,prior)
        bounds10=sharp_stratified_standardization(records,10)
        bounds1=sharp_stratified_standardization(records,1)
        predictive=evaluate_parent_group_cv(records,n_splits=5)
        return {
            "status":"postoutcome_fixed_prior_covariate_exploration_completed",
            "source_integrity":{
                "HF453_original_sha256":a["sha256"],
                "HF253_original_sha256":b["sha256"],
                "HF253_original_bytes":b["bytes"],
                "HF253_publisher_MD5_claimed":False,
            },
            "source_prior_covariate_status":metadata,
            "full_original_source_cohort_eligibility":eligibility,
            "strict_CP_common_support_standardization":bounds10,
            "all_nonzero_CP_common_support_sensitivity":bounds1,
            "primary_parent_holdout_predictive_information":predictive,
            "original_HF453_first_outcome_not_recomputed_or_promoted":True,
            "exploratory_after_original_Y_opened":True,
            "one_forest_not_independent_ecosystem_replication":True,
            "no_raw_identifiers_species_rows_or_individual_outcomes_exported":True,
            "no_causal_light_competition_or_forest_transfer_claim":True,
            "Product_B_unblocked":False,
        }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--config",type=Path,default=CONFIG_PATH)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--execute-lock",type=Path)
    args=p.parse_args()
    if args.preflight_only==(args.execute_lock is not None):
        p.error("exactly one of --preflight-only or --execute-lock")
    cfg=json.loads(args.config.read_text())
    validate_config(cfg)
    if args.execute_lock is not None and args.execute_lock.read_text()!=LOCK_TEXT:
        raise ValueError("postoutcome_species_size_original_scientific_lock_changed")
    r={"status":"source_free_scientific_preflight_only"} if args.preflight_only else run_exploration(cfg)
    payload={
        "schema":"sdmr.hf453_prior_species_size_postoutcome_v1",
        "program":PROGRAM,
        "preflight":args.preflight_only,
        "original_HF453_Y_previously_opened":True,
        "postoutcome_exploratory_analysis":True,
        "one_forest_only":True,
        "no_new_independent_ecological_replication":True,
        "no_causal_process_identified":True,
        "not_SDMR_productA_M5_repromotion":True,
        "Product_B_unblocked":False,
        "result":r,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print("HF453 prior-covariate exploratory stage:",r["status"])
    if not args.preflight_only:
        q=r["primary_parent_holdout_predictive_information"]
        print("Parent OOF",q["status"],"delta_logloss",q.get("delta_logloss_baseline_minus_plus_CP"))
        s=r["strict_CP_common_support_standardization"]
        print("Fixed-strata overlap",s["n_in_strata_with_both_CP_groups_eligible"],
              "sign",s["sign"],"bounds_pp",s["lower_pp"],s["upper_pp"])


if __name__=="__main__":
    main()
