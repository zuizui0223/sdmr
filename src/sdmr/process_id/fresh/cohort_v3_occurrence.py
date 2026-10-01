"""Coordinate-only occurrence source gate and outer split for fresh empirical v3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal
from sdmr.sealed_occurrence_contract import freeze_occurrence_answer_check_split
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list

PROGRAM="sdmr-fresh-empirical-v3-occurrence-split"
SNAPSHOT_DATE="2026-08-01"
SNAPSHOT_DOI="10.15468/dl.fs3btq"
SNAPSHOT_REGION="us-east-1"
YEAR_MIN=2010
YEAR_MAX=2025
CELL_DEGREES=0.05
EXPECTED_CANDIDATES=80
EXPECTED_CHUNKS=32
MIN_RAW_OCCURRENCES=80
MIN_THINNED_CELLS=50
OUTER_N_BLOCKS=8
ANSWER_CHECK_FRACTION=0.20
OUTER_SEED=42

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_candidates(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={"candidate_rank","scientific_name","family","genus","selection_hash"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v3 candidate roster missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_CANDIDATES or df["scientific_name"].astype(str).nunique()!=EXPECTED_CANDIDATES:
        raise ValueError("v3 candidate roster must contain exactly 80 unique taxa")
    ranks=sorted(pd.to_numeric(df["candidate_rank"],errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v3 candidate ranks must be exactly 1..80")
    df["scientific_name"]=df["scientific_name"].astype(str).str.strip()
    if df["scientific_name"].eq("").any():
        raise ValueError("v3 candidate names must be non-empty")
    return df.sort_values("candidate_rank").reset_index(drop=True)

def _species_sql(names)->str:
    vals=sorted({str(x).strip() for x in names if str(x).strip()})
    if len(vals)!=EXPECTED_CANDIDATES:
        raise ValueError("v3 occurrence scan requires exactly 80 candidate names")
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
        raise ValueError("v3 occurrence chunk denominator changed")
    import duckdb
    con=duckdb.connect()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    partial=out/f"partial_{int(chunk_index):02d}.parquet"
    metadata_path=out/f"metadata_{int(chunk_index):02d}.json"
    try:
        _configure_duckdb_cloud(con,cloud_provider="aws",region=SNAPSHOT_REGION)
        files=_list_snapshot_shards(con,SNAPSHOT_DATE,SNAPSHOT_REGION)
        shards=_chunk_files(files,int(chunk_index),int(chunk_count))
        if not shards:
            raise RuntimeError("empty v3 occurrence shard chunk")
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
        con.execute(f"COPY ({query}) TO {_sql_literal(str(partial.resolve()))} (FORMAT PARQUET, COMPRESSION ZSTD)")
        partial_rows=int(con.execute(f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(partial.resolve()))})").fetchone()[0])
    finally:
        con.close()
    meta={
      "program":PROGRAM,"snapshot_date":SNAPSHOT_DATE,"snapshot_doi":SNAPSHOT_DOI,
      "chunk_index":int(chunk_index),"chunk_count":EXPECTED_CHUNKS,
      "snapshot_shard_count":len(files),"chunk_shard_count":len(shards),
      "candidate_roster_sha256":_sha256(candidate_path),"partial_rows":partial_rows,
      "partial_sha256":_sha256(partial),
      "environmental_values_read":False,"soil_support_opened":False,
      "answer_check_features_read":False,"model_fitting_performed":False,
    }
    metadata_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def _combine_cells(paths):
    frames=[pd.read_parquet(p) for p in paths]
    raw=pd.concat(frames,ignore_index=True)
    raw["gbifid"]=raw["gbifid"].astype(str)
    groups=["species","cell_x","cell_y"]
    counts=raw.groupby(groups,as_index=False)["n_occurrences_in_cell"].sum()
    reps=(raw.sort_values([*groups,"gbifid"],kind="mergesort")
          .drop_duplicates(groups,keep="first")
          [[*groups,"gbifid","longitude","latitude"]])
    return counts.merge(reps,on=groups,how="left",validate="one_to_one").sort_values(groups).reset_index(drop=True)

def _freeze_taxon(cells,taxon):
    sub=cells.loc[cells.species.astype(str).eq(str(taxon))].copy()
    raw_n=int(sub.n_occurrences_in_cell.sum()); thin_n=int(len(sub))
    if raw_n<MIN_RAW_OCCURRENCES or thin_n<MIN_THINNED_CELLS:
        raise RuntimeError(f"v3 candidate failed source gate without replacement: {taxon}: raw={raw_n}, thinned={thin_n}")
    sub["occurrence_id"]=sub["species"].astype(str)+"|"+sub["gbifid"].astype(str)
    split=freeze_occurrence_answer_check_split(
        sub[["occurrence_id","longitude","latitude"]],
        id_col="occurrence_id",lon_col="longitude",lat_col="latitude",
        n_blocks=OUTER_N_BLOCKS,holdout_fraction=ANSWER_CHECK_FRACTION,random_state=OUTER_SEED,
    )
    assign=split.assignment.copy()
    assign.insert(0,"scientific_name",str(taxon))
    joined=sub.merge(assign[["occurrence_id","outer_role","spatial_block"]],on="occurrence_id",validate="one_to_one")
    model=joined.loc[joined.outer_role.eq("model_pool"),[
        "species","occurrence_id","gbifid","longitude","latitude","cell_x","cell_y","spatial_block"
    ]].rename(columns={"species":"scientific_name"})
    ledger=assign[["scientific_name","occurrence_id","spatial_block","outer_role"]].copy()
    summary={
      "scientific_name":str(taxon),"raw_occurrences":raw_n,"thinned_occurrences":thin_n,
      "model_pool_occurrences":int(len(model)),
      "answer_check_occurrences":int((ledger.outer_role=="answer_check").sum()),
      "split_digest":split.split_digest,"source_gate_passed":True,
    }
    if summary["model_pool_occurrences"]<1 or summary["answer_check_occurrences"]<1:
        raise RuntimeError(f"v3 outer split lost a role for {taxon}")
    return model,ledger,summary

def run_aggregate(*,candidate_path,parts_root,output_dir):
    candidates=load_candidates(candidate_path)
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata_*.json")); partials=sorted(root.rglob("partial_*.parquet"))
    if len(metas)!=EXPECTED_CHUNKS or len(partials)!=EXPECTED_CHUNKS:
        raise RuntimeError(f"expected 32 v3 occurrence chunks; metadata={len(metas)} partials={len(partials)}")
    metadata=[json.loads(p.read_text()) for p in metas]
    if {int(x["chunk_index"]) for x in metadata}!=set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("v3 occurrence chunk index set incomplete")
    by_idx={int(x["chunk_index"]):x for x in metadata}
    part_by_idx={int(p.stem.rsplit("_",1)[1]):p for p in partials}
    for i in range(EXPECTED_CHUNKS):
        if _sha256(part_by_idx[i])!=by_idx[i]["partial_sha256"]:
            raise RuntimeError(f"v3 occurrence partial SHA mismatch: {i}")
    if len({x["candidate_roster_sha256"] for x in metadata})!=1:
        raise RuntimeError("candidate roster fingerprint differs across chunks")
    if next(iter({x["candidate_roster_sha256"] for x in metadata}))!=_sha256(candidate_path):
        raise RuntimeError("candidate roster fingerprint differs from aggregate input")
    for key in ("environmental_values_read","soil_support_opened","answer_check_features_read","model_fitting_performed"):
        if any(x.get(key) is not False for x in metadata):
            raise RuntimeError(f"v3 pre-support information barrier crossed: {key}")

    cells=_combine_cells([part_by_idx[i] for i in range(EXPECTED_CHUNKS)])
    observed=set(cells.species.astype(str))
    missing=[x for x in candidates.scientific_name if x not in observed]
    if missing: raise RuntimeError("v3 candidates absent from occurrence scan: "+", ".join(missing))

    models=[];ledgers=[];summaries=[]
    for taxon in candidates.scientific_name:
        m,l,s=_freeze_taxon(cells,taxon);models.append(m);ledgers.append(l);summaries.append(s)
    model=pd.concat(models,ignore_index=True); ledger=pd.concat(ledgers,ignore_index=True); summary=pd.DataFrame(summaries)
    if len(summary)!=EXPECTED_CANDIDATES or not summary.source_gate_passed.all():
        raise RuntimeError("v3 occurrence source gate denominator changed")
    answer_ids=set(ledger.loc[ledger.outer_role.eq("answer_check"),"occurrence_id"].astype(str))
    if set(model.occurrence_id.astype(str)) & answer_ids:
        raise RuntimeError("v3 answer-check occurrence leaked into model-pool artifact")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    model_path=out/"model_pool_occurrences_v3.csv"; ledger_path=out/"outer_split_v3.csv"; summary_path=out/"taxon_source_gate_v3.csv"
    model.to_csv(model_path,index=False);ledger.to_csv(ledger_path,index=False);summary.to_csv(summary_path,index=False)
    result={
      "program":PROGRAM,"status":"candidate80_occurrence_split_passed",
      "candidate_count":EXPECTED_CANDIDATES,
      "model_pool_occurrences":int(len(model)),
      "answer_check_occurrences":int((ledger.outer_role=="answer_check").sum()),
      "model_pool_sha256":_sha256(model_path),"outer_split_sha256":_sha256(ledger_path),
      "source_gate_sha256":_sha256(summary_path),
      "environmental_values_read":False,"soil_support_opened":False,
      "answer_check_coordinates_persisted_for_support":False,
      "answer_check_features_read":False,"model_fitting_performed":False,
      "next_gate":"build_300km_model_pool_only_background_for_all_80_candidates",
    }
    (out/"occurrence_split_result_v3.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("chunk");q.add_argument("--candidates",required=True);q.add_argument("--chunk-index",type=int,required=True);q.add_argument("--chunk-count",type=int,default=32);q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate");q.add_argument("--candidates",required=True);q.add_argument("--parts-root",required=True);q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    result=(run_chunk(candidate_path=a.candidates,chunk_index=a.chunk_index,chunk_count=a.chunk_count,output_dir=a.output_dir)
            if a.command=="chunk" else run_aggregate(candidate_path=a.candidates,parts_root=a.parts_root,output_dir=a.output_dir))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
