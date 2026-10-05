"""Numeric environmental feature gate for fresh empirical v5 final50.

The final50 cohort is frozen upstream by geometry + all46 usable-support
preeligibility. This stage opens numeric environmental values only for the
already-frozen final50 model-pool occurrences and 300-km backgrounds.
Answer-check occurrences remain sealed and model fitting is forbidden.

The same six structural CHELSA decoding rules used by preeligibility are
applied deterministically before the unchanged complete-case gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.data.raster import extract_raster_values, probe_raster_layers
from sdmr.process_id.fresh.features import (
    EXPECTED_PREDICTORS,
    build_frozen_layer_specs,
    evaluate_complete_case_gate,
)
from sdmr.process_id.fresh.features_v3 import (
    STRUCTURAL_RULES,
    SOIL_PREDICTORS,
    SOIL_SHARD_COUNT,
    spatial_shard_bounds,
)

PROGRAM="sdmr-fresh-empirical-v5-feature-gate"
EXPECTED_TAXA=50
BACKGROUND_POINTS_PER_TAXON=5000
PRIMARY_M_KM=300

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _location_sha(frame: pd.DataFrame)->str:
    if list(frame.columns)!=["location_id","longitude","latitude"]:
        raise ValueError("v5 feature location-index columns changed")
    c=frame.copy()
    c["location_id"]=pd.to_numeric(c["location_id"],errors="raise").astype("int64")
    return hashlib.sha256(
        c.to_csv(index=False,float_format="%.17g",lineterminator="\n").encode("utf-8")
    ).hexdigest()

def load_final50(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={"selection_rank","candidate_rank","scientific_name","jointly_eligible"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v5 final50 manifest missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_TAXA or df.scientific_name.astype(str).nunique()!=EXPECTED_TAXA:
        raise ValueError("v5 feature stage requires exactly 50 frozen taxa")
    ranks=sorted(pd.to_numeric(df.selection_rank,errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_TAXA+1)):
        raise ValueError("v5 final50 ranks must be exactly 1..50")
    if not df.jointly_eligible.astype(bool).all():
        raise ValueError("v5 final50 includes a taxon that did not pass joint preeligibility")
    df["scientific_name"]=df.scientific_name.astype(str).str.strip()
    return df.sort_values("selection_rank").reset_index(drop=True)

def validate_contract(path: str|Path)->dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program")!=PROGRAM:
        raise ValueError("wrong v5 feature contract program")
    if c.get("status")!="staged_before_final50_numeric_value_read":
        raise ValueError("v5 feature contract status changed")
    if int(c.get("taxon_count",-1))!=EXPECTED_TAXA:
        raise ValueError("v5 feature taxon denominator changed")
    if int(c.get("predictor_count",-1))!=EXPECTED_PREDICTORS:
        raise ValueError("v5 feature predictor denominator changed")
    gate=c.get("complete_case_gate",{})
    if float(gate.get("minimum_model_pool_retention_fraction",-1))!=0.80:
        raise ValueError("v5 feature model retention gate changed")
    if int(gate.get("minimum_model_pool_complete_rows",-1))!=50:
        raise ValueError("v5 feature model row gate changed")
    if int(gate.get("minimum_background_complete_rows",-1))!=4000:
        raise ValueError("v5 feature background gate changed")
    for key in ("taxon_replacement","predictor_deletion","threshold_relaxation"):
        if gate.get(key) is not False:
            raise ValueError(f"v5 feature gate policy changed: {key}")
    if gate.get("imputation")!="none_outside_structural_source_decoding":
        raise ValueError("v5 feature imputation policy changed")
    expected=[
      {"predictor":p,"companion":comp,"operator":op,"condition_value":cond,
       "set_to":value,"reason":reason}
      for p,comp,op,cond,value,reason in STRUCTURAL_RULES
    ]
    if c.get("structural_source_decoding")!=expected:
        raise ValueError("v5 feature structural decoding rules changed")
    b=c.get("information_boundary",{})
    if b.get("numeric_environmental_values") is not True:
        raise ValueError("v5 numeric value read not explicitly authorized")
    if b.get("answer_check_access") is not False or b.get("model_fitting") is not False:
        raise ValueError("v5 feature information boundary changed")
    return c

def prepare_primary_points(*,selected_path,model_pool_path,background_path):
    selected=load_final50(selected_path)
    taxa=set(selected.scientific_name.astype(str))

    model=pd.read_csv(model_pool_path)
    req_m={"scientific_name","occurrence_id","longitude","latitude"}
    miss=req_m-set(model.columns)
    if miss:
        raise ValueError(f"v5 model-pool artifact missing columns: {sorted(miss)}")
    model=model.loc[model.scientific_name.astype(str).isin(taxa)].copy()
    if set(model.scientific_name.astype(str))!=taxa:
        raise ValueError("v5 final50 model-pool coverage changed")
    if model.occurrence_id.astype(str).duplicated().any():
        raise ValueError("v5 model-pool occurrence IDs must be unique")
    if len(model)<50*50:
        raise ValueError("v5 final50 model-pool denominator is implausibly small")

    bg=pd.read_csv(background_path)
    req_b={"scientific_name","m_km","background_rank","longitude","latitude"}
    miss=req_b-set(bg.columns)
    if miss:
        raise ValueError(f"v5 background artifact missing columns: {sorted(miss)}")
    bg=bg.loc[
        bg.scientific_name.astype(str).isin(taxa)
        & pd.to_numeric(bg.m_km,errors="raise").astype(int).eq(PRIMARY_M_KM)
    ].copy()
    per=bg.groupby(bg.scientific_name.astype(str)).size()
    if len(per)!=EXPECTED_TAXA or not per.eq(BACKGROUND_POINTS_PER_TAXON).all():
        raise ValueError("v5 final50 background is not exactly 5000 rows per taxon")

    model_idx=model[["scientific_name","occurrence_id","longitude","latitude"]].copy()
    model_idx.insert(1,"point_role","model_pool")
    model_idx["point_id"]=model_idx.occurrence_id.astype(str)

    bg_idx=bg[["scientific_name","background_rank","longitude","latitude"]].copy()
    bg_idx.insert(1,"point_role","background_300km")
    bg_idx["point_id"]=(bg_idx.scientific_name.astype(str)+"|bg300|"+
                        pd.to_numeric(bg_idx.background_rank,errors="raise").astype(int).astype(str))
    if bg_idx.point_id.duplicated().any():
        raise ValueError("v5 background point IDs must be unique")

    combined=pd.concat([
      model_idx[["scientific_name","point_role","point_id","longitude","latitude"]],
      bg_idx[["scientific_name","point_role","point_id","longitude","latitude"]],
    ],ignore_index=True)
    combined["longitude"]=pd.to_numeric(combined.longitude,errors="raise").astype(float)
    combined["latitude"]=pd.to_numeric(combined.latitude,errors="raise").astype(float)
    if not np.isfinite(combined[["longitude","latitude"]].to_numpy(float)).all():
        raise ValueError("v5 feature coordinates must be finite")

    locations=(combined[["longitude","latitude"]].drop_duplicates()
               .sort_values(["longitude","latitude"],kind="mergesort").reset_index(drop=True))
    locations.insert(0,"location_id",np.arange(len(locations),dtype=np.int64))
    model_idx=model_idx.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    bg_idx=bg_idx.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    model_idx["location_id"]=model_idx.location_id.astype("int64")
    bg_idx["location_id"]=bg_idx.location_id.astype("int64")
    return selected,model_idx,bg_idx,locations

def probe_layers(*,process_registry_path,chelsa_manifest_path):
    specs,_=build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    p=probe_raster_layers(specs)
    if len(p)!=EXPECTED_PREDICTORS or not p.status.eq("ok").all():
        raise RuntimeError("v5 feature raster probe is not 46/46 PASS")
    return p

def _spec_map(process_registry_path,chelsa_manifest_path):
    specs,_=build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    return {s.predictor:s for s in specs}

def extract_chelsa(*,predictor,selected_path,model_pool_path,background_path,
                   process_registry_path,chelsa_manifest_path,output_dir):
    _,_,_,locations=prepare_primary_points(
        selected_path=selected_path,model_pool_path=model_pool_path,background_path=background_path
    )
    by=_spec_map(process_registry_path,chelsa_manifest_path)
    predictor=str(predictor)
    if predictor not in by or by[predictor].source=="SoilGrids":
        raise ValueError("v5 CHELSA feature job received non-CHELSA predictor")
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

def extract_soil_shard(*,predictor,shard_index,shard_count,selected_path,
                       model_pool_path,background_path,process_registry_path,
                       chelsa_manifest_path,output_dir):
    predictor=str(predictor)
    if predictor not in SOIL_PREDICTORS or int(shard_count)!=SOIL_SHARD_COUNT:
        raise ValueError("v5 SoilGrids feature shard contract changed")
    _,_,_,locations=prepare_primary_points(
        selected_path=selected_path,model_pool_path=model_pool_path,background_path=background_path
    )
    start,stop=spatial_shard_bounds(len(locations),int(shard_index),int(shard_count))
    shard=locations.iloc[start:stop].copy().reset_index(drop=True)
    spec=_spec_map(process_registry_path,chelsa_manifest_path)[predictor]
    if spec.source!="SoilGrids":
        raise ValueError("v5 SoilGrids feature source changed")
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
      "start_row":int(start),"stop_row":int(stop),"shard_rows":int(len(part)),
      "full_location_rows":int(len(locations)),"location_index_sha256":_location_sha(locations),
      "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
      "finite_rows":int(finite.sum()),"missing_rows":int((~finite).sum()),
      "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def assemble_soil(*,parts_root,selected_path,model_pool_path,background_path,output_dir):
    _,_,_,locations=prepare_primary_points(
        selected_path=selected_path,model_pool_path=model_pool_path,background_path=background_path
    )
    locsha=_location_sha(locations)
    metas=sorted(Path(parts_root).rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    expected=len(SOIL_PREDICTORS)*SOIL_SHARD_COUNT
    if len(metadata)!=expected:
        raise RuntimeError(f"expected {expected} v5 SoilGrids feature shards; found {len(metadata)}")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for predictor in SOIL_PREDICTORS:
        rows=[m for m in metadata if m.get("predictor")==predictor]
        by={int(m["shard_index"]):m for m in rows}
        if set(by)!=set(range(SOIL_SHARD_COUNT)):
            raise RuntimeError(f"incomplete v5 SoilGrids feature shard set: {predictor}")
        frames=[];provs=[]
        for idx in range(SOIL_SHARD_COUNT):
            meta=by[idx]
            if meta.get("location_index_sha256")!=locsha:
                raise RuntimeError(f"v5 SoilGrids location fingerprint drift: {predictor}/{idx}")
            mp=next(p for p in metas if json.loads(p.read_text()).get("predictor")==predictor
                    and int(json.loads(p.read_text())["shard_index"])==idx)
            fp=mp.with_name("feature.parquet"); pp=mp.with_name("provenance.csv")
            if _sha256(fp)!=meta["feature_sha256"] or _sha256(pp)!=meta["provenance_sha256"]:
                raise RuntimeError(f"v5 SoilGrids shard SHA mismatch: {predictor}/{idx}")
            frames.append(pd.read_parquet(fp));provs.append(pd.read_csv(pp))
        f=pd.concat(frames,ignore_index=True).sort_values("location_id",kind="mergesort").reset_index(drop=True)
        if f.location_id.astype("int64").tolist()!=locations.location_id.astype("int64").tolist():
            raise RuntimeError(f"v5 SoilGrids feature coverage not exact: {predictor}")
        prov=pd.concat(provs,ignore_index=True).drop_duplicates()
        if len(prov)!=1:
            raise RuntimeError(f"v5 SoilGrids provenance differs across shards: {predictor}")
        d=out/predictor;d.mkdir(parents=True,exist_ok=True)
        fp=d/"feature.parquet";pp=d/"provenance.csv";mp=d/"metadata.json"
        f.to_parquet(fp,index=False);prov.to_csv(pp,index=False)
        meta={
          "program":PROGRAM,"predictor":predictor,"source_family":"SoilGrids",
          "location_rows":int(len(f)),"location_index_sha256":locsha,
          "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
          "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
          "spatial_shards":SOIL_SHARD_COUNT,
        }
        mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return {"program":PROGRAM,"status":"v5_soil_feature_assembly_passed","location_rows":len(locations)}

def apply_structural_decoding(features:pd.DataFrame):
    out=features.copy(); ledger=[]
    for predictor,companion,operator,condition,value,reason in STRUCTURAL_RULES:
        c=pd.to_numeric(out[companion],errors="coerce")
        cond=c.eq(condition) if operator=="eq" else c.gt(condition)
        mask=out[predictor].isna() & cond
        n=int(mask.sum())
        out.loc[mask,predictor]=float(value)
        ledger.append({
          "predictor":predictor,"companion":companion,"operator":operator,
          "condition_value":float(condition),"set_to":float(value),
          "corrected_rows":n,"reason":reason,"rule_is_predeclared":True,
        })
    return out,pd.DataFrame(ledger)

def aggregate(*,parts_root,selected_path,model_pool_path,background_path,
              process_registry_path,output_dir):
    _,model,bg,locations=prepare_primary_points(
        selected_path=selected_path,model_pool_path=model_pool_path,background_path=background_path
    )
    predictors=tuple(pd.read_csv(process_registry_path).predictor.astype(str))
    if len(predictors)!=EXPECTED_PREDICTORS or len(set(predictors))!=EXPECTED_PREDICTORS:
        raise ValueError("v5 feature predictor universe changed")
    metas=sorted(Path(parts_root).rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    by={str(m["predictor"]):m for m in metadata}
    if len(metadata)!=EXPECTED_PREDICTORS or set(by)!=set(predictors):
        raise RuntimeError("v5 feature metadata predictor set changed")
    locsha=_location_sha(locations)
    loc=locations[["location_id"]].copy().set_index("location_id")
    provs=[]; raw=[]
    for p in predictors:
        meta=by[p]
        if meta.get("location_index_sha256")!=locsha or int(meta.get("location_rows",-1))!=len(locations):
            raise RuntimeError(f"v5 feature location fingerprint changed: {p}")
        if meta.get("environmental_values_read") is not True or meta.get("answer_check_accessed") is not False or meta.get("model_fitting_performed") is not False:
            raise RuntimeError(f"v5 feature information boundary crossed: {p}")
        mp=next(x for x in metas if json.loads(x.read_text()).get("predictor")==p)
        fp=mp.with_name("feature.parquet"); pp=mp.with_name("provenance.csv")
        if _sha256(fp)!=meta["feature_sha256"] or _sha256(pp)!=meta["provenance_sha256"]:
            raise RuntimeError(f"v5 feature part SHA mismatch: {p}")
        f=pd.read_parquet(fp)
        if list(f.columns)!=["location_id",p]:
            raise RuntimeError(f"v5 feature columns changed: {p}")
        s=f.set_index(pd.to_numeric(f.location_id,errors="raise").astype("int64"))[p].reindex(loc.index)
        loc[p]=pd.to_numeric(s,errors="coerce")
        raw.append({"predictor":p,"raw_missing_rows":int(loc[p].isna().sum())})
        provs.append(pd.read_csv(pp))
    loc=loc.reset_index()
    decoded,ledger=apply_structural_decoding(loc)

    model2=model.merge(decoded,on="location_id",how="left",validate="many_to_one")
    bg2=bg.merge(decoded,on="location_id",how="left",validate="many_to_one")
    gate=evaluate_complete_case_gate(model_features=model2,background_features=bg2,predictors=predictors)
    all_pass=bool(gate.complete_case_gate_passed.all())
    complete=set(decoded.loc[decoded[list(predictors)].notna().all(axis=1),"location_id"].astype(int))
    model_idx=model.copy();model_idx["complete_case"]=model_idx.location_id.astype(int).isin(complete)
    bg_idx=bg.copy();bg_idx["complete_case"]=bg_idx.location_id.astype(int).isin(complete)
    post=[{"predictor":p,"post_decode_missing_rows":int(decoded[p].isna().sum())} for p in predictors]
    miss=pd.DataFrame(raw).merge(pd.DataFrame(post),on="predictor")
    prov=pd.concat(provs,ignore_index=True)

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    lp=out/"location_features_v5.parquet"; gp=out/"complete_case_gate_v5.csv"
    mp=out/"model_pool_feature_index_v5.csv";bp=out/"background_300km_feature_index_v5.csv"
    dp=out/"source_decoding_ledger_v5.csv";mis=out/"predictor_missingness_v5.csv";pp=out/"raster_provenance_v5.csv"
    decoded.to_parquet(lp,index=False);gate.to_csv(gp,index=False);model_idx.to_csv(mp,index=False)
    bg_idx.to_csv(bp,index=False);ledger.to_csv(dp,index=False);miss.to_csv(mis,index=False);prov.to_csv(pp,index=False)

    result={
      "program":PROGRAM,
      "status":"v5_feature_gate_passed" if all_pass else "v5_feature_gate_terminal_unavailable",
      "taxon_count":EXPECTED_TAXA,"predictor_count":EXPECTED_PREDICTORS,
      "unique_location_rows":int(len(decoded)),"model_pool_rows":int(len(model_idx)),
      "primary_background_rows":int(len(bg_idx)),
      "taxa_passing_complete_case_gate":int(gate.complete_case_gate_passed.sum()),
      "all_taxa_complete_case_gate_passed":all_pass,
      "minimum_model_pool_retention_fraction":float(gate.model_pool_retention_fraction.min()),
      "minimum_background_complete_rows":int(gate.background_complete_rows.min()),
      "structural_decoding_rows":int(ledger.corrected_rows.sum()),
      "location_features_sha256":_sha256(lp),"complete_case_gate_sha256":_sha256(gp),
      "model_pool_feature_index_sha256":_sha256(mp),"background_feature_index_sha256":_sha256(bp),
      "source_decoding_ledger_sha256":_sha256(dp),"predictor_missingness_sha256":_sha256(mis),
      "raster_provenance_sha256":_sha256(pp),
      "environmental_values_read":True,"answer_check_accessed":False,"model_fitting_performed":False,
      "taxon_replacement_performed":False,"predictor_deletion_performed":False,
      "threshold_relaxation_performed":False,
      "next_gate":"fit_frozen_process_first_and_flat_comparators_on_model_pool_only" if all_pass else "terminal_unavailable_no_replacement",
    }
    (out/"feature_gate_result_v5.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("probe");q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output",required=True)
    common=[("--selected",{"required":True}),("--model-pool",{"required":True}),("--background",{"required":True})]
    q=sub.add_parser("chelsa");q.add_argument("--predictor",required=True)
    for n,k in common:q.add_argument(n,**k)
    q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("soil-shard");q.add_argument("--predictor",required=True);q.add_argument("--shard-index",type=int,required=True);q.add_argument("--shard-count",type=int,default=SOIL_SHARD_COUNT)
    for n,k in common:q.add_argument(n,**k)
    q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("soil-assemble");q.add_argument("--parts-root",required=True)
    for n,k in common:q.add_argument(n,**k)
    q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate");q.add_argument("--parts-root",required=True)
    for n,k in common:q.add_argument(n,**k)
    q.add_argument("--process-registry",required=True);q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    if a.command=="probe":
        df=probe_layers(process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest)
        Path(a.output).parent.mkdir(parents=True,exist_ok=True);df.to_csv(a.output,index=False)
        result={"program":PROGRAM,"status":"probe_passed","layers":len(df)}
    elif a.command=="chelsa":
        result=extract_chelsa(predictor=a.predictor,selected_path=a.selected,model_pool_path=a.model_pool,background_path=a.background,process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir)
    elif a.command=="soil-shard":
        result=extract_soil_shard(predictor=a.predictor,shard_index=a.shard_index,shard_count=a.shard_count,selected_path=a.selected,model_pool_path=a.model_pool,background_path=a.background,process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir)
    elif a.command=="soil-assemble":
        result=assemble_soil(parts_root=a.parts_root,selected_path=a.selected,model_pool_path=a.model_pool,background_path=a.background,output_dir=a.output_dir)
    else:
        result=aggregate(parts_root=a.parts_root,selected_path=a.selected,model_pool_path=a.model_pool,background_path=a.background,process_registry_path=a.process_registry,output_dir=a.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
