"""All-46 pre-eligibility support runtime for fresh empirical v5.

Only candidates that passed the frozen v5 geometry gate are sampled. Numeric
environmental values may be opened in memory, but artifacts persist only
location_id + boolean usable-support bits and candidate-level counts.
Answer-check coordinates/features and model fitting remain forbidden.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.data.raster import extract_raster_values
from sdmr.process_id.fresh.cohort_v4_all46_support import (
    SOIL_PREDICTORS,
    SOIL_SHARD_COUNT,
    STRUCTURAL_RULES,
    _specs,
    _usable_from_values,
    spatial_shard_bounds,
)

PROGRAM="sdmr-fresh-empirical-v5-all46-support-runtime"
EXPECTED_CANDIDATES=120
EXPECTED_FINAL=50
EXPECTED_PREDICTORS=46
BACKGROUND_ROWS_PER_CANDIDATE=5000
MODEL_MIN_FRACTION=0.80
MODEL_MIN_ROWS=50
BACKGROUND_MIN_ROWS=4000
PRIMARY_M_KM=300

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _location_sha(frame: pd.DataFrame)->str:
    required=["location_id","longitude","latitude"]
    if list(frame.columns)!=required:
        raise ValueError("v5 support location-index columns changed")
    canonical=frame.copy()
    canonical["location_id"]=pd.to_numeric(canonical["location_id"],errors="raise").astype("int64")
    payload=canonical.to_csv(index=False,float_format="%.17g",lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def load_candidates(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={"candidate_rank","scientific_name","family","genus","selection_hash"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v5 candidate roster missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_CANDIDATES or df.scientific_name.astype(str).nunique()!=EXPECTED_CANDIDATES:
        raise ValueError("v5 all46 support requires exactly 120 unique candidates")
    ranks=sorted(pd.to_numeric(df.candidate_rank,errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v5 candidate ranks must be exactly 1..120")
    df["scientific_name"]=df.scientific_name.astype(str).str.strip()
    return df.sort_values("candidate_rank").reset_index(drop=True)

def validate_contract(path: str|Path)->dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program")!="sdmr-fresh-empirical-v5-preeligibility":
        raise ValueError("wrong v5 preeligibility design program")
    if c.get("status")!="design_frozen_before_v5_candidate_selection":
        raise ValueError("v5 design was not frozen before candidate selection")
    geom=c.get("geometry_eligibility",{})
    if geom.get("whole_program_failure_on_one_geometry_ineligible") is not False:
        raise ValueError("v5 geometry policy changed")
    support=c.get("all46_support_eligibility",{})
    if int(support.get("predictor_count",-1))!=EXPECTED_PREDICTORS:
        raise ValueError("v5 support predictor denominator changed")
    if support.get("persist_numeric_environmental_values") is not False:
        raise ValueError("v5 numeric support persistence became allowed")
    if support.get("answer_check_support_read") is not False:
        raise ValueError("v5 answer-check support became allowed")
    gate=support.get("gate",{})
    if float(gate.get("model_pool_minimum_joint_usable_fraction",-1))!=MODEL_MIN_FRACTION:
        raise ValueError("v5 model-pool support fraction changed")
    if int(gate.get("model_pool_minimum_joint_usable_rows",-1))!=MODEL_MIN_ROWS:
        raise ValueError("v5 model-pool support row minimum changed")
    if int(gate.get("background_denominator_rows",-1))!=BACKGROUND_ROWS_PER_CANDIDATE:
        raise ValueError("v5 background denominator changed")
    if int(gate.get("background_minimum_joint_usable_rows",-1))!=BACKGROUND_MIN_ROWS:
        raise ValueError("v5 background support minimum changed")
    final=c.get("final_selection",{})
    if final.get("eligible_definition")!="geometry_eligible AND all46_support_eligible":
        raise ValueError("v5 joint eligibility definition changed")
    if final.get("rule")!="first_50_jointly_eligible_in_frozen_candidate_order":
        raise ValueError("v5 final selection order changed")
    if int(final.get("final_taxa",-1))!=EXPECTED_FINAL:
        raise ValueError("v5 final taxon denominator changed")
    rules=support.get("structural_decoding_rules",[])
    expected=[("fcf","bio6"),("swe","scd"),("fgd","gsl"),("lgd","gsl"),("gdgfgd5","ngd5"),("gdgfgd10","ngd10")]
    if [(r.get("predictor"),r.get("companion")) for r in rules]!=expected:
        raise ValueError("v5 structural support rule set changed")
    return c

def prepare_support_points(*,candidate_path,model_pool_path,background_path,geometry_path):
    candidates=load_candidates(candidate_path)
    geometry=pd.read_csv(geometry_path)
    required_g={"candidate_rank","scientific_name","source_gate_passed","geometry_eligible","background_points"}
    missing=required_g-set(geometry.columns)
    if missing:
        raise ValueError(f"v5 geometry audit missing columns: {sorted(missing)}")
    if len(geometry)!=EXPECTED_CANDIDATES:
        raise ValueError("v5 geometry audit denominator changed")
    geometry=geometry.sort_values("candidate_rank").reset_index(drop=True)
    if geometry.candidate_rank.astype(int).tolist()!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v5 geometry audit rank order changed")
    if geometry.scientific_name.astype(str).tolist()!=candidates.scientific_name.astype(str).tolist():
        raise ValueError("v5 geometry audit taxon order changed")
    eligible_geometry=geometry.loc[geometry.geometry_eligible.astype(bool)].copy()
    if len(eligible_geometry)<EXPECTED_FINAL:
        raise ValueError("v5 geometry leaves fewer than 50 candidates")
    eligible_taxa=set(eligible_geometry.scientific_name.astype(str))

    model=pd.read_csv(model_pool_path)
    required_m={"scientific_name","occurrence_id","longitude","latitude"}
    missing=required_m-set(model.columns)
    if missing:
        raise ValueError(f"v5 model-pool artifact missing columns: {sorted(missing)}")
    model=model.loc[model.scientific_name.astype(str).isin(eligible_taxa)].copy()
    if set(model.scientific_name.astype(str))!=eligible_taxa:
        raise ValueError("v5 geometry-eligible model-pool coverage changed")
    if model.occurrence_id.astype(str).duplicated().any():
        raise ValueError("v5 model-pool occurrence IDs must be unique")

    bg=pd.read_csv(background_path)
    required_b={"scientific_name","m_km","background_rank","longitude","latitude"}
    missing=required_b-set(bg.columns)
    if missing:
        raise ValueError(f"v5 background artifact missing columns: {sorted(missing)}")
    bg=bg.loc[
        bg.scientific_name.astype(str).isin(eligible_taxa)
        & pd.to_numeric(bg.m_km,errors="raise").astype(int).eq(PRIMARY_M_KM)
    ].copy()
    if set(bg.scientific_name.astype(str))!=eligible_taxa:
        raise ValueError("v5 primary background does not cover exact geometry-eligible taxa")
    per=bg.groupby(bg.scientific_name.astype(str)).size()
    if len(per)!=len(eligible_taxa) or not per.eq(BACKGROUND_ROWS_PER_CANDIDATE).all():
        raise ValueError("v5 support requires exactly 5000 backgrounds for each geometry-eligible taxon")

    model_index=model[["scientific_name","occurrence_id","longitude","latitude"]].copy()
    model_index.insert(1,"point_role","model_pool")
    model_index["point_id"]=model_index.occurrence_id.astype(str)

    bg_index=bg[["scientific_name","background_rank","longitude","latitude"]].copy()
    bg_index.insert(1,"point_role","background_300km")
    bg_index["point_id"]=(bg_index.scientific_name.astype(str)+"|bg300|"+
                          pd.to_numeric(bg_index.background_rank,errors="raise").astype(int).astype(str))
    if bg_index.point_id.duplicated().any():
        raise ValueError("v5 background point IDs must be unique")

    combined=pd.concat([
        model_index[["scientific_name","point_role","point_id","longitude","latitude"]],
        bg_index[["scientific_name","point_role","point_id","longitude","latitude"]],
    ],ignore_index=True)
    combined["longitude"]=pd.to_numeric(combined.longitude,errors="raise").astype(float)
    combined["latitude"]=pd.to_numeric(combined.latitude,errors="raise").astype(float)
    if not np.isfinite(combined[["longitude","latitude"]].to_numpy(float)).all():
        raise ValueError("v5 support coordinates must be finite")
    locations=(combined[["longitude","latitude"]].drop_duplicates()
               .sort_values(["longitude","latitude"],kind="mergesort").reset_index(drop=True))
    locations.insert(0,"location_id",np.arange(len(locations),dtype=np.int64))
    model_index=model_index.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    bg_index=bg_index.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    model_index["location_id"]=pd.to_numeric(model_index.location_id,errors="raise").astype("int64")
    bg_index["location_id"]=pd.to_numeric(bg_index.location_id,errors="raise").astype("int64")
    return candidates,geometry,model_index,bg_index,locations

def extract_chelsa_support(*,predictor,candidate_path,model_pool_path,background_path,geometry_path,process_registry_path,chelsa_manifest_path,output_dir):
    predictor=str(predictor)
    _,_,_,_,locations=prepare_support_points(
        candidate_path=candidate_path,model_pool_path=model_pool_path,
        background_path=background_path,geometry_path=geometry_path
    )
    specs,_=_specs(process_registry_path=process_registry_path,chelsa_manifest_path=chelsa_manifest_path)
    if predictor not in specs or specs[predictor].source=="SoilGrids":
        raise ValueError("v5 CHELSA-support job received non-CHELSA predictor")
    layers=[specs[predictor]]
    if predictor in STRUCTURAL_RULES:
        layers.append(specs[STRUCTURAL_RULES[predictor][0]])
    featured,_=extract_raster_values(
        locations,layers,lon_col="longitude",lat_col="latitude",checksum_local_files=False
    )
    usable=_usable_from_values(predictor=predictor,featured=featured)
    support=pd.DataFrame({"location_id":locations.location_id.astype("int64"),"is_usable":usable.astype(bool)})
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    sp=out/"support.parquet";mp=out/"metadata.json"
    support.to_parquet(sp,index=False)
    meta={
      "program":PROGRAM,"predictor":predictor,"source_family":"CHELSA",
      "location_rows":int(len(support)),"location_index_sha256":_location_sha(locations),
      "support_sha256":_sha256(sp),"usable_rows":int(support.is_usable.sum()),
      "unusable_rows":int((~support.is_usable).sum()),
      "structural_rule_applied":predictor in STRUCTURAL_RULES,
      "persisted_information":"location_id_plus_boolean_usable_bit_only",
      "numeric_environmental_values_persisted":False,
      "answer_check_support_read":False,"model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def extract_soil_support_shard(*,predictor,shard_index,shard_count,candidate_path,model_pool_path,background_path,geometry_path,process_registry_path,chelsa_manifest_path,output_dir):
    predictor=str(predictor)
    if predictor not in SOIL_PREDICTORS:
        raise ValueError("v5 SoilGrids-support predictor outside frozen set")
    if int(shard_count)!=SOIL_SHARD_COUNT:
        raise ValueError("v5 SoilGrids-support shard count changed")
    _,_,_,_,locations=prepare_support_points(
        candidate_path=candidate_path,model_pool_path=model_pool_path,
        background_path=background_path,geometry_path=geometry_path
    )
    start,stop=spatial_shard_bounds(len(locations),int(shard_index),int(shard_count))
    shard=locations.iloc[start:stop].copy().reset_index(drop=True)
    specs,_=_specs(process_registry_path=process_registry_path,chelsa_manifest_path=chelsa_manifest_path)
    spec=specs[predictor]
    if spec.source!="SoilGrids":
        raise ValueError("v5 SoilGrids-support source changed")
    featured,_=extract_raster_values(
        shard,[spec],lon_col="longitude",lat_col="latitude",checksum_local_files=False
    )
    usable=pd.to_numeric(featured[predictor],errors="coerce").notna().to_numpy(bool)
    support=pd.DataFrame({"location_id":shard.location_id.astype("int64"),"is_usable":usable.astype(bool)})
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    sp=out/"support.parquet";mp=out/"metadata.json"
    support.to_parquet(sp,index=False)
    meta={
      "program":PROGRAM,"predictor":predictor,"source_family":"SoilGrids",
      "shard_index":int(shard_index),"shard_count":SOIL_SHARD_COUNT,
      "start_row":int(start),"stop_row":int(stop),"shard_rows":int(len(support)),
      "full_location_rows":int(len(locations)),"location_index_sha256":_location_sha(locations),
      "support_sha256":_sha256(sp),"usable_rows":int(support.is_usable.sum()),
      "unusable_rows":int((~support.is_usable).sum()),
      "persisted_information":"location_id_plus_boolean_usable_bit_only",
      "numeric_environmental_values_persisted":False,
      "answer_check_support_read":False,"model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def assemble_soil_support(*,parts_root,candidate_path,model_pool_path,background_path,geometry_path,output_dir):
    _,_,_,_,locations=prepare_support_points(
        candidate_path=candidate_path,model_pool_path=model_pool_path,
        background_path=background_path,geometry_path=geometry_path
    )
    locsha=_location_sha(locations)
    root=Path(parts_root);metas=sorted(root.rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    expected=len(SOIL_PREDICTORS)*SOIL_SHARD_COUNT
    if len(metadata)!=expected:
        raise RuntimeError(f"expected {expected} v5 SoilGrids support shards; found {len(metadata)}")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for predictor in SOIL_PREDICTORS:
        rows=[m for m in metadata if m.get("predictor")==predictor]
        byidx={int(m["shard_index"]):m for m in rows}
        if set(byidx)!=set(range(SOIL_SHARD_COUNT)):
            raise RuntimeError(f"incomplete v5 SoilGrids support shard set: {predictor}")
        frames=[]
        for idx in range(SOIL_SHARD_COUNT):
            meta=byidx[idx]
            if meta.get("location_index_sha256")!=locsha:
                raise RuntimeError(f"v5 support location fingerprint drift: {predictor}/{idx}")
            if meta.get("numeric_environmental_values_persisted") is not False or meta.get("answer_check_support_read") is not False or meta.get("model_fitting_performed") is not False:
                raise RuntimeError(f"v5 SoilGrids support boundary crossed: {predictor}/{idx}")
            meta_path=next(p for p in metas if json.loads(p.read_text()).get("predictor")==predictor and int(json.loads(p.read_text())["shard_index"])==idx)
            sp=meta_path.with_name("support.parquet")
            if _sha256(sp)!=meta["support_sha256"]:
                raise RuntimeError(f"v5 SoilGrids support shard SHA mismatch: {predictor}/{idx}")
            frames.append(pd.read_parquet(sp))
        full=pd.concat(frames,ignore_index=True).sort_values("location_id",kind="mergesort").reset_index(drop=True)
        if full.location_id.astype("int64").tolist()!=locations.location_id.astype("int64").tolist():
            raise RuntimeError(f"v5 SoilGrids support coverage not exact: {predictor}")
        d=out/predictor;d.mkdir(parents=True,exist_ok=True)
        sp=d/"support.parquet";mp=d/"metadata.json"
        full.to_parquet(sp,index=False)
        final_meta={
          "program":PROGRAM,"predictor":predictor,"source_family":"SoilGrids",
          "location_rows":int(len(full)),"location_index_sha256":locsha,
          "support_sha256":_sha256(sp),"usable_rows":int(full.is_usable.sum()),
          "unusable_rows":int((~full.is_usable).sum()),"spatial_shards":SOIL_SHARD_COUNT,
          "persisted_information":"location_id_plus_boolean_usable_bit_only",
          "numeric_environmental_values_persisted":False,
          "answer_check_support_read":False,"model_fitting_performed":False,
        }
        mp.write_text(json.dumps(final_meta,indent=2,sort_keys=True)+"\n")
    return {
      "program":PROGRAM,"status":"v5_soil_support_assembly_passed",
      "predictor_count":len(SOIL_PREDICTORS),"location_rows":int(len(locations)),
      "numeric_environmental_values_persisted":False,
      "answer_check_support_read":False,"model_fitting_performed":False,
    }

def aggregate_support(*,parts_root,candidate_path,model_pool_path,background_path,geometry_path,contract_path,output_dir):
    validate_contract(contract_path)
    candidates,geometry,model,bg,locations=prepare_support_points(
        candidate_path=candidate_path,model_pool_path=model_pool_path,
        background_path=background_path,geometry_path=geometry_path
    )
    locsha=_location_sha(locations)
    root=Path(parts_root);metas=sorted(root.rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    if len(metadata)!=EXPECTED_PREDICTORS:
        raise RuntimeError(f"v5 support metadata denominator changed: {len(metadata)}")
    by={str(m["predictor"]):m for m in metadata}
    expected_predictors=pd.read_csv(
        "configs/sdmr_fresh_empirical_process_registry_v1.csv"
    )["predictor"].astype(str).tolist()
    if len(by)!=EXPECTED_PREDICTORS or set(by)!=set(expected_predictors):
        raise RuntimeError("v5 support predictor set changed")

    joint=pd.DataFrame({"location_id":locations.location_id.astype("int64")})
    summary=[]
    for predictor in expected_predictors:
        meta=by[predictor]
        if meta.get("location_index_sha256")!=locsha or int(meta.get("location_rows",-1))!=len(locations):
            raise RuntimeError(f"v5 support location fingerprint changed: {predictor}")
        if meta.get("numeric_environmental_values_persisted") is not False or meta.get("answer_check_support_read") is not False or meta.get("model_fitting_performed") is not False:
            raise RuntimeError(f"v5 support boundary crossed: {predictor}")
        meta_path=next(p for p in metas if json.loads(p.read_text()).get("predictor")==predictor)
        sp=meta_path.with_name("support.parquet")
        if _sha256(sp)!=meta["support_sha256"]:
            raise RuntimeError(f"v5 support SHA mismatch: {predictor}")
        support=pd.read_parquet(sp).sort_values("location_id",kind="mergesort").reset_index(drop=True)
        if list(support.columns)!=["location_id","is_usable"]:
            raise RuntimeError(f"v5 support columns changed: {predictor}")
        if support.location_id.astype("int64").tolist()!=locations.location_id.astype("int64").tolist():
            raise RuntimeError(f"v5 support row coverage changed: {predictor}")
        joint[predictor]=support.is_usable.astype(bool).to_numpy()
        summary.append({
          "predictor":predictor,
          "usable_rows":int(support.is_usable.sum()),
          "unusable_rows":int((~support.is_usable).sum()),
        })
    joint["joint_usable"]=joint[expected_predictors].all(axis=1)
    model2=model.merge(joint[["location_id","joint_usable"]],on="location_id",how="left",validate="many_to_one")
    bg2=bg.merge(joint[["location_id","joint_usable"]],on="location_id",how="left",validate="many_to_one")
    geom_map=geometry.set_index(geometry.scientific_name.astype(str))

    rows=[]
    for cand in candidates.itertuples(index=False):
        taxon=str(cand.scientific_name)
        grow=geometry.loc[geometry.scientific_name.astype(str).eq(taxon)].iloc[0]
        geom_ok=bool(grow.geometry_eligible)
        if not geom_ok:
            rows.append({
              "candidate_rank":int(cand.candidate_rank),
              "scientific_name":taxon,
              "geometry_eligible":False,
              "model_pool_rows":int(grow.model_pool_occurrences),
              "model_pool_joint_usable_rows":0,
              "model_pool_joint_usable_fraction":0.0,
              "background_300km_rows":0,
              "background_300km_joint_usable_rows":0,
              "all46_support_eligible":False,
              "jointly_eligible":False,
              "answer_check_support_read":False,
              "numeric_environmental_values_persisted":False,
            })
            continue
        m=model2.loc[model2.scientific_name.astype(str).eq(taxon)]
        b=bg2.loc[bg2.scientific_name.astype(str).eq(taxon)]
        m_usable=int(m.joint_usable.sum());b_usable=int(b.joint_usable.sum())
        m_fraction=float(m_usable/len(m)) if len(m) else 0.0
        support_ok=(
          m_fraction>=MODEL_MIN_FRACTION and m_usable>=MODEL_MIN_ROWS
          and len(b)==BACKGROUND_ROWS_PER_CANDIDATE and b_usable>=BACKGROUND_MIN_ROWS
        )
        rows.append({
          "candidate_rank":int(cand.candidate_rank),
          "scientific_name":taxon,
          "geometry_eligible":True,
          "model_pool_rows":int(len(m)),
          "model_pool_joint_usable_rows":m_usable,
          "model_pool_joint_usable_fraction":m_fraction,
          "background_300km_rows":int(len(b)),
          "background_300km_joint_usable_rows":b_usable,
          "all46_support_eligible":bool(support_ok),
          "jointly_eligible":bool(support_ok),
          "answer_check_support_read":False,
          "numeric_environmental_values_persisted":False,
        })
    audit=pd.DataFrame(rows).sort_values("candidate_rank").reset_index(drop=True)
    if len(audit)!=EXPECTED_CANDIDATES:
        raise RuntimeError("v5 eligibility audit denominator changed")
    eligible=audit.loc[audit.jointly_eligible].scientific_name.astype(str).tolist()
    ordered=candidates.loc[candidates.scientific_name.astype(str).isin(set(eligible))].copy()
    count=int(len(ordered))

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    ap=out/"candidate_joint_eligibility_v5.csv"
    pp=out/"predictor_support_summary_v5.csv"
    audit.to_csv(ap,index=False);pd.DataFrame(summary).to_csv(pp,index=False)
    result={
      "program":"sdmr-fresh-empirical-v5-preeligibility",
      "candidate_count":EXPECTED_CANDIDATES,
      "geometry_eligible_count":int(audit.geometry_eligible.sum()),
      "all46_support_eligible_count":int(audit.all46_support_eligible.sum()),
      "jointly_eligible_count":count,
      "final_selected_count":0,
      "status":"terminal_unavailable_before_final50_freeze",
      "eligibility_audit_sha256":_sha256(ap),
      "predictor_support_summary_sha256":_sha256(pp),
      "numeric_environmental_values_persisted":False,
      "answer_check_support_read":False,"model_fitting_performed":False,
      "taxon_replacement_performed":False,"predictor_deletion_performed":False,
      "geometry_threshold_relaxation_performed":False,"support_threshold_relaxation_performed":False,
    }
    if count>=EXPECTED_FINAL:
        final=ordered.head(EXPECTED_FINAL).copy().reset_index(drop=True)
        final.insert(0,"selection_rank",range(1,EXPECTED_FINAL+1))
        final=final.merge(audit,on=["candidate_rank","scientific_name"],how="left",validate="one_to_one")
        fp=out/"selected_fresh_taxa_v5.csv"
        final.to_csv(fp,index=False)
        result.update({
          "status":"final50_frozen_after_geometry_plus_all46_preeligibility",
          "final_selected_count":EXPECTED_FINAL,
          "selected_manifest_sha256":_sha256(fp),
        })
    (out/"preeligibility_selection_result_v5.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n"
    )
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    common=[
      ("--candidates",{"required":True}),("--model-pool",{"required":True}),
      ("--background",{"required":True}),("--geometry",{"required":True}),
    ]
    q=sub.add_parser("chelsa")
    q.add_argument("--predictor",required=True)
    for name,kwargs in common:q.add_argument(name,**kwargs)
    q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("soil-shard")
    q.add_argument("--predictor",required=True);q.add_argument("--shard-index",type=int,required=True);q.add_argument("--shard-count",type=int,default=SOIL_SHARD_COUNT)
    for name,kwargs in common:q.add_argument(name,**kwargs)
    q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("soil-assemble")
    q.add_argument("--parts-root",required=True)
    for name,kwargs in common:q.add_argument(name,**kwargs)
    q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate")
    q.add_argument("--parts-root",required=True)
    for name,kwargs in common:q.add_argument(name,**kwargs)
    q.add_argument("--contract",required=True);q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    base=dict(candidate_path=a.candidates,model_pool_path=a.model_pool,background_path=a.background,geometry_path=a.geometry)
    if a.command=="chelsa":
        result=extract_chelsa_support(predictor=a.predictor,process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir,**base)
    elif a.command=="soil-shard":
        result=extract_soil_support_shard(predictor=a.predictor,shard_index=a.shard_index,shard_count=a.shard_count,process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir,**base)
    elif a.command=="soil-assemble":
        result=assemble_soil_support(parts_root=a.parts_root,output_dir=a.output_dir,**base)
    else:
        result=aggregate_support(parts_root=a.parts_root,contract_path=a.contract,output_dir=a.output_dir,**base)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
