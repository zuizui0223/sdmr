"""Coordinate-only occurrence source gate and outer split for fresh empirical v5 candidate120."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list
from sdmr.process_id.fresh.cohort_v3_occurrence import (
    MIN_RAW_OCCURRENCES, MIN_THINNED_CELLS, _combine_cells, _freeze_taxon,
)

PROGRAM="sdmr-fresh-empirical-v5-occurrence-split"
SNAPSHOT_DATE="2026-08-01"
SNAPSHOT_DOI="10.15468/dl.fs3btq"
SNAPSHOT_REGION="us-east-1"
YEAR_MIN=2010
YEAR_MAX=2025
CELL_DEGREES=0.05
EXPECTED_CANDIDATES=120
EXPECTED_CHUNKS=32

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_candidates(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={"candidate_rank","scientific_name","family","genus","selection_hash"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v5 candidate roster missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_CANDIDATES or df["scientific_name"].astype(str).nunique()!=EXPECTED_CANDIDATES:
        raise ValueError("v5 occurrence split requires exactly 120 candidates")
    ranks=sorted(pd.to_numeric(df["candidate_rank"],errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v5 candidate ranks must be exactly 1..120")
    df["scientific_name"]=df["scientific_name"].astype(str).str.strip()
    return df.sort_values("candidate_rank").reset_index(drop=True)

def _species_sql(names)->str:
    vals=sorted({str(x).strip() for x in names if str(x).strip()})
    if len(vals)!=EXPECTED_CANDIDATES:
        raise ValueError("v5 occurrence scan requires exactly 120 candidate names")
    return ",".join(_sql_literal(x) for x in vals)

def _where_sql(names)->str:
    return " AND ".join([
        f"species IN ({_species_sql(names)})",
        "upper(taxonrank) = 'SPECIES'",
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
        raise ValueError("v5 occurrence chunk denominator changed")
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
            raise RuntimeError("empty v5 occurrence shard chunk")
        source=f"read_parquet({_sql_list(shards)}, union_by_name=true)"
        query=f"""
        WITH filtered AS (
          SELECT species, CAST(gbifid AS VARCHAR) AS gbifid,
            decimallongitude, decimallatitude,
            CAST(FLOOR((decimallongitude + 180.0) / {CELL_DEGREES}) AS BIGINT) AS cell_x,
            CAST(FLOOR((decimallatitude + 90.0) / {CELL_DEGREES}) AS BIGINT) AS cell_y
          FROM {source}
          WHERE {_where_sql(candidates.scientific_name)}
        )
        SELECT species,cell_x,cell_y,
          COUNT(*)::BIGINT AS n_occurrences_in_cell,
          ARG_MIN(gbifid,gbifid) AS gbifid,
          ARG_MIN(decimallongitude,gbifid) AS longitude,
          ARG_MIN(decimallatitude,gbifid) AS latitude
        FROM filtered
        GROUP BY species,cell_x,cell_y
        ORDER BY species,cell_x,cell_y
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
      "answer_check_features_read":False,"model_fitting_performed":False,
    }
    meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def run_aggregate(*,candidate_path,parts_root,output_dir):
    candidates=load_candidates(candidate_path)
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata_*.json"))
    partials=sorted(root.rglob("partial_*.parquet"))
    if len(metas)!=EXPECTED_CHUNKS or len(partials)!=EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected 32 v5 occurrence chunks; metadata={len(metas)} partials={len(partials)}"
        )
    metadata=[json.loads(p.read_text()) for p in metas]
    by_idx={int(m["chunk_index"]):m for m in metadata}
    part_idx={int(p.stem.rsplit("_",1)[1]):p for p in partials}
    if set(by_idx)!=set(range(EXPECTED_CHUNKS)) or set(part_idx)!=set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("v5 occurrence chunk index set incomplete")
    for i in range(EXPECTED_CHUNKS):
        if _sha256(part_idx[i])!=by_idx[i]["partial_sha256"]:
            raise RuntimeError(f"v5 occurrence partial SHA mismatch: {i}")
    if len({m["candidate_roster_sha256"] for m in metadata})!=1 or metadata[0]["candidate_roster_sha256"]!=_sha256(candidate_path):
        raise RuntimeError("v5 candidate roster fingerprint changed across chunks")
    for key in ("environmental_values_read","eligibility_bits_opened","answer_check_features_read","model_fitting_performed"):
        if any(m.get(key) is not False for m in metadata):
            raise RuntimeError(f"v5 pre-eligibility information boundary crossed: {key}")

    cells=_combine_cells([part_idx[i] for i in range(EXPECTED_CHUNKS)])
    models=[];ledgers=[];summaries=[]
    for taxon in candidates.scientific_name:
        subset=cells.loc[cells.species.astype(str).eq(str(taxon))].copy()
        raw_n=int(subset["n_occurrences_in_cell"].sum()) if len(subset) else 0
        thin_n=int(len(subset))
        if raw_n<MIN_RAW_OCCURRENCES or thin_n<MIN_THINNED_CELLS:
            summaries.append({
              "scientific_name":str(taxon),
              "raw_occurrences":raw_n,
              "thinned_occurrences":thin_n,
              "model_pool_occurrences":0,
              "answer_check_occurrences":0,
              "split_digest":"",
              "source_gate_passed":False,
            })
            continue
        m,l,s=_freeze_taxon(cells,taxon)
        models.append(m);ledgers.append(l);summaries.append(s)
    model=(pd.concat(models,ignore_index=True) if models else pd.DataFrame(
        columns=["scientific_name","occurrence_id","gbifid","longitude","latitude","cell_x","cell_y","spatial_block"]
    ))
    ledger=(pd.concat(ledgers,ignore_index=True) if ledgers else pd.DataFrame(
        columns=["scientific_name","occurrence_id","spatial_block","outer_role"]
    ))
    summary=pd.DataFrame(summaries)
    if len(summary)!=EXPECTED_CANDIDATES:
        raise RuntimeError("v5 occurrence source-gate audit denominator changed")
    passed=int(summary["source_gate_passed"].sum())
    if passed<50:
        raise RuntimeError(
            f"v5 source geometry leaves fewer than 50 candidates before background eligibility: {passed}"
        )

    answer_ids=set(
        ledger.loc[ledger.outer_role.eq("answer_check"),"occurrence_id"].astype(str)
    )
    if set(model.occurrence_id.astype(str)) & answer_ids:
        raise RuntimeError("v5 answer-check occurrence leaked into model-pool artifact")

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    mp=out/"model_pool_occurrences_v5.csv"
    op=out/"outer_split_v5.csv"
    sp=out/"taxon_source_gate_v5.csv"
    model.to_csv(mp,index=False);ledger.to_csv(op,index=False);summary.to_csv(sp,index=False)
    result={
      "program":PROGRAM,"status":"candidate120_occurrence_split_frozen",
      "candidate_count":EXPECTED_CANDIDATES,
      "source_gate_eligible_count":int(summary["source_gate_passed"].sum()),
      "source_gate_ineligible_count":int((~summary["source_gate_passed"]).sum()),
      "source_gate_ineligible_taxa":summary.loc[~summary["source_gate_passed"],"scientific_name"].astype(str).tolist(),
      "model_pool_occurrences":int(len(model)),
      "answer_check_occurrences":int((ledger.outer_role=="answer_check").sum()),
      "model_pool_sha256":_sha256(mp),"outer_split_sha256":_sha256(op),
      "source_gate_sha256":_sha256(sp),
      "environmental_values_read":False,"eligibility_bits_opened":False,
      "answer_check_coordinates_persisted_for_eligibility":False,
      "answer_check_features_read":False,"model_fitting_performed":False,
      "next_gate":"compute_300km_geometry_eligibility_for_candidate120",
    }
    (out/"occurrence_split_result_v5.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n"
    )
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("chunk")
    q.add_argument("--candidates",required=True);q.add_argument("--chunk-index",type=int,required=True)
    q.add_argument("--chunk-count",type=int,default=32);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate")
    q.add_argument("--candidates",required=True);q.add_argument("--parts-root",required=True)
    q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    result=(
      run_chunk(candidate_path=a.candidates,chunk_index=a.chunk_index,chunk_count=a.chunk_count,output_dir=a.output_dir)
      if a.command=="chunk"
      else run_aggregate(candidate_path=a.candidates,parts_root=a.parts_root,output_dir=a.output_dir)
    )
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
