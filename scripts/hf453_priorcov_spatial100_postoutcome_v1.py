#!/usr/bin/env python3
"""HF453 100m spatial-group holdout after 2022 Y and prior covariate result opened.

Developmental, not confirmatory: original source SHA pinned; old 2019 gx/gy
are independent of 2022 Y, but spatial block size was specified AFTER seeing
the earlier positive parent holdout result. One 35ha Harvard forest only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import tempfile
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from hf253_hf453_original_tag_crosswalk_v2 import (
    fetch_HF253_provider_bytes, get_frozen_hf453,
    FROZEN_HF453_SHA, FROZEN_HF453_MD5, FROZEN_HF453_SIZE,
)
from hf453_prior_species_size_confounding_postoutcome_v1 import (
    read_HF253_prior, read_HF453_first_interval, build_risk_panel,
    ORIGINAL_HF253_SHA, ORIGINAL_HF253_BYTES,
)

PROGRAM = "sdmr_hf453_spatial100_parent_holdout_postoutcome_v1"
CONFIG_FILE=Path("configs/hf453_spatial_block_priorcov_postoutcome_v1.json")
WIDTH,HEIGHT,BLOCK=500.,700.,100.
MIN_BLOCKS,MIN_COVERAGE=10,0.8
LOCK_CONTENT="\n".join([
    f"program={PROGRAM}",
    "role=post_first_CP_parent_CV_spatial_sensitivity_NOT_confirmation",
    f"HF453_source_sha256={FROZEN_HF453_SHA}",
    f"HF253_source_sha256={ORIGINAL_HF253_SHA}",
    "first_parent_CV_run=44747246917",
    "block=100m_by_100m_source_2019_parent_centroid",
    "origin=0_0_HF253_gx_gy",
    "plot_dimensions_m=500_x_700",
    "exclude_original_parent_if_any_tag_coordinate_unavailable=true",
    "minimum_10_spatial_blocks_and_80pct_eligible_stems=true",
    "compare_parent_v_spatial_folds_same_stems_same_logit_models=true",
    "no_source_rows_coordinates_stem_or_tree_IDs_exported=true",
    "no_biome_causal_or_ProductB_promotion=true",
])+"\n"


def validate_spatial_contract(d:dict)->None:
    if d.get("schema")!="sdmr.hf453_priorcp_spatial_block_postoutcome_v1":
        raise ValueError("unknown_new_spatial_contract")
    if (d.get("status")!="post_first_prior_covariate_result_opened_no_spatial_source_values_seen"
        or d.get("role")!="SECOND_POST_OUTCOME_SPATIAL_SENSITIVITY_NOT_REPLICATION"
        or d.get("previous_priorcov_result_run")!=44747246917
        or d.get("first_priorcov_fixed_logloss_gain")!=0.000695237):
        raise ValueError("postoutcome_original_CP_result_or_role_modified")
    s=d["sources"]
    if (s.get("HF453_sha256")!=FROZEN_HF453_SHA
        or s.get("HF453_bytes")!=FROZEN_HF453_SIZE
        or s.get("HF253_sha256")!=ORIGINAL_HF253_SHA
        or s.get("HF253_bytes")!=ORIGINAL_HF253_BYTES):
        raise ValueError("original_HF253_HF453_byte_receipt_changed")
    geom=d["source_coordinate"]
    checks={
        "source_fieldnames":["stem.tag","tree.id","gx","gy"],
        "original_all_matching_stems":30808,
        "original_parent_tree_ids":27688,
        "source_plot_width_m":500,
        "source_plot_height_m":700,
        "parent_position":"arithmetic_centroid_of_all_matched_2019_stems_in_original_parent",
        "fixed_source_coordinate_validity":"finite_x_in_0_500_inclusive_and_y_in_0_700_inclusive",
    }
    for key, val in checks.items():
        if geom.get(key)!=val:
            raise ValueError("fixed_source_geometry_changed:"+key)
    folds=d["fold_geometry"]
    if (folds.get("block_size_m")!=100
        or folds.get("block_origin_x_m")!=0
        or folds.get("block_origin_y_m")!=0
        or folds.get("rectangular_plot_bins_x")!=5
        or folds.get("rectangular_plot_bins_y")!=7
        or folds.get("minimum_distinct_source_blocks")!=10
        or folds.get("min_fraction_geo_complete_of_original_CV_stems")!=0.8
        or folds.get("outer_split")!="GroupKFold_5_by_parent_centroid_100m_cells"
        or folds.get("comparator_split")!="GroupKFold_5_by_parent_tree_id_on_exact_same_spatial_eligible_stems"):
        raise ValueError("geographic_holdout_geometry_or_threshold_modified")
    if d["frozen_model"]["learner"]!="LogisticRegression_L2_C1_lbfgs_maxiter1000":
        raise ValueError("original_learner_changed_after_first_CP_result")
    if not all(d["output"][k] for k in (
        "postoutcome_exploratory","not_cross_forest_validation",
        "not_causal_process_identification","no_original_HF453_primary_result_rewriting"
    )):
        raise ValueError("postoutcome_scientific_ceiling_removed")


def parse_original_source_locations(stream,target:set[str])->tuple[dict,dict]:
    reader=csv.reader(stream)
    header=next(reader,None)
    if header and header[0].startswith("\xef\xbb\xbf"):header[0]=header[0][3:]
    cols=["stem.tag","tree.id","gx","gy"]
    if not header or len(set(header))!=len(header) or any(c not in header for c in cols):
        raise ValueError("source_prior_coordinate_headers_not_authorized")
    indices=[header.index(c) for c in cols]
    mapped={}
    nrows=0;nonascii_ids=0;missing_position=0;out_of_plot=0
    for row in reader:
        nrows+=1
        if len(row)!=len(header):
            raise ValueError("HF253_original_prior_position_row_width_changed")
        tag,parent,xstr,ystr=(row[i] for i in indices)
        if tag not in target:continue
        if (not tag.isascii() or not parent.isascii()
            or not parent or parent=="NA" or tag in mapped):
            raise ValueError("HF253_original_target_coordinate_identity_unstable")
        coord=None
        try:
            if xstr in ("","NA") or ystr in ("","NA"):
                missing_position+=1
            else:
                x=float(xstr);y=float(ystr)
                if not math.isfinite(x) or not math.isfinite(y):
                    missing_position+=1
                elif not (0<=x<=WIDTH and 0<=y<=HEIGHT):
                    out_of_plot+=1
                else:
                    coord=(x,y)
        except ValueError:
            missing_position+=1
        mapped[tag]=(parent,coord)
    if nrows!=123218 or set(mapped)!=target or len(target)!=30808:
        raise ValueError("original_matching_source_position_denominator_invalid")
    return mapped,{
        "n_original_source_rows":nrows,
        "n_original_target_stem_tags":len(target),
        "n_source_stems_with_missing_unusable_position":missing_position,
        "n_source_stems_outside_fixed_plot_rectangle":out_of_plot,
        "n_source_valid_stem_positions":len(target)-missing_position-out_of_plot,
        "no_species_dbh_health_outcome_or_2022_status_read_during_spatial_grain_definition":True,
    }


def original_parent_centroid_blocks(mapped:dict)->tuple[dict,dict]:
    parents=defaultdict(list)
    for tag,(parent,coord) in mapped.items():
        parents[parent].append(coord)
    if len(parents)!=27688:
        raise ValueError("original_distinct_source_parent_grain_drift")
    result={}
    incomplete=0;across_raw_cells=0
    for parent,coords in parents.items():
        if any(c is None for c in coords):
            incomplete+=1
            continue
        positions=[c for c in coords if c is not None]
        meanx=math.fsum(v[0] for v in positions)/len(positions)
        meany=math.fsum(v[1] for v in positions)/len(positions)
        block=(min(int(meanx//BLOCK),4),min(int(meany//BLOCK),6))
        result[parent]=block
        raw_cells={(min(int(x//BLOCK),4),min(int(y//BLOCK),6))
                   for x,y in positions}
        if len(raw_cells)>1:across_raw_cells+=1
    return result,{
        "n_original_parent_tree_ID_candidates":len(parents),
        "n_parent_IDs_with_any_missing_or_out_of_rectangle_stem_position":incomplete,
        "n_original_parent_IDs_with_valid_full_source_positions":len(result),
        "n_parents_with_matched_stems_in_multiple_native_100m_cells":across_raw_cells,
        "n_100m_source_blocks_among_all_original_parent_centroids":len(set(result.values())),
        "parent_centroids_from_original_stems_before_reading_new_2022_Y":True,
        "parent_tree_ID_not_exported":True,
    }


def evaluate_grouped_same_model(records:list[dict],mode:str,n_splits:int=5)->dict:
    if mode not in ("parent","spatial100"):
        raise ValueError("unknown_predeclared_grouped_validation")
    frame=pd.DataFrame(records).sort_values("tag").reset_index(drop=True)
    y=(frame["response"]=="p").to_numpy(dtype=int)
    if len(np.unique(y))<2 or min(np.bincount(y,minlength=2))<10:
        return {"status":"unavailable_known_response_class"}
    parents=frame["parent"].to_numpy()
    groups=(frame["parent"].to_numpy() if mode=="parent" else frame["spatial_block"].to_numpy())
    ngroups=len(set(groups))
    if ngroups<n_splits:
        return {"status":"unavailable_not_enough_source_groups","n_groups":ngroups}
    weight=1/frame.groupby("parent")["tag"].transform("size").to_numpy(dtype=float)
    X=frame[["sp","logdb","prior_unhealthy","cp_more"]].rename(columns={"sp":"species"})
    scores=np.full((len(frame),2),np.nan)
    folds=[]
    for f,(tr,te) in enumerate(GroupKFold(n_splits=n_splits).split(X,y,groups)):
        overlap=len(set(parents[tr])&set(parents[te]))
        if overlap:
            raise AssertionError("original_parent_reappeared_across_heldout_split")
        if min(np.bincount(y[tr],minlength=2))<10:
            return {"status":"unavailable_frozen_train_fold_event_count"}
        for j,numcols in enumerate((
            ["logdb","prior_unhealthy"],
            ["logdb","prior_unhealthy","cp_more"],
        )):
            prep=ColumnTransformer([
                ("species",OneHotEncoder(handle_unknown="ignore"),["species"]),
                ("numeric",StandardScaler(),numcols)
            ])
            model=Pipeline([
                ("preprocess",prep),
                ("logit",LogisticRegression(
                    C=1.,solver="lbfgs",max_iter=1000,class_weight=None,
                )),
            ])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always",ConvergenceWarning)
                model.fit(X.iloc[tr],y[tr],logit__sample_weight=weight[tr])
            if any(issubclass(w.category,ConvergenceWarning) for w in caught):
                return {"status":"STOP_frozen_parent_or_spatial_logit_not_converged"}
            scores[te,j]=model.predict_proba(X.iloc[te])[:,1]
        folds.append({
            "fold":f+1,
            "n_heldout_original_stems":len(te),
            "n_heldout_source_parent_IDs":len(set(parents[te])),
            "n_heldout_group_units":len(set(groups[te])),
            "n_heldout_original_known_dead":int(y[te].sum()),
            "n_training_heldout_shared_parent_IDs":overlap,
        })
    if not np.isfinite(scores).all():
        raise AssertionError("an original admitted stem was not scored once")
    p=np.clip(scores,1e-12,1-1e-12)
    logloss=-(y[:,None]*np.log(p)+(1-y[:,None])*np.log(1-p))
    brier=(scores-y[:,None])**2
    meanlog=(weight[:,None]*logloss).sum(axis=0)/weight.sum()
    meanbrier=(weight[:,None]*brier).sum(axis=0)/weight.sum()
    return {
        "status":"postoutcome_one_forest_groupfold_descriptive",
        "mode":mode,
        "n_folds":n_splits,
        "n_original_known_outcome_stems":len(frame),
        "n_original_parent_tree_IDs":len(set(parents)),
        "n_source_group_units":ngroups,
        "n_known_next_DC_DS":int(y.sum()),
        "n_heldout_parent_overlap":sum(x["n_training_heldout_shared_parent_IDs"] for x in folds),
        "folds":folds,
        "logloss_baseline":round(float(meanlog[0]),10),
        "logloss_plus_CP":round(float(meanlog[1]),10),
        "delta_logloss":round(float(meanlog[0]-meanlog[1]),10),
        "brier_baseline":round(float(meanbrier[0]),10),
        "brier_plus_CP":round(float(meanbrier[1]),10),
        "delta_brier":round(float(meanbrier[0]-meanbrier[1]),10),
        "not_independent_forest_or_causal_confirmation":True,
    }


def run_spatial_sensitivity(config:dict)->dict:
    validate_spatial_contract(config)
    with tempfile.TemporaryDirectory(prefix="hf453_spatial_postoutcome_") as tmp:
        a=Path(tmp)/"HF453_original_discarded.csv"
        b=Path(tmp)/"HF253_original_discarded.csv"
        src453=get_frozen_hf453(a)
        if src453!={"sha256":FROZEN_HF453_SHA,"md5":FROZEN_HF453_MD5,
                   "n_bytes":FROZEN_HF453_SIZE}:
            raise ValueError("HF453_original_file_bytes_changed")
        src253=fetch_HF253_provider_bytes(b)
        if src253["sha256"]!=ORIGINAL_HF253_SHA or src253["bytes"]!=ORIGINAL_HF253_BYTES:
            raise ValueError("HF253_original_file_bytes_changed")
        # Geographic admission uses original 2019-only tags/coords,
        # BEFORE the file is reopened for the already consumed 2022 Y.
        with a.open("r",encoding="latin-1",newline="") as f:
            from hf253_hf453_original_tag_crosswalk_v2 import original_HF453_2021_tag_source
            tags=original_HF453_2021_tag_source(f)
        with b.open("r",encoding="latin-1",newline="") as f:
            coordinates,source_position= parse_original_source_locations(f,tags)
        parent_blocks,source_parent=original_parent_centroid_blocks(coordinates)
        with b.open("r",encoding="latin-1",newline="") as f:
            prior,_=read_HF253_prior(f)
        with a.open("r",encoding="latin-1",newline="") as f:
            historical_y=read_HF453_first_interval(f)
        old_records,old_counts=build_risk_panel(historical_y,prior)
        matched=[r for r in old_records if r["response"]!="m"]
        geographic=[
            {**r,"spatial_block":str(parent_blocks[r["parent"]])}
            for r in matched if r["parent"] in parent_blocks
        ]
        removed=len(matched)-len(geographic)
        coverage=len(geographic)/max(1,len(matched))
        groups=len({r["spatial_block"] for r in geographic})
        if coverage<MIN_COVERAGE or groups<MIN_BLOCKS:
            cv_parent={"status":"unavailable_fixed_geography_coverage_or_blocks"}
            cv_spatial={"status":"unavailable_fixed_geography_coverage_or_blocks"}
            stage="original_source_geometry_coverage_unavailable"
        else:
            cv_parent=evaluate_grouped_same_model(geographic,"parent")
            cv_spatial=evaluate_grouped_same_model(geographic,"spatial100")
            stage="spatial_and_parent_sensitivity_completed"
        return {
            "status":stage,
            "original_HF453_sha256":src453["sha256"],
            "original_HF253_sha256":src253["sha256"],
            "original_2019_source_position":source_position,
            "original_preY_parent_centroid_block_frame":source_parent,
            "old_prior_covariate_complete_known_next_stems":len(matched),
            "n_source_stems_geographically_admitted_after_prior_covariates":len(geographic),
            "n_excluded_from_100m_block_validation":removed,
            "coverage_of_original_parent_CV_sample":round(coverage,8),
            "n_100m_spatial_blocks_in_admitted_sample":groups,
            "on_exact_same_geographic_subset_parent_grouped_CV":cv_parent,
            "on_exact_same_geographic_subset_spatial_block_grouped_CV":cv_spatial,
            "no_outcome_or_species_dbh_raster_source_selection_tuning":True,
            "no_individual_source_coords_rows_or_parent_IDs_exported":True,
            "postoutcome_second_sensitivity_not_original_confirmation":True,
            "one_forest_not_biome_transfer":True,
            "no_causal_canopy_mechanism_or_process_identity_estimated":True,
            "Product_B_unblocked":False,
        }


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",type=Path,default=CONFIG_FILE)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--execute-lock",type=Path)
    args=ap.parse_args()
    if args.preflight_only==(args.execute_lock is not None):
        ap.error("exactly one of --preflight-only or --execute-lock required")
    cfg=json.loads(args.config.read_text())
    validate_spatial_contract(cfg)
    if args.execute_lock and args.execute_lock.read_text()!=LOCK_CONTENT:
        raise ValueError("new_spatial_sensitivity_one_shot_protocol_changed")
    result={"status":"source_unopened_spatial_contract_only"} if args.preflight_only else run_spatial_sensitivity(cfg)
    output={
        "schema":"sdmr.hf453_spatial100_postoutcome_v1",
        "program":PROGRAM,
        "preflight":args.preflight_only,
        "one_forest":True,
        "post_original_HF453_Y_and_prior_CP_result_opening":True,
        "not_confirmatory_transfer_test":True,
        "original_first_status_and_priorCV_receipts_unchanged":True,
        "no_causal_process_identified":True,
        "Product_B_unblocked":False,
        "result":result,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print("HF453 frozen 100m spatial sensitivity:",result["status"])
    if not args.preflight_only:
        print("Spatial source coverage",result["coverage_of_original_parent_CV_sample"],
              "blocks",result["n_100m_spatial_blocks_in_admitted_sample"])
        print("Parent grouped gain",result["on_exact_same_geographic_subset_parent_grouped_CV"].get("delta_logloss"))
        print("Spatial grouped gain",result["on_exact_same_geographic_subset_spatial_block_grouped_CV"].get("delta_logloss"))


if __name__=="__main__":
    main()
