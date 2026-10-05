"""Per-candidate 300-km geometry eligibility and deterministic background for fresh empirical v5."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list
from sdmr.process_id.fresh.cohort_v3_background import _combine_target, _xyz, _chord

PROGRAM="sdmr-fresh-empirical-v5-background"
SNAPSHOT_DATE="2026-08-01"
SNAPSHOT_DOI="10.15468/dl.fs3btq"
SNAPSHOT_REGION="us-east-1"
YEAR_MIN=2010
YEAR_MAX=2025
CELL_DEGREES=0.05
EXPECTED_CANDIDATES=120
EXPECTED_CHUNKS=32
PRIMARY_M_KM=300
BACKGROUND_POINTS=5000
BACKGROUND_SEED="sdmr-fresh-v5-background-v1"

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_candidates(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={"candidate_rank","scientific_name","family","genus","selection_hash"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v5 candidate roster missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_CANDIDATES or df.scientific_name.astype(str).nunique()!=EXPECTED_CANDIDATES:
        raise ValueError("v5 background requires exactly 120 candidate taxa")
    ranks=sorted(pd.to_numeric(df.candidate_rank,errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v5 candidate ranks must be exactly 1..120")
    df["scientific_name"]=df.scientific_name.astype(str).str.strip()
    return df.sort_values("candidate_rank").reset_index(drop=True)

def _target_where_sql(excluded_names)->str:
    names=sorted({str(x).strip() for x in excluded_names if str(x).strip()})
    if len(names)!=EXPECTED_CANDIDATES:
        raise ValueError("v5 target footprint must exclude exact candidate120")
    excluded=",".join(_sql_literal(x) for x in names)
    return " AND ".join([
        "phylum = 'Tracheophyta'",
        "species IS NOT NULL",
        "trim(species) <> ''",
        f"species NOT IN ({excluded})",
        f"year BETWEEN {YEAR_MIN} AND {YEAR_MAX}",
        "(occurrencestatus IS NULL OR upper(occurrencestatus) = 'PRESENT')",
        "(basisofrecord IS NULL OR upper(basisofrecord) <> 'FOSSIL_SPECIMEN')",
        "(coordinateuncertaintyinmeters IS NULL OR coordinateuncertaintyinmeters <= 10000)",
        "gbifid IS NOT NULL",
        "decimallatitude IS NOT NULL",
        "decimallongitude IS NOT NULL",
        "decimallatitude BETWEEN -90 AND 90",
        "decimallongitude BETWEEN -180 AND 180",
        "NOT (decimallatitude = 0 AND decimallongitude = 0)",
    ])

def run_chunk(*,candidate_path,chunk_index,chunk_count,output_dir):
    candidates=load_candidates(candidate_path)
    if int(chunk_count)!=EXPECTED_CHUNKS or not 0<=int(chunk_index)<EXPECTED_CHUNKS:
        raise ValueError("v5 background chunk denominator changed")
    import duckdb
    con=duckdb.connect()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    partial=out/f"partial_{int(chunk_index):02d}.parquet"
    meta_path=out/f"metadata_{int(chunk_index):02d}.json"
    try:
        _configure_duckdb_cloud(con,cloud_provider="aws",region=SNAPSHOT_REGION)
        files=_list_snapshot_shards(con,SNAPSHOT_DATE,SNAPSHOT_REGION)
        shards=_chunk_files(files,int(chunk_index),int(chunk_count))
        if not shards:
            raise RuntimeError("empty v5 target-footprint shard chunk")
        source=f"read_parquet({_sql_list(shards)}, union_by_name=true)"
        query=f"""
        WITH filtered AS (
          SELECT CAST(gbifid AS VARCHAR) AS gbifid,
            decimallongitude AS longitude, decimallatitude AS latitude,
            CAST(FLOOR((decimallongitude + 180.0) / {CELL_DEGREES}) AS BIGINT) AS gx,
            CAST(FLOOR((decimallatitude + 90.0) / {CELL_DEGREES}) AS BIGINT) AS gy
          FROM {source}
          WHERE {_target_where_sql(candidates.scientific_name)}
        )
        SELECT gx,gy,
          ARG_MIN(gbifid,gbifid) AS gbifid,
          ARG_MIN(longitude,gbifid) AS longitude,
          ARG_MIN(latitude,gbifid) AS latitude
        FROM filtered
        GROUP BY gx,gy
        ORDER BY gx,gy
        """
        con.execute(
            f"COPY ({query}) TO {_sql_literal(str(partial.resolve()))} "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        partial_rows=int(con.execute(
            f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(partial.resolve()))})"
        ).fetchone()[0])
    finally:
        con.close()
    meta={
      "program":PROGRAM,"snapshot_date":SNAPSHOT_DATE,"snapshot_doi":SNAPSHOT_DOI,
      "chunk_index":int(chunk_index),"chunk_count":EXPECTED_CHUNKS,
      "snapshot_shard_count":len(files),"chunk_shard_count":len(shards),
      "candidate_roster_sha256":_sha256(candidate_path),
      "partial_rows":partial_rows,"partial_sha256":_sha256(partial),
      "environmental_values_read":False,"eligibility_bits_opened":False,
      "answer_check_coordinates_read":False,"answer_check_features_read":False,
      "model_fitting_performed":False,
    }
    meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def _hash(taxon,gbifid):
    return hashlib.sha256(
        f"{BACKGROUND_SEED}\n{taxon}\n{gbifid}\n".encode()
    ).hexdigest()

def build_geometry_and_backgrounds(*,target_footprint,model_pool,source_gate,candidates):
    from scipy.spatial import cKDTree
    target=target_footprint.copy().reset_index(drop=True)
    if {"gx","gy","gbifid","longitude","latitude"}-set(target.columns):
        raise ValueError("v5 target footprint columns changed")
    if {"scientific_name","occurrence_id","longitude","latitude"}-set(model_pool.columns):
        raise ValueError("v5 model-pool columns changed")
    if {"scientific_name","source_gate_passed"}-set(source_gate.columns):
        raise ValueError("v5 source-gate summary columns changed")
    if target[["gx","gy"]].duplicated().any():
        raise ValueError("v5 target footprint cells must be unique")
    if len(candidates)!=EXPECTED_CANDIDATES:
        raise ValueError("v5 geometry requires exact candidate120")

    txyz=_xyz(target.longitude,target.latitude)
    limit=_chord(PRIMARY_M_KM)
    source_map=dict(zip(
        source_gate.scientific_name.astype(str),
        source_gate.source_gate_passed.astype(bool),
    ))
    frames=[];rows=[]
    for row in candidates.itertuples(index=False):
        taxon=str(row.scientific_name)
        source_ok=bool(source_map.get(taxon,False))
        focal=model_pool.loc[model_pool.scientific_name.astype(str).eq(taxon)]
        if not source_ok:
            rows.append({
              "candidate_rank":int(row.candidate_rank),
              "scientific_name":taxon,
              "source_gate_passed":False,
              "model_pool_occurrences":0,
              "candidate_target_cells":0,
              "geometry_eligible":False,
              "background_points":0,
              "geometry_failure_reason":"source_gate_failed",
            })
            continue
        if focal.empty:
            raise RuntimeError(f"v5 source-gate-passed taxon lacks model-pool coordinates: {taxon}")
        tree=cKDTree(_xyz(focal.longitude,focal.latitude))
        d,_=tree.query(txyz,k=1,distance_upper_bound=limit,workers=-1)
        cand=target.loc[np.isfinite(d)&(d<=limit+1e-15)].copy()
        n=int(len(cand))
        eligible=bool(n>=BACKGROUND_POINTS)
        if eligible:
            cand["selection_hash"]=[_hash(taxon,g) for g in cand.gbifid.astype(str)]
            chosen=(cand.sort_values(["selection_hash","gbifid","gx","gy"],kind="mergesort")
                    .head(BACKGROUND_POINTS).copy())
            chosen.insert(0,"background_rank",range(1,BACKGROUND_POINTS+1))
            chosen.insert(0,"m_km",PRIMARY_M_KM)
            chosen.insert(0,"scientific_name",taxon)
            frames.append(chosen[[
                "scientific_name","m_km","background_rank","gbifid",
                "longitude","latitude","gx","gy","selection_hash"
            ]])
        rows.append({
          "candidate_rank":int(row.candidate_rank),
          "scientific_name":taxon,
          "source_gate_passed":True,
          "model_pool_occurrences":int(len(focal)),
          "candidate_target_cells":n,
          "geometry_eligible":eligible,
          "background_points":BACKGROUND_POINTS if eligible else 0,
          "geometry_failure_reason":"" if eligible else "fewer_than_5000_target_group_cells_within_300km",
        })
    backgrounds=(pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=[
        "scientific_name","m_km","background_rank","gbifid","longitude","latitude","gx","gy","selection_hash"
    ]))
    audit=pd.DataFrame(rows).sort_values("candidate_rank").reset_index(drop=True)
    return backgrounds,audit

def run_aggregate(*,candidate_path,model_pool_path,source_gate_path,parts_root,output_dir):
    candidates=load_candidates(candidate_path)
    model=pd.read_csv(model_pool_path)
    source_gate=pd.read_csv(source_gate_path)
    if len(source_gate)!=EXPECTED_CANDIDATES:
        raise ValueError("v5 source-gate summary denominator changed")
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata_*.json"))
    partials=sorted(root.rglob("partial_*.parquet"))
    if len(metas)!=EXPECTED_CHUNKS or len(partials)!=EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected 32 v5 target chunks; metadata={len(metas)} partials={len(partials)}"
        )
    metadata=[json.loads(p.read_text()) for p in metas]
    by_idx={int(x["chunk_index"]):x for x in metadata}
    part_idx={int(p.stem.rsplit("_",1)[1]):p for p in partials}
    if set(by_idx)!=set(range(EXPECTED_CHUNKS)) or set(part_idx)!=set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("v5 target chunk index set incomplete")
    for i in range(EXPECTED_CHUNKS):
        if _sha256(part_idx[i])!=by_idx[i]["partial_sha256"]:
            raise RuntimeError(f"v5 target partial SHA mismatch: {i}")
    if len({x["candidate_roster_sha256"] for x in metadata})!=1 or metadata[0]["candidate_roster_sha256"]!=_sha256(candidate_path):
        raise RuntimeError("v5 target candidate-roster fingerprint changed")
    for key in (
        "environmental_values_read","eligibility_bits_opened","answer_check_coordinates_read",
        "answer_check_features_read","model_fitting_performed",
    ):
        if any(x.get(key) is not False for x in metadata):
            raise RuntimeError(f"v5 geometry information boundary crossed: {key}")

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    footprint=out/"target_footprint_v5.parquet"
    rows=_combine_target([part_idx[i] for i in range(EXPECTED_CHUNKS)],footprint)
    target=pd.read_parquet(footprint)
    bg,audit=build_geometry_and_backgrounds(
        target_footprint=target,
        model_pool=model,
        source_gate=source_gate,
        candidates=candidates,
    )
    eligible=int(audit.geometry_eligible.sum())
    status=(
      "candidate120_geometry_frozen"
      if eligible>=50 else
      "terminal_unavailable_fewer_than_50_geometry_eligible"
    )
    bp=out/"background_points_v5.csv"
    ap=out/"geometry_eligibility_v5.csv"
    bg.to_csv(bp,index=False);audit.to_csv(ap,index=False)
    result={
      "program":PROGRAM,"status":status,
      "candidate_count":EXPECTED_CANDIDATES,
      "source_gate_eligible_count":int(audit.source_gate_passed.sum()),
      "geometry_eligible_count":eligible,
      "geometry_ineligible_count":int((~audit.geometry_eligible).sum()),
      "target_footprint_rows":rows,
      "primary_m_km":PRIMARY_M_KM,
      "background_rows":int(len(bg)),
      "minimum_candidate_target_cells":int(audit.loc[audit.source_gate_passed,"candidate_target_cells"].min())
        if audit.source_gate_passed.any() else 0,
      "background_points_sha256":_sha256(bp),
      "geometry_eligibility_sha256":_sha256(ap),
      "target_footprint_sha256":_sha256(footprint),
      "environmental_values_read":False,"eligibility_bits_opened":False,
      "answer_check_coordinates_read":False,"answer_check_features_read":False,
      "model_fitting_performed":False,
      "taxon_replacement_performed":False,"geometry_threshold_relaxation_performed":False,
      "next_gate":"evaluate_all46_usable_support_bits_for_geometry_eligible_candidates"
        if eligible>=50 else "terminal_unavailable_no_replacement_no_relaxation",
    }
    (out/"background_result_v5.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n"
    )
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("chunk")
    q.add_argument("--candidates",required=True);q.add_argument("--chunk-index",type=int,required=True)
    q.add_argument("--chunk-count",type=int,default=32);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate")
    q.add_argument("--candidates",required=True);q.add_argument("--model-pool",required=True)
    q.add_argument("--source-gate",required=True);q.add_argument("--parts-root",required=True)
    q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    result=(
      run_chunk(candidate_path=a.candidates,chunk_index=a.chunk_index,chunk_count=a.chunk_count,output_dir=a.output_dir)
      if a.command=="chunk"
      else run_aggregate(candidate_path=a.candidates,model_pool_path=a.model_pool,source_gate_path=a.source_gate,parts_root=a.parts_root,output_dir=a.output_dir)
    )
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
