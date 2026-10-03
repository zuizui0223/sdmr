"""Fresh v3 model-pool-only process and comparator freeze.

This stage consumes only the prospectively frozen final50 model-pool occurrence
features and the training 4/5 of each 5000-row background. It does not read
answer-check coordinates, answer-check environmental values, or sealed outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from sdmr.baselines import vif_prune_predictors
from sdmr.process_id.evidence import (
    _balanced_log_score,
    _fit_probabilities,
    evaluate_occurrence_processes,
)
from sdmr.process_id.known_truth.permutation_gate import (
    evaluate_full_system_permutation_gate,
)
from sdmr.process_id.known_truth.worlds import KnownTruthWorld
from sdmr.process_information_closure import (
    normalize_process_information_registry,
)

PROGRAM="sdmr-fresh-empirical-v3-model-pool-freeze"
EXPECTED_TAXA=50
EXPECTED_PREDICTORS=46
EXPECTED_PROCESSES=(
    "thermal","water","seasonality","radiation_energy","soil_substrate","productivity"
)
PRIMARY_M_KM=300
BACKGROUND_ROWS_PER_TAXON=5000
BACKGROUND_TRAIN_ROWS=4000
INNER_SPLITS=3
MAX_FLAT_PREDICTORS=8
MARGIN=0.01
ADEQUACY_FLOOR=-0.75
SEM_MULTIPLIER=1.0
PERMUTATIONS=999
PERM_ALPHA=0.001
MIN_GAIN_OVER_NULL=0.01

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_freeze(path: str|Path)->dict:
    c=json.loads(Path(path).read_text())
    if c.get("schema")!="sdmr.fresh_empirical_v3_model_and_promotion_freeze.v1":
        raise ValueError("wrong fresh-v3 model freeze")
    if c.get("status")!="frozen_before_model_fit_and_answer_check_opening":
        raise ValueError("model design was not frozen pre-fit")
    if int(c["cohort"]["exact_taxa"])!=EXPECTED_TAXA:
        raise ValueError("final taxon denominator changed")
    if c["data_boundary"]["answer_check_occurrence_coordinates_opened"] is not False:
        raise ValueError("answer-check occurrence coordinates already opened")
    if c["data_boundary"]["answer_check_environmental_values_opened"] is not False:
        raise ValueError("answer-check environmental values already opened")
    p=c["process_identification"]["stage_p"]
    if int(p["n_inner_splits"])!=INNER_SPLITS:
        raise ValueError("inner process split count changed")
    if str(p.get("split_mode"))!="spatial":
        raise ValueError("fresh-v3 process split mode must be spatial")
    if float(p["margin"])!=MARGIN or float(p["adequacy_floor"])!=ADEQUACY_FLOOR:
        raise ValueError("process state thresholds changed")
    a=p["full_system_authorization"]
    if int(a["n_permutations"])!=PERMUTATIONS or float(a["alpha"])!=PERM_ALPHA:
        raise ValueError("full-system permutation gate changed")
    if float(a["minimum_gain_over_null"])!=MIN_GAIN_OVER_NULL:
        raise ValueError("minimum full-system gain changed")
    return c

def load_registry(path: str|Path)->pd.DataFrame:
    r=pd.read_csv(path)
    required={"predictor","process","role"}
    if required-set(r.columns):
        raise ValueError("process registry missing columns")
    if len(r)!=EXPECTED_PREDICTORS or r.predictor.astype(str).nunique()!=EXPECTED_PREDICTORS:
        raise ValueError("process registry predictor denominator changed")
    n=normalize_process_information_registry(
        r[["predictor","process","role"]],
        process_universe=EXPECTED_PROCESSES,
        predictor_universe=tuple(r.predictor.astype(str)),
    )
    if set(n.process.astype(str))!=set(EXPECTED_PROCESSES):
        raise ValueError("process registry process universe changed")
    return n

def _xyz(lon,lat):
    lon=np.radians(np.asarray(lon,float)); lat=np.radians(np.asarray(lat,float))
    c=np.cos(lat)
    return np.column_stack([c*np.cos(lon),c*np.sin(lon),np.sin(lat)])

def assign_background_groups(
    occurrence:pd.DataFrame,
    background:pd.DataFrame,
)->np.ndarray:
    req_o={"occurrence_id","longitude","latitude","spatial_block"}
    req_b={"longitude","latitude"}
    if req_o-set(occurrence.columns) or req_b-set(background.columns):
        raise ValueError("group assignment columns missing")
    o=occurrence.copy().sort_values("occurrence_id",kind="mergesort").reset_index(drop=True)
    tree=cKDTree(_xyz(o.longitude,o.latitude))
    distance,index=tree.query(_xyz(background.longitude,background.latitude),k=1)
    if not np.isfinite(distance).all():
        raise RuntimeError("non-finite nearest occurrence distance")
    return o.iloc[np.asarray(index,int)].spatial_block.to_numpy()

def _make_world(
    *,
    taxon:str,
    occurrence:pd.DataFrame,
    background:pd.DataFrame,
    predictors:tuple[str,...],
    registry:pd.DataFrame,
)->KnownTruthWorld:
    req={"longitude","latitude","spatial_block",*predictors}
    if req-set(occurrence.columns):
        raise ValueError(f"{taxon}: occurrence features missing")
    if {"longitude","latitude",*predictors}-set(background.columns):
        raise ValueError(f"{taxon}: background features missing")
    if occurrence[predictors].isna().any().any() or background[predictors].isna().any().any():
        raise ValueError(f"{taxon}: incomplete feature row entered model pool")

    occ=occurrence[["longitude","latitude","spatial_block",*predictors]].copy().reset_index(drop=True)
    bg=background[["longitude","latitude",*predictors]].copy().reset_index(drop=True)
    bg_groups=assign_background_groups(occurrence,background)
    occ_groups=occ.spatial_block.to_numpy()
    occ=occ.drop(columns="spatial_block")
    sample=pd.concat([occ,bg],ignore_index=True)
    sample.insert(0,"cell_id",np.arange(len(sample),dtype=int))
    occ2=sample.iloc[:len(occ)].copy().reset_index(drop=True)
    bg2=sample.iloc[len(occ):].copy().reset_index(drop=True)
    groups=np.concatenate([occ_groups,bg_groups])
    env=sample.copy()
    env["true_suitability"]=0.5
    return KnownTruthWorld(
        name=str(taxon),
        environment=env,
        true_suitability=np.full(len(env),0.5),
        occurrences=occ2,
        background=bg2,
        process_registry=registry.reset_index(drop=True),
        predictor_universe=tuple(predictors),
        process_universe=EXPECTED_PROCESSES,
        spatial_groups=np.asarray(groups),
        generating_processes=(),
        observation_unresolved_processes=(),
        model_pool_mask=np.ones(len(env),dtype=bool),
    )

def _authorize_and_classify(world:KnownTruthWorld, *, learner:str)->tuple[pd.DataFrame,dict]:
    kwargs={
      "n_splits":INNER_SPLITS,
      "split_mode":"spatial",
      "learner":learner,
      "C":1.0,
      "adequacy_floor":ADEQUACY_FLOOR,
      "n_permutations":PERMUTATIONS,
      "alpha":PERM_ALPHA,
      "permutation_seed":0,
      "minimum_gain_over_null":MIN_GAIN_OVER_NULL,
    }
    if learner=="hgb":
        kwargs["hgb_profile"]="shallow3"
    gate=evaluate_full_system_permutation_gate(world,**kwargs)
    ev=evaluate_occurrence_processes(
        world,
        n_splits=INNER_SPLITS,
        margin=MARGIN,
        adequacy_floor=ADEQUACY_FLOOR,
        sem_multiplier=SEM_MULTIPLIER,
        C=1.0,
        learner=learner,
        split_mode="spatial",
        hgb_profile="shallow3" if learner=="hgb" else "current",
        require_full_system_information=False,
    )
    states=ev.states.copy()
    if not bool(gate.summary["authorized"]):
        states["state"]="unavailable"
        states["reason"]="full_system_not_informative_permutation_gate"
    states["learner"]="shallow3_hgb" if learner=="hgb" else "penalized_logistic"
    states["full_system_authorized"]=bool(gate.summary["authorized"])
    states["full_system_permutation_p"]=float(gate.summary["p_value"])
    states["full_system_gain_over_null"]=float(gate.summary["mean_gain_over_null"])
    return states,dict(gate.summary)

def combine_stability(
    logistic:pd.DataFrame,
    hgb:pd.DataFrame,
)->pd.DataFrame:
    a=logistic[["process","state"]].rename(columns={"state":"logistic_state"})
    b=hgb[["process","state"]].rename(columns={"state":"hgb_state"})
    x=a.merge(b,on="process",validate="one_to_one")
    sharp={"replaceable","contributory","required"}
    stable=[]
    for row in x.itertuples(index=False):
        ls=str(row.logistic_state); hs=str(row.hgb_state)
        if "unavailable" in {ls,hs}:
            stable.append("unavailable")
        elif ls==hs and ls in sharp:
            stable.append(ls)
        elif ls==hs=="unresolved":
            stable.append("unresolved")
        else:
            stable.append("unresolved")
    x["stable_state"]=stable
    x["stable_sharp"]=x.stable_state.isin(sharp)
    return x

def retained_sdmr_predictors(
    registry:pd.DataFrame,
    stable_states:pd.DataFrame,
)->tuple[str,...]:
    state=dict(zip(stable_states.process.astype(str),stable_states.stable_state.astype(str)))
    rows=[]
    for predictor,grp in registry.groupby("predictor",sort=False):
        processes=tuple(dict.fromkeys(grp.process.astype(str)))
        drop=bool(processes) and all(state[p]=="replaceable" for p in processes)
        if not drop:
            rows.append(str(predictor))
    return tuple(rows)

def _split_indices(sample:pd.DataFrame, groups:np.ndarray):
    uniq=np.unique(groups)
    n=min(INNER_SPLITS,len(uniq))
    if n<2:
        raise ValueError("insufficient groups for inner selector CV")
    splitter=GroupKFold(n_splits=n)
    return list(splitter.split(np.zeros(len(sample)),sample.label.to_numpy(int),groups=groups))

def _metric_score(y,p,metric):
    if metric=="balanced_log_score":
        return float(_balanced_log_score(y,p))
    if metric=="auc":
        if len(np.unique(y))!=2:
            return float("nan")
        return float(roc_auc_score(y,p))
    raise ValueError(metric)

def score_predictors_cv(
    occurrence:pd.DataFrame,
    background:pd.DataFrame,
    groups_occ:np.ndarray,
    groups_bg:np.ndarray,
    predictors:tuple[str,...],
    *,
    metric:str,
)->float:
    if not predictors:
        return float("nan")
    occ=occurrence.copy(); bg=background.copy()
    occ["label"]=1; bg["label"]=0
    sample=pd.concat([occ,bg],ignore_index=True)
    groups=np.concatenate([groups_occ,groups_bg])
    scores=[]
    for tr,te in _split_indices(sample,groups):
        train=sample.iloc[tr].reset_index(drop=True)
        test=sample.iloc[te].reset_index(drop=True)
        _,p=_fit_probabilities(
            train,test,predictors,C=1.0,learner="hgb",hgb_profile="shallow3"
        )
        if np.isfinite(p).all():
            val=_metric_score(test.label.to_numpy(int),p,metric)
            if np.isfinite(val): scores.append(val)
    return float(np.mean(scores)) if scores else float("nan")

def forward_select(
    occurrence:pd.DataFrame,
    background:pd.DataFrame,
    groups_occ:np.ndarray,
    groups_bg:np.ndarray,
    predictors:tuple[str,...],
    *,
    metric:str,
    max_predictors:int=MAX_FLAT_PREDICTORS,
)->tuple[tuple[str,...],pd.DataFrame]:
    remaining=sorted(set(map(str,predictors)))
    selected=[]
    prefix=[]
    trace=[]
    for step in range(1,min(max_predictors,len(remaining))+1):
        candidates=[]
        for p in remaining:
            seq=tuple([*selected,p])
            score=score_predictors_cv(
                occurrence,background,groups_occ,groups_bg,seq,metric=metric
            )
            if np.isfinite(score):
                candidates.append((score,p,seq))
        if not candidates: break
        candidates.sort(key=lambda z:(-z[0],z[1]))
        score,p,seq=candidates[0]
        selected.append(p);remaining.remove(p)
        prefix.append((float(score),tuple(selected)))
        trace.append({"step":step,"chosen_predictor":p,"mean_inner_score":float(score),"metric":metric})
    if not prefix:
        raise RuntimeError(f"no evaluable {metric} forward-selection prefix")
    # Larger is better. Tie -> fewer predictors, then lexicographic sequence.
    best=sorted(prefix,key=lambda z:(-z[0],len(z[1]),z[1]))[0][1]
    return tuple(best),pd.DataFrame(trace)

def freeze_one_taxon(
    *,
    taxon:str,
    model_index:pd.DataFrame,
    bg_index:pd.DataFrame,
    location_features:pd.DataFrame,
    occurrence_geometry:pd.DataFrame,
    predictors:tuple[str,...],
    registry:pd.DataFrame,
)->tuple[pd.DataFrame,dict,list[pd.DataFrame]]:
    m=model_index.loc[model_index.scientific_name.astype(str).eq(taxon)].copy()
    b=bg_index.loc[
        bg_index.scientific_name.astype(str).eq(taxon)
        & (pd.to_numeric(bg_index.background_rank,errors="raise").astype(int)%5 != 0)
    ].copy()
    if len(b)!=BACKGROUND_TRAIN_ROWS:
        raise RuntimeError(f"{taxon}: training background rows {len(b)} != {BACKGROUND_TRAIN_ROWS}")
    if not m.complete_case.astype(bool).all() or not b.complete_case.astype(bool).all():
        raise RuntimeError(f"{taxon}: incomplete row survived passed feature gate")
    features=location_features.set_index("location_id")
    m=m.merge(features[list(predictors)],left_on="location_id",right_index=True,validate="many_to_one")
    b=b.merge(features[list(predictors)],left_on="location_id",right_index=True,validate="many_to_one")
    geo=occurrence_geometry[["scientific_name","occurrence_id","spatial_block"]].copy()
    m=m.merge(geo,on=["scientific_name","occurrence_id"],how="left",validate="one_to_one")
    if m.spatial_block.isna().any():
        raise RuntimeError(f"{taxon}: model-pool spatial block missing")
    groups_occ=m.spatial_block.to_numpy()
    groups_bg=assign_background_groups(m,b)

    world=_make_world(taxon=taxon,occurrence=m,background=b,predictors=predictors,registry=registry)
    lstate,lgate=_authorize_and_classify(world,learner="linear")
    hstate,hgate=_authorize_and_classify(world,learner="hgb")
    stable=combine_stability(lstate,hstate)
    stable.insert(0,"scientific_name",taxon)

    sdmr=retained_sdmr_predictors(registry,stable)
    auc,auc_trace=forward_select(m,b,groups_occ,groups_bg,predictors,metric="auc")
    flat,flat_trace=forward_select(m,b,groups_occ,groups_bg,predictors,metric="balanced_log_score")
    vif,vif_trace=vif_prune_predictors(b,list(predictors),threshold=5.0)
    vif=tuple(vif)

    row={
      "scientific_name":taxon,
      "hgb_full_system_authorized":bool(hgate["authorized"]),
      "hgb_full_system_permutation_p":float(hgate["p_value"]),
      "hgb_full_system_gain_over_null":float(hgate["mean_gain_over_null"]),
      "logistic_full_system_authorized":bool(lgate["authorized"]),
      "logistic_full_system_permutation_p":float(lgate["p_value"]),
      "logistic_full_system_gain_over_null":float(lgate["mean_gain_over_null"]),
      "sdmr_prediction_available":bool(hgate["authorized"]),
      "sdmr_predictors":";".join(sdmr),
      "sdmr_predictor_count":len(sdmr),
      "matched_flat_predictors":";".join(flat),
      "matched_flat_predictor_count":len(flat),
      "auc_flat_predictors":";".join(auc),
      "auc_flat_predictor_count":len(auc),
      "vif_predictors":";".join(vif),
      "vif_predictor_count":len(vif),
    }
    traces=[]
    for name,frame in (("matched_flat",flat_trace),("auc_flat",auc_trace),("vif",vif_trace)):
        q=frame.copy();q.insert(0,"scientific_name",taxon);q.insert(1,"selector",name);traces.append(q)
    return stable,row,traces

def run(*,feature_bundle,occurrence_split,selected,registry,freeze,output_dir):
    c=validate_freeze(freeze)
    selected_df=pd.read_csv(selected)
    if len(selected_df)!=EXPECTED_TAXA or selected_df.scientific_name.astype(str).nunique()!=EXPECTED_TAXA:
        raise ValueError("final50 identity denominator changed")
    if _sha256(selected)!=c["cohort"]["selected_manifest_sha256"]:
        raise ValueError("final50 manifest hash changed")
    reg=load_registry(registry); predictors=tuple(pd.read_csv(registry).predictor.astype(str))

    root=Path(feature_bundle)
    result=json.loads((root/"feature_gate_result_v3.json").read_text())
    if result.get("status")!="v3_feature_gate_passed" or result.get("all_taxa_complete_case_gate_passed") is not True:
        raise RuntimeError("fresh-v3 feature gate is not terminal PASS")
    if result.get("answer_check_accessed") is not False or result.get("model_fitting_performed") is not False:
        raise RuntimeError("feature stage crossed answer-check/model boundary")

    location=pd.read_parquet(root/"location_features_v3.parquet")
    model=pd.read_csv(root/"model_pool_feature_index_v3.csv")
    bg=pd.read_csv(root/"background_300km_feature_index_v3.csv")
    occ=pd.read_csv(Path(occurrence_split)/"model_pool_occurrences_v3.csv")
    if set(selected_df.scientific_name.astype(str))!=set(model.scientific_name.astype(str)):
        raise RuntimeError("feature model-pool final50 set changed")

    states=[];rows=[];traces=[]
    for taxon in selected_df.sort_values("selection_rank").scientific_name.astype(str):
        st,row,tr=freeze_one_taxon(
            taxon=taxon,model_index=model,bg_index=bg,location_features=location,
            occurrence_geometry=occ,predictors=predictors,registry=reg
        )
        states.append(st);rows.append(row);traces.extend(tr)

    states=pd.concat(states,ignore_index=True)
    summary=pd.DataFrame(rows)
    trace=pd.concat(traces,ignore_index=True,sort=False)
    if len(states)!=EXPECTED_TAXA*len(EXPECTED_PROCESSES):
        raise RuntimeError("process-state denominator changed")
    stable_fraction=float(states.stable_sharp.mean())
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    sp=out/"taxon_process_states_v3.csv"; pp=out/"taxon_predictor_sets_v3.csv"; tp=out/"selector_traces_v3.csv"
    states.to_csv(sp,index=False);summary.to_csv(pp,index=False);trace.to_csv(tp,index=False)
    receipt={
      "program":PROGRAM,
      "status":"model_pool_states_and_predictor_sets_frozen",
      "taxon_count":EXPECTED_TAXA,
      "process_cells":int(len(states)),
      "stable_sharp_process_fraction_model_pool":stable_fraction,
      "hgb_authorized_taxa":int(summary.hgb_full_system_authorized.sum()),
      "logistic_authorized_taxa":int(summary.logistic_full_system_authorized.sum()),
      "sdmr_prediction_available_taxa":int(summary.sdmr_prediction_available.sum()),
      "taxon_process_states_sha256":_sha256(sp),
      "taxon_predictor_sets_sha256":_sha256(pp),
      "selector_traces_sha256":_sha256(tp),
      "answer_check_accessed":False,
      "answer_check_environmental_values_read":False,
      "model_pool_model_fitting_performed":True,
      "sealed_scoring_performed":False,
      "post_fit_retuning_allowed":False,
      "next_gate":"freeze artifact receipt then open answer-check once under separate execution contract"
    }
    (out/"model_pool_freeze_result_v3.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--feature-bundle",required=True)
    p.add_argument("--occurrence-split",required=True)
    p.add_argument("--selected",required=True)
    p.add_argument("--registry",required=True)
    p.add_argument("--freeze",required=True)
    p.add_argument("--output-dir",required=True)
    a=p.parse_args()
    print(json.dumps(run(
        feature_bundle=a.feature_bundle,occurrence_split=a.occurrence_split,
        selected=a.selected,registry=a.registry,freeze=a.freeze,output_dir=a.output_dir
    ),indent=2,sort_keys=True))

if __name__=="__main__":
    main()
