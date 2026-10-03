"""Fresh empirical v3 environmental feature gate.

The final 50 taxa are already frozen by pre-outcome SoilGrids support
eligibility.  This stage may read numeric environmental values only for
model-pool occurrences and frozen 300-km backgrounds.  Answer-check
occurrences remain sealed and no model fitting is permitted here.

The six CHELSA structural source-decoding rules were established before the
v3 final cohort was selected.  They are applied deterministically before the
unchanged complete-case gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from sdmr.data.raster import extract_raster_values, probe_raster_layers
from sdmr.process_id.fresh.features import (
    EXPECTED_PREDICTORS,
    EXPECTED_CHELSA,
    EXPECTED_SOILGRIDS,
    build_frozen_layer_specs,
    evaluate_complete_case_gate,
)

PROGRAM="sdmr-fresh-empirical-v3-feature-gate"
EXPECTED_TAXA=50
EXPECTED_SELECTED_SHA256="4b49f457bcf8b74969e39144789c8e20a3b9739558475290f0a7abf77d7f9359"
EXPECTED_MODEL_POOL80_SHA256="0f1966002b6be5da354cbec503c9d2d4f33a5f2b56c0f26029fef0f05123b4ee"
EXPECTED_BACKGROUND80_SHA256="5c1e912e1392f327c81b286fce31b3f17d777021193b77f30caf4616d677e961"
EXPECTED_MODEL_POOL_ROWS=43_849
EXPECTED_BACKGROUND_ROWS=250_000
BACKGROUND_POINTS_PER_TAXON=5_000
PRIMARY_M_KM=300
SOIL_PREDICTORS=(
    "sg_phh2o_0_5",
    "sg_clay_0_5",
    "sg_soc_0_5",
    "sg_nitrogen_0_5",
)
SOIL_SHARD_COUNT=32

STRUCTURAL_RULES=(
    ("fcf","bio6","gt",0.0,0.0,"no_freezing_month_zero_freeze_thaw_transitions"),
    ("swe","scd","eq",0.0,0.0,"zero_snow_cover_days_zero_swe"),
    ("fgd","gsl","eq",365.0,1.0,"all_year_growing_season_first_day_1"),
    ("lgd","gsl","eq",365.0,365.0,"all_year_growing_season_last_day_365"),
    ("gdgfgd5","ngd5","eq",365.0,1.0,"all_year_above_5C_first_qualifying_day_1"),
    ("gdgfgd10","ngd10","eq",365.0,1.0,"all_year_above_10C_first_qualifying_day_1"),
)

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _location_sha(frame: pd.DataFrame)->str:
    required=["location_id","longitude","latitude"]
    if list(frame.columns)!=required:
        raise ValueError("v3 feature location index columns changed")
    canonical=frame.copy()
    canonical["location_id"]=pd.to_numeric(canonical["location_id"],errors="raise").astype("int64")
    payload=canonical.to_csv(index=False,float_format="%.17g",lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def load_final50(path: str|Path)->pd.DataFrame:
    if _sha256(path)!=EXPECTED_SELECTED_SHA256:
        raise ValueError("v3 final50 manifest fingerprint changed")
    df=pd.read_csv(path)
    required={"selection_rank","scientific_name","family","genus","candidate_rank","soil_support_eligible"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v3 final50 manifest missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_TAXA or df["scientific_name"].astype(str).nunique()!=EXPECTED_TAXA:
        raise ValueError("v3 feature stage requires exactly 50 frozen taxa")
    ranks=sorted(pd.to_numeric(df["selection_rank"],errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_TAXA+1)):
        raise ValueError("v3 final50 selection ranks must be exactly 1..50")
    if not df["soil_support_eligible"].astype(bool).all():
        raise ValueError("v3 final50 contains a taxon that did not pass support eligibility")
    df["scientific_name"]=df["scientific_name"].astype(str).str.strip()
    return df.sort_values("selection_rank").reset_index(drop=True)

def validate_contract(path: str|Path)->dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program")!=PROGRAM:
        raise ValueError("wrong v3 feature contract program")
    if c.get("status")!="frozen_before_numeric_environmental_value_read":
        raise ValueError("v3 feature contract is not pre-value frozen")
    if int(c.get("taxon_count",-1))!=EXPECTED_TAXA or int(c.get("predictor_count",-1))!=EXPECTED_PREDICTORS:
        raise ValueError("v3 feature taxon/predictor denominator changed")
    if c.get("selected_manifest_sha256")!=EXPECTED_SELECTED_SHA256:
        raise ValueError("v3 feature selected manifest fingerprint changed")
    missing=c.get("complete_case_gate",{})
    if float(missing.get("minimum_model_pool_retention_fraction",-1))!=0.80:
        raise ValueError("v3 model-pool retention gate changed")
    if int(missing.get("minimum_model_pool_complete_rows",-1))!=50:
        raise ValueError("v3 model-pool row gate changed")
    if int(missing.get("minimum_background_complete_rows",-1))!=4000:
        raise ValueError("v3 background complete-row gate changed")
    for key in ("taxon_replacement","predictor_deletion","threshold_relaxation","imputation"):
        expected=False if key!="imputation" else "none_outside_structural_source_decoding"
        if missing.get(key)!=expected:
            raise ValueError(f"v3 feature complete-case rule changed: {key}")
    frozen=c.get("structural_source_decoding",[])
    expected=[
      {
        "predictor":p,"companion":comp,"operator":op,"condition_value":cond,
        "set_to":value,"reason":reason
      }
      for p,comp,op,cond,value,reason in STRUCTURAL_RULES
    ]
    if frozen!=expected:
        raise ValueError("v3 structural source-decoding rules changed")
    boundary=c.get("information_boundary",{})
    if boundary.get("answer_check_access") is not False:
        raise ValueError("v3 feature contract opened answer-check")
    if boundary.get("model_fitting") is not False:
        raise ValueError("v3 feature contract allowed model fitting")
    if boundary.get("numeric_environmental_values") is not True:
        raise ValueError("v3 feature value read was not explicitly authorized")
    return c

def prepare_primary_points(*,selected_path,model_pool80_path,background80_path):
    selected=load_final50(selected_path)
    taxa=set(selected["scientific_name"].astype(str))
    if _sha256(model_pool80_path)!=EXPECTED_MODEL_POOL80_SHA256:
        raise ValueError("candidate80 model-pool artifact fingerprint changed")
    if _sha256(background80_path)!=EXPECTED_BACKGROUND80_SHA256:
        raise ValueError("candidate80 background artifact fingerprint changed")

    model=pd.read_csv(model_pool80_path)
    req_m={"scientific_name","occurrence_id","longitude","latitude"}
    miss=req_m-set(model.columns)
    if miss: raise ValueError(f"v3 model-pool artifact missing columns: {sorted(miss)}")
    model=model.loc[model["scientific_name"].astype(str).isin(taxa)].copy()
    if len(model)!=EXPECTED_MODEL_POOL_ROWS:
        raise ValueError(f"v3 final50 model-pool denominator changed: {len(model)}")
    if set(model["scientific_name"].astype(str))!=taxa:
        raise ValueError("v3 final50 model-pool taxon set changed")
    if model["occurrence_id"].astype(str).duplicated().any():
        raise ValueError("v3 model-pool occurrence IDs must be unique")

    bg=pd.read_csv(background80_path)
    req_b={"scientific_name","m_km","background_rank","gbifid","longitude","latitude"}
    miss=req_b-set(bg.columns)
    if miss: raise ValueError(f"v3 background artifact missing columns: {sorted(miss)}")
    bg=bg.loc[
        bg["scientific_name"].astype(str).isin(taxa)
        & pd.to_numeric(bg["m_km"],errors="raise").astype(int).eq(PRIMARY_M_KM)
    ].copy()
    if len(bg)!=EXPECTED_BACKGROUND_ROWS:
        raise ValueError("v3 final50 primary background denominator changed")
    per=bg.groupby(bg["scientific_name"].astype(str)).size()
    if len(per)!=EXPECTED_TAXA or not per.eq(BACKGROUND_POINTS_PER_TAXON).all():
        raise ValueError("v3 final50 background is not exactly 5000 rows per taxon")

    model_points=model[["scientific_name","occurrence_id","longitude","latitude"]].copy()
    model_points.insert(1,"point_role","model_pool")
    model_points["point_id"]=model_points["occurrence_id"].astype(str)

    bg_points=bg[["scientific_name","background_rank","gbifid","longitude","latitude"]].copy()
    bg_points.insert(1,"point_role","background_300km")
    bg_points["point_id"]=(bg_points["scientific_name"].astype(str)+"|bg300|"+
                           pd.to_numeric(bg_points["background_rank"],errors="raise").astype(int).astype(str))
    if bg_points["point_id"].duplicated().any():
        raise ValueError("v3 background point IDs must be unique")

    combined=pd.concat([
        model_points[["scientific_name","point_role","point_id","longitude","latitude"]],
        bg_points[["scientific_name","point_role","point_id","longitude","latitude"]],
    ],ignore_index=True)
    combined["longitude"]=pd.to_numeric(combined["longitude"],errors="raise").astype(float)
    combined["latitude"]=pd.to_numeric(combined["latitude"],errors="raise").astype(float)
    if not np.isfinite(combined[["longitude","latitude"]].to_numpy(float)).all():
        raise ValueError("v3 feature coordinates must be finite")

    locations=(combined[["longitude","latitude"]].drop_duplicates()
               .sort_values(["longitude","latitude"],kind="mergesort").reset_index(drop=True))
    locations.insert(0,"location_id",np.arange(len(locations),dtype=np.int64))
    model_points=model_points.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    bg_points=bg_points.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    model_points["location_id"]=model_points["location_id"].astype("int64")
    bg_points["location_id"]=bg_points["location_id"].astype("int64")
    return selected,model_points,bg_points,locations

def probe_layers(*,process_registry_path,chelsa_manifest_path):
    specs,_=build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    probe=probe_raster_layers(specs)
    if len(probe)!=EXPECTED_PREDICTORS or set(probe["predictor"].astype(str))!=set(s.predictor for s in specs):
        raise RuntimeError("v3 feature probe predictor denominator changed")
    return probe

def extract_chelsa_predictor(*,predictor,selected_path,model_pool80_path,background80_path,process_registry_path,chelsa_manifest_path,output_dir):
    _,_,_,locations=prepare_primary_points(
        selected_path=selected_path,model_pool80_path=model_pool80_path,background80_path=background80_path
    )
    specs,_=build_frozen_layer_specs(
        process_registry_path=process_registry_path,chelsa_manifest_path=chelsa_manifest_path
    )
    by={s.predictor:s for s in specs}
    predictor=str(predictor)
    if predictor not in by or by[predictor].source=="SoilGrids":
        raise ValueError("v3 CHELSA job received non-CHELSA predictor")
    featured,provenance=extract_raster_values(
        locations,[by[predictor]],lon_col="longitude",lat_col="latitude",checksum_local_files=False
    )
    part=featured[["location_id",predictor]].copy()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    fp=out/"feature.parquet";pp=out/"provenance.csv";mp=out/"metadata.json"
    part.to_parquet(fp,index=False);provenance.to_csv(pp,index=False)
    finite=pd.to_numeric(part[predictor],errors="coerce").notna()
    meta={
      "program":PROGRAM,"predictor":predictor,"source_family":"CHELSA",
      "location_rows":int(len(part)),"location_index_sha256":_location_sha(locations),
      "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
      "finite_rows":int(finite.sum()),"missing_rows":int((~finite).sum()),
      "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def spatial_shard_bounds(n_rows:int,shard_index:int,shard_count:int)->tuple[int,int]:
    if n_rows<1 or shard_count<1 or not 0<=shard_index<shard_count:
        raise ValueError("invalid v3 feature soil shard bounds")
    a=(n_rows*shard_index)//shard_count;b=(n_rows*(shard_index+1))//shard_count
    if b<=a: raise ValueError("empty v3 feature soil shard")
    return a,b

def extract_soil_shard(*,predictor,shard_index,shard_count,selected_path,model_pool80_path,background80_path,process_registry_path,chelsa_manifest_path,output_dir):
    predictor=str(predictor)
    if predictor not in SOIL_PREDICTORS:
        raise ValueError("v3 SoilGrids job predictor outside frozen set")
    if int(shard_count)!=SOIL_SHARD_COUNT:
        raise ValueError("v3 SoilGrids shard count changed")
    _,_,_,locations=prepare_primary_points(
        selected_path=selected_path,model_pool80_path=model_pool80_path,background80_path=background80_path
    )
    a,b=spatial_shard_bounds(len(locations),int(shard_index),int(shard_count))
    shard=locations.iloc[a:b].copy().reset_index(drop=True)
    specs,_=build_frozen_layer_specs(
        process_registry_path=process_registry_path,chelsa_manifest_path=chelsa_manifest_path
    )
    by={s.predictor:s for s in specs}
    spec=by[predictor]
    if spec.source!="SoilGrids": raise ValueError("v3 SoilGrids predictor source changed")
    featured,provenance=extract_raster_values(
        shard,[spec],lon_col="longitude",lat_col="latitude",checksum_local_files=False
    )
    part=featured[["location_id",predictor]].copy()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    fp=out/"feature.parquet";pp=out/"provenance.csv";mp=out/"metadata.json"
    part.to_parquet(fp,index=False);provenance.to_csv(pp,index=False)
    finite=pd.to_numeric(part[predictor],errors="coerce").notna()
    meta={
      "program":PROGRAM,"predictor":predictor,"source_family":"SoilGrids",
      "shard_index":int(shard_index),"shard_count":SOIL_SHARD_COUNT,
      "start_row":int(a),"stop_row":int(b),"shard_rows":int(len(part)),
      "full_location_rows":int(len(locations)),"location_index_sha256":_location_sha(locations),
      "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
      "finite_rows":int(finite.sum()),"missing_rows":int((~finite).sum()),
      "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def assemble_soil(*,parts_root,selected_path,model_pool80_path,background80_path,output_dir):
    _,_,_,locations=prepare_primary_points(
        selected_path=selected_path,model_pool80_path=model_pool80_path,background80_path=background80_path
    )
    locsha=_location_sha(locations); root=Path(parts_root)
    metas=sorted(root.rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    expected=len(SOIL_PREDICTORS)*SOIL_SHARD_COUNT
    if len(metadata)!=expected:
        raise RuntimeError(f"expected {expected} v3 SoilGrids feature shards; found {len(metadata)}")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for predictor in SOIL_PREDICTORS:
        rows=[m for m in metadata if m.get("predictor")==predictor]
        byidx={int(m["shard_index"]):m for m in rows}
        if set(byidx)!=set(range(SOIL_SHARD_COUNT)):
            raise RuntimeError(f"incomplete v3 SoilGrids feature shard set: {predictor}")
        frames=[];prov=[]
        for idx in range(SOIL_SHARD_COUNT):
            meta=byidx[idx]
            if meta.get("location_index_sha256")!=locsha:
                raise RuntimeError(f"v3 SoilGrids location fingerprint drift: {predictor}/{idx}")
            meta_path=next(p for p in metas if json.loads(p.read_text()).get("predictor")==predictor and int(json.loads(p.read_text())["shard_index"])==idx)
            fp=meta_path.with_name("feature.parquet"); pp=meta_path.with_name("provenance.csv")
            if _sha256(fp)!=meta["feature_sha256"] or _sha256(pp)!=meta["provenance_sha256"]:
                raise RuntimeError(f"v3 SoilGrids shard SHA mismatch: {predictor}/{idx}")
            frames.append(pd.read_parquet(fp));prov.append(pd.read_csv(pp))
        feature=pd.concat(frames,ignore_index=True).sort_values("location_id",kind="mergesort").reset_index(drop=True)
        if feature["location_id"].astype("int64").tolist()!=locations["location_id"].astype("int64").tolist():
            raise RuntimeError(f"v3 SoilGrids shard coverage not exact: {predictor}")
        provenance=pd.concat(prov,ignore_index=True).drop_duplicates()
        if len(provenance)!=1: raise RuntimeError(f"v3 SoilGrids provenance differs across shards: {predictor}")
        d=out/predictor;d.mkdir(parents=True,exist_ok=True)
        fp=d/"feature.parquet";pp=d/"provenance.csv";mp=d/"metadata.json"
        feature.to_parquet(fp,index=False);provenance.to_csv(pp,index=False)
        finite=pd.to_numeric(feature[predictor],errors="coerce").notna()
        meta={
          "program":PROGRAM,"predictor":predictor,"source_family":"SoilGrids",
          "location_rows":int(len(feature)),"location_index_sha256":locsha,
          "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
          "finite_rows":int(finite.sum()),"missing_rows":int((~finite).sum()),
          "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
          "spatial_shards":SOIL_SHARD_COUNT,
        }
        mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return {"program":PROGRAM,"status":"v3_soil_feature_assembly_passed","predictor_count":4,"location_rows":len(locations)}

def apply_structural_decoding(features:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    out=features.copy();ledger=[]
    for predictor,companion,operator,condition,value,reason in STRUCTURAL_RULES:
        p=out[predictor]; c=pd.to_numeric(out[companion],errors="coerce")
        cond=(c.eq(condition) if operator=="eq" else c.gt(condition))
        mask=p.isna() & cond
        count=int(mask.sum())
        out.loc[mask,predictor]=float(value)
        ledger.append({
          "predictor":predictor,"companion":companion,"operator":operator,
          "condition_value":float(condition),"set_to":float(value),
          "corrected_rows":count,"reason":reason,"rule_is_predeclared":True,
        })
    return out,pd.DataFrame(ledger)

def aggregate(*,parts_root,selected_path,model_pool80_path,background80_path,process_registry_path,output_dir):
    _,model_points,bg_points,locations=prepare_primary_points(
        selected_path=selected_path,model_pool80_path=model_pool80_path,background80_path=background80_path
    )
    registry=pd.read_csv(process_registry_path); predictors=tuple(registry["predictor"].astype(str))
    if len(predictors)!=EXPECTED_PREDICTORS or len(set(predictors))!=EXPECTED_PREDICTORS:
        raise ValueError("v3 feature aggregate predictor universe changed")
    root=Path(parts_root); metas=sorted(root.rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    by={str(m["predictor"]):m for m in metadata}
    if set(by)!=set(predictors) or len(by)!=EXPECTED_PREDICTORS:
        raise RuntimeError(f"v3 feature part predictor set changed: {len(by)}")
    locsha=_location_sha(locations)
    feature_paths={}
    provenance_paths={}
    for mp in metas:
        m=json.loads(mp.read_text()); p=str(m["predictor"])
        if m.get("location_index_sha256")!=locsha or int(m.get("location_rows",-1))!=len(locations):
            raise RuntimeError(f"v3 feature location fingerprint/denominator changed: {p}")
        if m.get("environmental_values_read") is not True or m.get("answer_check_accessed") is not False or m.get("model_fitting_performed") is not False:
            raise RuntimeError(f"v3 feature information boundary crossed: {p}")
        fp=mp.with_name("feature.parquet"); pp=mp.with_name("provenance.csv")
        if _sha256(fp)!=m["feature_sha256"] or _sha256(pp)!=m["provenance_sha256"]:
            raise RuntimeError(f"v3 feature part SHA mismatch: {p}")
        feature_paths[p]=fp;provenance_paths[p]=pp

    location_features=locations[["location_id"]].copy().set_index("location_id")
    raw_missing=[]
    for p in predictors:
        f=pd.read_parquet(feature_paths[p])
        if list(f.columns)!=["location_id",p]:
            raise RuntimeError(f"v3 feature columns changed: {p}")
        f["location_id"]=pd.to_numeric(f["location_id"],errors="raise").astype("int64")
        s=f.set_index("location_id")[p].reindex(location_features.index)
        location_features[p]=pd.to_numeric(s,errors="coerce")
        raw_missing.append({"predictor":p,"raw_missing_rows":int(s.isna().sum())})
    location_features=location_features.reset_index()
    decoded,ledger=apply_structural_decoding(location_features)

    model=model_points.merge(decoded,on="location_id",how="left",validate="many_to_one")
    bg=bg_points.merge(decoded,on="location_id",how="left",validate="many_to_one")
    gate=evaluate_complete_case_gate(model_features=model,background_features=bg,predictors=predictors)
    all_pass=bool(gate["complete_case_gate_passed"].all())
    complete=set(decoded.loc[decoded[list(predictors)].notna().all(axis=1),"location_id"].astype(int))
    model_idx=model_points.copy(); model_idx["complete_case"]=model_idx["location_id"].astype(int).isin(complete)
    bg_idx=bg_points.copy(); bg_idx["complete_case"]=bg_idx["location_id"].astype(int).isin(complete)
    post_missing=[{"predictor":p,"post_decode_missing_rows":int(decoded[p].isna().sum())} for p in predictors]
    missing=pd.DataFrame(raw_missing).merge(pd.DataFrame(post_missing),on="predictor")
    provenance=pd.concat([pd.read_csv(provenance_paths[p]) for p in predictors],ignore_index=True)

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    lp=out/"location_features_v3.parquet";led=out/"source_decoding_ledger_v3.csv"
    gp=out/"complete_case_gate_v3.csv";mp=out/"model_pool_feature_index_v3.csv"
    bp=out/"background_300km_feature_index_v3.csv";mis=out/"predictor_missingness_v3.csv";prov=out/"raster_provenance_v3.csv"
    decoded.to_parquet(lp,index=False);ledger.to_csv(led,index=False);gate.to_csv(gp,index=False)
    model_idx.to_csv(mp,index=False);bg_idx.to_csv(bp,index=False);missing.to_csv(mis,index=False);provenance.to_csv(prov,index=False)
    min_ret=gate.loc[gate["model_pool_retention_fraction"].astype(float).idxmin()]
    min_bg=gate.loc[gate["background_complete_rows"].astype(int).idxmin()]
    result={
      "program":PROGRAM,
      "status":"v3_feature_gate_passed" if all_pass else "v3_feature_gate_terminal_unavailable",
      "taxon_count":EXPECTED_TAXA,"predictor_count":EXPECTED_PREDICTORS,
      "unique_location_rows":int(len(decoded)),"model_pool_rows":int(len(model_idx)),
      "primary_background_rows":int(len(bg_idx)),
      "taxa_passing_complete_case_gate":int(gate["complete_case_gate_passed"].sum()),
      "all_taxa_complete_case_gate_passed":all_pass,
      "minimum_model_pool_retention_fraction":float(min_ret["model_pool_retention_fraction"]),
      "minimum_model_pool_retention_taxon":str(min_ret["scientific_name"]),
      "minimum_background_complete_rows":int(min_bg["background_complete_rows"]),
      "minimum_background_complete_taxon":str(min_bg["scientific_name"]),
      "structural_decoding_rows":int(ledger["corrected_rows"].sum()),
      "location_features_sha256":_sha256(lp),"source_decoding_ledger_sha256":_sha256(led),
      "complete_case_gate_sha256":_sha256(gp),"model_pool_feature_index_sha256":_sha256(mp),
      "background_feature_index_sha256":_sha256(bp),"predictor_missingness_sha256":_sha256(mis),
      "raster_provenance_sha256":_sha256(prov),
      "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
      "taxon_replacement_performed":False,"predictor_deletion_performed":False,"threshold_relaxation_performed":False,
      "next_gate":"fit_frozen_process_first_and_flat_comparators_on_model_pool_only" if all_pass else "terminal_unavailable_no_replacement",
    }
    (out/"feature_gate_result_v3.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("probe");q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output",required=True)
    q=sub.add_parser("chelsa");q.add_argument("--predictor",required=True);q.add_argument("--selected",required=True);q.add_argument("--model-pool80",required=True);q.add_argument("--background80",required=True);q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("soil-shard");q.add_argument("--predictor",required=True);q.add_argument("--shard-index",type=int,required=True);q.add_argument("--shard-count",type=int,default=SOIL_SHARD_COUNT);q.add_argument("--selected",required=True);q.add_argument("--model-pool80",required=True);q.add_argument("--background80",required=True);q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("soil-assemble");q.add_argument("--parts-root",required=True);q.add_argument("--selected",required=True);q.add_argument("--model-pool80",required=True);q.add_argument("--background80",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate");q.add_argument("--parts-root",required=True);q.add_argument("--selected",required=True);q.add_argument("--model-pool80",required=True);q.add_argument("--background80",required=True);q.add_argument("--process-registry",required=True);q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    if a.command=="probe":
        df=probe_layers(process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest)
        Path(a.output).parent.mkdir(parents=True,exist_ok=True);df.to_csv(a.output,index=False)
        result={"program":PROGRAM,"status":"probe_passed" if df.status.eq("ok").all() else "probe_failed","layers":len(df),"ok":int(df.status.eq("ok").sum())}
    elif a.command=="chelsa":
        result=extract_chelsa_predictor(predictor=a.predictor,selected_path=a.selected,model_pool80_path=a.model_pool80,background80_path=a.background80,process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir)
    elif a.command=="soil-shard":
        result=extract_soil_shard(predictor=a.predictor,shard_index=a.shard_index,shard_count=a.shard_count,selected_path=a.selected,model_pool80_path=a.model_pool80,background80_path=a.background80,process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir)
    elif a.command=="soil-assemble":
        result=assemble_soil(parts_root=a.parts_root,selected_path=a.selected,model_pool80_path=a.model_pool80,background80_path=a.background80,output_dir=a.output_dir)
    else:
        result=aggregate(parts_root=a.parts_root,selected_path=a.selected,model_pool80_path=a.model_pool80,background80_path=a.background80,process_registry_path=a.process_registry,output_dir=a.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
