#!/usr/bin/env python3
"""Post-terminal v5 model-pool-only exploratory standardization probe.

Never imports/materializes the sealed answer-check. No v5 promotion effect.
Comparisons are diagnostic because v5 failures are already known.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 0
SPLITS = 3
FROZEN_ARTIFACTS = {
    "feature_zip": ("location_features_v5.parquet", "model_pool_feature_index_v5.csv", "background_300km_feature_index_v5.csv"),
    "occurrence_zip": ("model_pool_occurrences_v5.csv",),
    "pool_zip": ("model_pool_freeze/full_system_authorization_all_taxa.csv", "model_pool_freeze/taxon_model_freeze_summary.csv"),
}
SOURCE_DIGESTS = {
    "location_features_v5.parquet": "705f4e8d5db87eb60061258dc1e5d936be988e7b9ced45f936a866d7e8f015c5",
    "model_pool_feature_index_v5.csv": "fa33b8ccc6ded3f12ce34b58370c83b1d66857e795cebafa678789f7f317471b",
    "background_300km_feature_index_v5.csv": "6caba416d9aefc7345994eb97568b8f24d5565c7ad6fca906de58821e88049f0",
    "model_pool_occurrences_v5.csv": "5abd582c3c03b99f58263c720f76e04d08c54250daef942b06ae854fd721c624",
    "model_pool_freeze/full_system_authorization_all_taxa.csv": "8ce83beaefb6aa1f9996452e0835a0e9531386e26180db4760bf3847535cd475",
}

def open_frozen(path: Path, required: tuple[str, ...]) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        missing=set(required)-names
        if missing:
            raise ValueError(f"required frozen file missing from {path.name}: {sorted(missing)}")
        # Explicit allowlist: reading raw answer-check files is forbidden.
        result={name:z.read(name) for name in required}
    for name,data in result.items():
        if name in SOURCE_DIGESTS and hashlib.sha256(data).hexdigest()!=SOURCE_DIGESTS[name]:
            raise ValueError(f"frozen artifact byte hash mismatch: {name}")
    return result

def xyz(lon, lat):
    lon=np.deg2rad(np.asarray(lon,dtype=float))
    lat=np.deg2rad(np.asarray(lat,dtype=float))
    c=np.cos(lat)
    return np.column_stack([c*np.cos(lon),c*np.sin(lon),np.sin(lat)])

def bg_nearest_spatial_block(occ: pd.DataFrame, bg: pd.DataFrame) -> np.ndarray:
    """Reimplement v5 frozen nearest-occurrence spatial-group rule."""
    o=occ.sort_values("occurrence_id",kind="mergesort").reset_index(drop=True)
    tree=cKDTree(xyz(o.longitude, o.latitude))
    points=xyz(bg.longitude, bg.latitude)
    distances, indices=tree.query(points,k=1)
    groups=o.spatial_block.to_numpy(dtype=int)
    result=np.empty(len(bg),dtype=int)
    for i,(point,dist,idx) in enumerate(zip(points,distances,indices,strict=True)):
        choices=tree.query_ball_point(point,r=float(dist)+1e-12)
        if len(choices)<=1:
            chosen=int(idx)
        else:
            choices=np.asarray(choices,dtype=int)
            delta=xyz(o.longitude.iloc[choices],o.latitude.iloc[choices])-point
            d2=np.einsum("ij,ij->i",delta,delta)
            tied=choices[np.isclose(d2,np.min(d2),rtol=0,atol=1e-15)]
            chosen=int(np.min(tied))
        result[i]=groups[chosen]
    return result

def balanced_log_score(labels, probability) -> float:
    y=np.asarray(labels,dtype=int)
    p=np.clip(np.asarray(probability,dtype=float),1e-9,1.0-1e-9)
    if not (np.any(y==1) and np.any(y==0)):
        raise ValueError("fold missing a class")
    return 0.5*(float(np.log(p[y==1]).mean())+float(np.log1p(-p[y==0]).mean()))

def gate_stats(fold_predictions: list[tuple[np.ndarray,np.ndarray]]) -> dict:
    mean=float(np.mean([balanced_log_score(y,p) for y,p in fold_predictions]))
    rng=np.random.default_rng(SEED)
    n_above=0
    for _ in range(999):
        score=np.mean([balanced_log_score(rng.permutation(y),p) for y,p in fold_predictions])
        n_above+=bool(score >= mean)
    pv=(1+n_above)/1000.0
    return dict(observed_mean_score=mean,mean_gain_over_null=mean+math.log(2),
                p_value=pv,absolute_adequate=bool(mean >= -0.75),
                minimum_gain_met=bool(mean+math.log(2) >= 0.01),
                permutation_significant=bool(pv<=0.001),
                authorized=bool(mean >= -0.75 and mean+math.log(2)>=0.01 and pv<=0.001))

def probe_one(taxon, model_index, bg_index, occurrence, locations, predictors, frozen_auth):
    o=model_index.loc[(model_index.scientific_name==taxon)&model_index.complete_case].copy()
    all_occ=occurrence.loc[occurrence.scientific_name==taxon,["occurrence_id","longitude","latitude","spatial_block"]].copy()
    if all_occ.occurrence_id.duplicated().any():
        raise ValueError("duplicate frozen occurrence_id")
    o=o.merge(all_occ[["occurrence_id","spatial_block"]],on="occurrence_id",how="left",validate="one_to_one")
    if o.spatial_block.isna().any():
        raise ValueError(f"unmatched occurrence blocks: {taxon}")
    b=bg_index.loc[(bg_index.scientific_name==taxon)&bg_index.complete_case
                   &(bg_index.background_rank.mod(5)!=0)].copy()
    b["spatial_block"]=bg_nearest_spatial_block(all_occ,b)
    loc_cols=["location_id",*predictors]
    o=o.merge(locations[loc_cols],on="location_id",how="left",validate="many_to_one")
    b=b.merge(locations[loc_cols],on="location_id",how="left",validate="many_to_one")
    x=np.vstack([o[predictors].to_numpy(dtype=float),b[predictors].to_numpy(dtype=float)])
    y=np.r_[np.ones(len(o),dtype=int),np.zeros(len(b),dtype=int)]
    groups=np.r_[o.spatial_block.to_numpy(dtype=int),b.spatial_block.to_numpy(dtype=int)]
    if len(np.unique(groups))<SPLITS or not np.isfinite(x).all():
        raise ValueError(f"invalid frozen model-pool input for {taxon}")
    splits=list(GroupKFold(n_splits=SPLITS).split(x,y,groups))
    result={"scientific_name":taxon,"n_occurrence":len(o),"n_background":len(b)}
    for route in ("raw_logistic_v5_replay","standardized_logistic_exploratory"):
        fold_predictions=[]
        for train,test in splits:
            clf=LogisticRegression(C=1,penalty="l2",solver="lbfgs",max_iter=1000,
                                   random_state=0,class_weight="balanced")
            model=clf if route=="raw_logistic_v5_replay" else make_pipeline(StandardScaler(),clf)
            model.fit(x[train],y[train])
            pred=model.predict_proba(x[test])[:,1]
            fold_predictions.append((y[test],np.asarray(pred)))
        d=gate_stats(fold_predictions)
        result[route]=d
    frozen=frozen_auth.loc[(frozen_auth.scientific_name==taxon)&
                           (frozen_auth.learner_route=="penalized_logistic")].iloc[0]
    result["frozen_raw_score"]=float(frozen.observed_mean_score)
    result["raw_replay_absolute_error"]=abs(result["raw_logistic_v5_replay"]["observed_mean_score"]-result["frozen_raw_score"])
    result["score_gain_from_standardization"]=(
        result["standardized_logistic_exploratory"]["observed_mean_score"]-
        result["raw_logistic_v5_replay"]["observed_mean_score"])
    result["diagnostic_only"]=True
    return result

def run(*, feature_zip:Path, occurrence_zip:Path, pool_zip:Path, registry_path:Path,
        taxon_limit:int, output:Path):
    f=open_frozen(feature_zip,FROZEN_ARTIFACTS["feature_zip"])
    o=open_frozen(occurrence_zip,FROZEN_ARTIFACTS["occurrence_zip"])
    p=open_frozen(pool_zip,FROZEN_ARTIFACTS["pool_zip"])
    registry=pd.read_csv(registry_path)
    predictors=list(dict.fromkeys(registry.predictor.astype(str)))
    if len(predictors)!=46:
        raise ValueError("frozen 46 predictor count changed")
    locations=pd.read_parquet(io.BytesIO(f["location_features_v5.parquet"]))
    model_index=pd.read_csv(io.BytesIO(f["model_pool_feature_index_v5.csv"]))
    bg_index=pd.read_csv(io.BytesIO(f["background_300km_feature_index_v5.csv"]))
    occurrence=pd.read_csv(io.BytesIO(o["model_pool_occurrences_v5.csv"]))
    auth=pd.read_csv(io.BytesIO(p["model_pool_freeze/full_system_authorization_all_taxa.csv"]))
    summary=pd.read_csv(io.BytesIO(p["model_pool_freeze/taxon_model_freeze_summary.csv"]))
    taxa=summary.sort_values("selection_rank").scientific_name.astype(str).tolist()
    if len(taxa)!=50 or len(set(taxa))!=50:
        raise ValueError("frozen final50 cohort mismatch")
    if taxon_limit<1 or taxon_limit>50:
        raise ValueError("taxon limit must be 1..50")
    rows=[]
    for taxon in taxa[:taxon_limit]:
        item=probe_one(taxon,model_index,bg_index,occurrence,locations,predictors,auth)
        rows.append(item)
        print(f"{len(rows):2d}/{taxon_limit} {taxon}: raw={item['raw_logistic_v5_replay']['observed_mean_score']:.4f}"
              f" standardized={item['standardized_logistic_exploratory']['observed_mean_score']:.4f}",flush=True)
    matches=[r["raw_replay_absolute_error"] for r in rows]
    report={
        "schema":"sdmr.v5.postterminal_standardization_model_pool_probe.v1",
        "status":"exploratory_development_only_no_empirical_repromotion",
        "sampling":"first N frozen selection ranks, NOT selected by model result",
        "taxon_limit":taxon_limit,"frozen_taxon_denominator":50,
        "reference_v5_emp_d": {"stable_sharp_cells":16,"all_cells":300,"promotion":"failed_closed"},
        "truth_or_sealed_answer_check_read":False,
        "predictor_count":46,"folds":3,"training_only_scaler":True,
        "same_original_model_pool_folds":True,
        "baseline_replay": {"maximum_absolute_score_error":max(matches),
                            "all_within_1e-3":all(x<=1e-3 for x in matches)},
        "raw_authorized_count":sum(r["raw_logistic_v5_replay"]["authorized"] for r in rows),
        "scaled_authorized_count":sum(r["standardized_logistic_exploratory"]["authorized"] for r in rows),
        "scaled_better_taxa":sum(r["score_gain_from_standardization"]>0 for r in rows),
        "paired_mean_score_gain":float(np.mean([r["score_gain_from_standardization"] for r in rows])),
        "rows":rows,
        "interpretation_limit":"post-outcome method development; no causal mechanism or v5 improvement claim",
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},indent=2))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--feature-zip",type=Path,required=True)
    ap.add_argument("--occurrence-zip",type=Path,required=True)
    ap.add_argument("--pool-zip",type=Path,required=True)
    ap.add_argument("--registry",type=Path,required=True)
    ap.add_argument("--taxon-limit",type=int,default=10)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    run(feature_zip=a.feature_zip,occurrence_zip=a.occurrence_zip,pool_zip=a.pool_zip,
        registry_path=a.registry,taxon_limit=a.taxon_limit,output=a.output)

if __name__=="__main__":
    main()
