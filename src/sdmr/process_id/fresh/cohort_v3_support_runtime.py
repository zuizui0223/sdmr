"""Finite/missing SoilGrids support eligibility for fresh empirical v3.

This runtime is intentionally pre-outcome. It reads only model-pool and
background coordinates, reduces each SoilGrids sample immediately to a boolean
finite/missing bit, never persists numeric soil values, and never reads
answer-check coordinates or features.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.data.raster import RasterLayerSpec, _raster_env, _sample_band_blockwise
from sdmr.process_id.fresh.cohort_v3_soil_support import (
    EXPECTED_CANDIDATES,
    EXPECTED_FINAL,
    EXPECTED_SOIL,
    select_final,
    validate_contract,
)

PROGRAM="sdmr-fresh-empirical-v3-soil-support-runtime"
SUPPORT_SHARDS=32
MODEL_MIN_FRACTION=0.80
MODEL_MIN_ROWS=50
BACKGROUND_ROWS=5000
BACKGROUND_MIN_ROWS=4000
SOIL_SCALE={
    "divide_by_10":0.1,
    "divide_by_100":0.01,
}

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _location_sha(frame: pd.DataFrame)->str:
    required=["location_id","longitude","latitude"]
    if list(frame.columns)!=required:
        raise ValueError("v3 support location columns changed")
    payload=frame.to_csv(index=False,float_format="%.17g",lineterminator="\n").encode()
    return hashlib.sha256(payload).hexdigest()

def spatial_shard_bounds(n_rows:int, shard_index:int, shard_count:int)->tuple[int,int]:
    if n_rows<1 or shard_count<1 or not 0<=shard_index<shard_count:
        raise ValueError("invalid v3 support shard bounds")
    start=(n_rows*shard_index)//shard_count
    stop=(n_rows*(shard_index+1))//shard_count
    if stop<=start:
        raise ValueError("empty v3 support shard")
    return start,stop

def load_candidate_roster(path: str|Path)->pd.DataFrame:
    c=pd.read_csv(path)
    required={"candidate_rank","scientific_name","family","genus","selection_hash"}
    if required-set(c.columns):
        raise ValueError("v3 support candidate roster columns changed")
    if len(c)!=EXPECTED_CANDIDATES or c.scientific_name.astype(str).nunique()!=EXPECTED_CANDIDATES:
        raise ValueError("v3 support requires exactly 80 candidates")
    ranks=sorted(pd.to_numeric(c.candidate_rank,errors="raise").astype(int))
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v3 candidate ranks must be 1..80")
    c["scientific_name"]=c.scientific_name.astype(str).str.strip()
    return c.sort_values("candidate_rank").reset_index(drop=True)

def prepare_support_points(*,candidate_path,model_pool_path,background_path):
    candidates=load_candidate_roster(candidate_path)
    taxa=set(candidates.scientific_name)

    model=pd.read_csv(model_pool_path)
    req_m={"scientific_name","occurrence_id","longitude","latitude"}
    if req_m-set(model.columns):
        raise ValueError("v3 model-pool support input columns changed")
    if set(model.scientific_name.astype(str))!=taxa:
        raise ValueError("v3 model-pool does not cover the exact candidate80")
    if model.occurrence_id.astype(str).duplicated().any():
        raise ValueError("v3 model-pool occurrence IDs must be unique")

    bg=pd.read_csv(background_path)
    req_b={"scientific_name","background_rank","longitude","latitude"}
    if req_b-set(bg.columns):
        raise ValueError("v3 background support input columns changed")
    if set(bg.scientific_name.astype(str))!=taxa:
        raise ValueError("v3 background does not cover the exact candidate80")
    per=bg.groupby(bg.scientific_name.astype(str)).size()
    if len(per)!=EXPECTED_CANDIDATES or not per.eq(BACKGROUND_ROWS).all():
        raise ValueError("v3 support requires exactly 5000 background rows per candidate")

    model_index=model[["scientific_name","occurrence_id","longitude","latitude"]].copy()
    model_index.insert(1,"point_role","model_pool")
    model_index["point_id"]=model_index.occurrence_id.astype(str)
    bg_index=bg[["scientific_name","background_rank","longitude","latitude"]].copy()
    bg_index.insert(1,"point_role","background_300km")
    bg_index["point_id"]=(bg_index.scientific_name.astype(str)+"|bg300|"+
                          pd.to_numeric(bg_index.background_rank,errors="raise").astype(int).astype(str))
    if bg_index.point_id.duplicated().any():
        raise ValueError("v3 background point IDs must be unique")

    combined=pd.concat([
        model_index[["scientific_name","point_role","point_id","longitude","latitude"]],
        bg_index[["scientific_name","point_role","point_id","longitude","latitude"]],
    ],ignore_index=True)
    combined["longitude"]=pd.to_numeric(combined.longitude,errors="raise").astype(float)
    combined["latitude"]=pd.to_numeric(combined.latitude,errors="raise").astype(float)
    if not np.isfinite(combined[["longitude","latitude"]].to_numpy(float)).all():
        raise ValueError("v3 support coordinates must be finite")
    locations=(combined[["longitude","latitude"]].drop_duplicates()
               .sort_values(["longitude","latitude"],kind="mergesort").reset_index(drop=True))
    locations.insert(0,"location_id",np.arange(len(locations),dtype=np.int64))
    model_index=model_index.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    bg_index=bg_index.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    model_index["location_id"]=model_index.location_id.astype("int64")
    bg_index["location_id"]=bg_index.location_id.astype("int64")
    return candidates,model_index,bg_index,locations

def soil_specs(process_registry_path: str|Path)->dict[str,RasterLayerSpec]:
    r=pd.read_csv(process_registry_path)
    rows=r.loc[r.predictor.astype(str).isin(EXPECTED_SOIL)].copy()
    if len(rows)!=len(EXPECTED_SOIL) or set(rows.predictor.astype(str))!=set(EXPECTED_SOIL):
        raise ValueError("v3 support SoilGrids registry changed")
    out={}
    for row in rows.itertuples(index=False):
        if str(row.source_family)!="SoilGrids":
            raise ValueError(f"v3 support predictor is not SoilGrids: {row.predictor}")
        transform=str(row.transform)
        if transform not in SOIL_SCALE:
            raise ValueError(f"unsupported SoilGrids transform: {transform}")
        uri=str(row.source_locator)
        if not uri.startswith("https://files.isric.org/soilgrids/latest/data/") or not uri.endswith(".vrt"):
            raise ValueError(f"SoilGrids locator drifted: {uri}")
        out[str(row.predictor)]=RasterLayerSpec(
            predictor=str(row.predictor),uri=uri,source="SoilGrids",
            version=str(row.source_version),scale=SOIL_SCALE[transform],offset=0.0
        )
    return out

def _finite_mask_for_points(points: pd.DataFrame, spec: RasterLayerSpec)->np.ndarray:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform
    lon=pd.to_numeric(points.longitude,errors="raise").to_numpy(float)
    lat=pd.to_numeric(points.latitude,errors="raise").to_numpy(float)
    with _raster_env(rasterio,spec.uri):
        with rasterio.open(spec.uri) as src:
            x=lon; y=lat
            if src.crs!=CRS.from_epsg(4326):
                xx,yy=transform(CRS.from_epsg(4326),src.crs,x.tolist(),y.tolist())
                x=np.asarray(xx,float);y=np.asarray(yy,float)
            sampled=_sample_band_blockwise(src,x,y)
            finite=np.isfinite(sampled)
            if src.nodata is not None:
                finite &= ~np.isclose(sampled,float(src.nodata),equal_nan=True)
    return finite.astype(bool)

def extract_support_shard(*,predictor,shard_index,shard_count,candidate_path,model_pool_path,background_path,process_registry_path,output_dir):
    if predictor not in EXPECTED_SOIL:
        raise ValueError("predictor outside frozen four-layer SoilGrids support set")
    if int(shard_count)!=SUPPORT_SHARDS:
        raise ValueError(f"v3 SoilGrids support shard_count must remain {SUPPORT_SHARDS}")
    _,_,_,locations=prepare_support_points(
        candidate_path=candidate_path,model_pool_path=model_pool_path,background_path=background_path
    )
    start,stop=spatial_shard_bounds(len(locations),int(shard_index),int(shard_count))
    shard=locations.iloc[start:stop].copy().reset_index(drop=True)
    spec=soil_specs(process_registry_path)[predictor]
    finite=_finite_mask_for_points(shard,spec)
    support=pd.DataFrame({"location_id":shard.location_id.astype("int64"),
                          "is_finite":finite.astype(bool)})
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    support_path=out/"support.parquet";meta_path=out/"metadata.json"
    support.to_parquet(support_path,index=False)
    meta={
      "program":PROGRAM,"predictor":predictor,"shard_index":int(shard_index),
      "shard_count":SUPPORT_SHARDS,"start_row":int(start),"stop_row":int(stop),
      "shard_rows":int(len(support)),"full_location_rows":int(len(locations)),
      "location_index_sha256":_location_sha(locations),
      "support_sha256":_sha256(support_path),
      "finite_rows":int(support.is_finite.sum()),"missing_rows":int((~support.is_finite).sum()),
      "persisted_information":"finite_or_missing_bit_only",
      "numeric_soil_values_persisted":False,"answer_check_support_read":False,
      "model_fitting_performed":False,
    }
    meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def assemble_support(*,parts_root,candidate_path,model_pool_path,background_path,contract_path,output_dir):
    contract=validate_contract(contract_path)
    candidates,model,bg,locations=prepare_support_points(
        candidate_path=candidate_path,model_pool_path=model_pool_path,background_path=background_path
    )
    loc_sha=_location_sha(locations)
    root=Path(parts_root); metas=sorted(root.rglob("metadata.json"))
    expected=len(EXPECTED_SOIL)*SUPPORT_SHARDS
    if len(metas)!=expected:
        raise RuntimeError(f"expected {expected} v3 support shard metadata files; found {len(metas)}")
    metadata=[json.loads(p.read_text()) for p in metas]
    joint=pd.DataFrame({"location_id":locations.location_id.astype("int64")})
    for predictor in EXPECTED_SOIL:
        rows=[m for m in metadata if m.get("predictor")==predictor]
        by_idx={int(m["shard_index"]):m for m in rows}
        if set(by_idx)!=set(range(SUPPORT_SHARDS)):
            raise RuntimeError(f"incomplete v3 SoilGrids support shard set: {predictor}")
        frames=[]
        for idx in range(SUPPORT_SHARDS):
            meta=by_idx[idx]
            if meta.get("location_index_sha256")!=loc_sha:
                raise RuntimeError(f"v3 support location fingerprint drift: {predictor}/{idx}")
            if meta.get("numeric_soil_values_persisted") is not False or meta.get("answer_check_support_read") is not False:
                raise RuntimeError(f"v3 support information boundary crossed: {predictor}/{idx}")
            mp=next(p for p in metas if json.loads(p.read_text()).get("predictor")==predictor and int(json.loads(p.read_text())["shard_index"])==idx)
            sp=mp.with_name("support.parquet")
            if _sha256(sp)!=meta["support_sha256"]:
                raise RuntimeError(f"v3 support shard SHA mismatch: {predictor}/{idx}")
            f=pd.read_parquet(sp)
            if list(f.columns)!=["location_id","is_finite"]:
                raise RuntimeError(f"v3 support shard columns changed: {predictor}/{idx}")
            frames.append(f)
        full=pd.concat(frames,ignore_index=True).sort_values("location_id",kind="mergesort").reset_index(drop=True)
        if full.location_id.astype("int64").tolist()!=locations.location_id.astype("int64").tolist():
            raise RuntimeError(f"v3 support shard coverage not exact: {predictor}")
        joint[predictor]=full.is_finite.astype(bool).to_numpy()
    joint["joint_finite"]=joint[list(EXPECTED_SOIL)].all(axis=1)

    model2=model.merge(joint[["location_id","joint_finite"]],on="location_id",validate="many_to_one")
    bg2=bg.merge(joint[["location_id","joint_finite"]],on="location_id",validate="many_to_one")
    rows=[]
    for taxon in candidates.scientific_name.astype(str):
        m=model2.loc[model2.scientific_name.astype(str).eq(taxon)]
        b=bg2.loc[bg2.scientific_name.astype(str).eq(taxon)]
        rows.append({
          "scientific_name":taxon,
          "model_pool_rows":int(len(m)),
          "model_pool_joint_finite_rows":int(m.joint_finite.sum()),
          "model_pool_joint_finite_fraction":float(m.joint_finite.mean()) if len(m) else 0.0,
          "background_300km_rows":int(len(b)),
          "background_300km_joint_finite_rows":int(b.joint_finite.sum()),
          "answer_check_support_read":False,
          "numeric_soil_values_persisted":False,
        })
    support=pd.DataFrame(rows)
    if len(support)!=EXPECTED_CANDIDATES:
        raise RuntimeError("v3 support audit denominator changed")

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    support_path=out/"candidate_soil_support_bits_v3.csv"
    support.to_csv(support_path,index=False)
    audit,final,result=select_final(candidate_path,support_path,contract_path)
    audit_path=out/"candidate_soil_support_audit_v3.csv"
    audit.to_csv(audit_path,index=False)
    if len(final):
        final_path=out/"selected_fresh_taxa_v3.csv"
        final.to_csv(final_path,index=False)
        result["selected_manifest_sha256"]=_sha256(final_path)
    result.update({
      "support_audit_sha256":_sha256(audit_path),
      "support_bit_summary_sha256":_sha256(support_path),
      "support_shards_per_predictor":SUPPORT_SHARDS,
      "numeric_soil_values_persisted":False,
      "answer_check_support_read":False,
      "model_fitting_performed":False,
    })
    (out/"soil_support_selection_result_v3.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("shard")
    q.add_argument("--predictor",required=True);q.add_argument("--shard-index",type=int,required=True);q.add_argument("--shard-count",type=int,default=SUPPORT_SHARDS)
    q.add_argument("--candidates",required=True);q.add_argument("--model-pool",required=True);q.add_argument("--background",required=True);q.add_argument("--process-registry",required=True);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate")
    q.add_argument("--parts-root",required=True);q.add_argument("--candidates",required=True);q.add_argument("--model-pool",required=True);q.add_argument("--background",required=True);q.add_argument("--contract",required=True);q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    if a.command=="shard":
        result=extract_support_shard(predictor=a.predictor,shard_index=a.shard_index,shard_count=a.shard_count,candidate_path=a.candidates,model_pool_path=a.model_pool,background_path=a.background,process_registry_path=a.process_registry,output_dir=a.output_dir)
    else:
        result=assemble_support(parts_root=a.parts_root,candidate_path=a.candidates,model_pool_path=a.model_pool,background_path=a.background,contract_path=a.contract,output_dir=a.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
