"""Metadata-only 80-candidate roster execution for SDMR fresh empirical v3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal, gbif_snapshot_s3_uri
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list
from .cohort import combine_partials
from .cohort_v3_candidates import select_candidate_roster

PROGRAM = "sdmr-fresh-empirical-v3-candidate-roster"
SNAPSHOT_DATE = "2026-08-01"
SNAPSHOT_DOI = "10.15468/dl.fs3btq"
SNAPSHOT_REGION = "us-east-1"
YEAR_MIN = 2010
YEAR_MAX = 2025
GRID_DEGREES = 1.0
EXPECTED_CHUNKS = 32
EXPECTED_HISTORICAL = 84
EXPECTED_PREDECESSOR = 50
EXPECTED_CANDIDATES = 80

def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _load_names(path: str | Path, *, expected_rows: int) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "scientific_name" not in df.columns:
        raise ValueError(f"{path} missing scientific_name")
    names = df["scientific_name"].astype(str).str.strip()
    if len(df) != expected_rows or names.eq("").any() or names.duplicated().any():
        raise ValueError(f"{path} denominator/identity invalid")
    return df.assign(scientific_name=names)

def validate_design(path: str | Path) -> dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program")!="sdmr-fresh-empirical-v3-soil-support-eligibility":
        raise ValueError("wrong v3 design contract")
    roster=c["candidate_roster"]
    if int(roster["exact_candidates"])!=EXPECTED_CANDIDATES or int(roster["final_taxa"])!=50:
        raise ValueError("v3 candidate/final denominator changed")
    if roster["source"]!="GBIF 2026-08-01 snapshot":
        raise ValueError("v3 GBIF source changed")
    if list(roster["temporal_window"])!=[YEAR_MIN,YEAR_MAX]:
        raise ValueError("v3 temporal window changed")
    if c["information_barrier"]["forbidden_before_final_50"][-1]!="EMP-A through EMP-F outcomes":
        raise ValueError("v3 information barrier changed")
    return c

def _where_sql(excluded: Iterable[str]) -> str:
    names=sorted({str(x).strip() for x in excluded if str(x).strip()})
    excluded_sql=",".join(_sql_literal(x) for x in names)
    return " AND ".join([
        "phylum = 'Tracheophyta'",
        "upper(taxonrank) = 'SPECIES'",
        "species IS NOT NULL",
        "trim(species) <> ''",
        "family IS NOT NULL",
        "trim(family) <> ''",
        "genus IS NOT NULL",
        "trim(genus) <> ''",
        f"year BETWEEN {YEAR_MIN} AND {YEAR_MAX}",
        "(occurrencestatus IS NULL OR upper(occurrencestatus) = 'PRESENT')",
        "(basisofrecord IS NULL OR upper(basisofrecord) <> 'FOSSIL_SPECIMEN')",
        "(coordinateuncertaintyinmeters IS NULL OR coordinateuncertaintyinmeters <= 10000)",
        "decimallatitude IS NOT NULL",
        "decimallongitude IS NOT NULL",
        "decimallatitude BETWEEN -90 AND 90",
        "decimallongitude BETWEEN -180 AND 180",
        "NOT (decimallatitude = 0 AND decimallongitude = 0)",
        f"species NOT IN ({excluded_sql})",
    ])

def run_chunk(*, design_path, historical_path, predecessor_path, chunk_index, chunk_count, output_dir):
    validate_design(design_path)
    historical=_load_names(historical_path,expected_rows=EXPECTED_HISTORICAL)
    predecessor=_load_names(predecessor_path,expected_rows=EXPECTED_PREDECESSOR)
    excluded=set(historical.scientific_name)|set(predecessor.scientific_name)
    if len(excluded) < EXPECTED_HISTORICAL:
        raise ValueError("v3 exclusions collapsed unexpectedly")
    if int(chunk_count)!=EXPECTED_CHUNKS or not 0<=int(chunk_index)<EXPECTED_CHUNKS:
        raise ValueError("v3 chunk denominator changed")

    import duckdb
    con=duckdb.connect()
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    partial=out/f"partial_{int(chunk_index):02d}.parquet"
    metadata_path=out/f"metadata_{int(chunk_index):02d}.json"
    try:
        _configure_duckdb_cloud(con,cloud_provider="aws",region=SNAPSHOT_REGION)
        files=_list_snapshot_shards(con,SNAPSHOT_DATE,SNAPSHOT_REGION)
        selected=_chunk_files(files,int(chunk_index),int(chunk_count))
        if not selected:
            raise RuntimeError("empty GBIF shard chunk")
        source=f"read_parquet({_sql_list(selected)}, union_by_name=true)"
        query=f"""
        WITH filtered AS (
          SELECT species AS scientific_name, family, genus,
            CAST(FLOOR((decimallongitude + 180.0) / {GRID_DEGREES}) AS BIGINT) AS cell_x,
            CAST(FLOOR((decimallatitude + 90.0) / {GRID_DEGREES}) AS BIGINT) AS cell_y
          FROM {source}
          WHERE {_where_sql(excluded)}
        )
        SELECT scientific_name,family,genus,cell_x,cell_y,
          COUNT(*)::BIGINT AS n_occurrences_in_cell
        FROM filtered
        GROUP BY scientific_name,family,genus,cell_x,cell_y
        ORDER BY scientific_name,family,genus,cell_x,cell_y
        """
        con.execute(f"COPY ({query}) TO {_sql_literal(str(partial.resolve()))} (FORMAT PARQUET, COMPRESSION ZSTD)")
        partial_rows=int(con.execute(f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(partial.resolve()))})").fetchone()[0])
    finally:
        con.close()

    meta={
      "program":PROGRAM,"snapshot_date":SNAPSHOT_DATE,"snapshot_doi":SNAPSHOT_DOI,"region":SNAPSHOT_REGION,
      "chunk_index":int(chunk_index),"chunk_count":EXPECTED_CHUNKS,
      "snapshot_shard_count":len(files),"chunk_shard_count":len(selected),
      "first_shard":selected[0],"last_shard":selected[-1],
      "design_sha256":_sha256(design_path),"historical_sha256":_sha256(historical_path),
      "predecessor_sha256":_sha256(predecessor_path),"excluded_names":len(excluded),
      "partial_rows":partial_rows,"partial_sha256":_sha256(partial),
      "environmental_values_read":False,"soil_support_opened":False,"answer_check_accessed":False,
      "model_fitting_performed":False,"prediction_metrics_read":False,"process_states_read":False,
    }
    metadata_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return meta

def run_aggregate(*, design_path, historical_path, predecessor_path, parts_root, output_dir):
    validate_design(design_path)
    historical=_load_names(historical_path,expected_rows=EXPECTED_HISTORICAL)
    predecessor=_load_names(predecessor_path,expected_rows=EXPECTED_PREDECESSOR)
    excluded=set(historical.scientific_name)|set(predecessor.scientific_name)

    root=Path(parts_root)
    metas=sorted(root.rglob("metadata_*.json"))
    partials=sorted(root.rglob("partial_*.parquet"))
    if len(metas)!=EXPECTED_CHUNKS or len(partials)!=EXPECTED_CHUNKS:
        raise RuntimeError(f"expected {EXPECTED_CHUNKS} v3 chunks; metadata={len(metas)} partials={len(partials)}")
    metadata=[json.loads(p.read_text()) for p in metas]
    if {int(x["chunk_index"]) for x in metadata}!=set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("v3 chunk index set incomplete")
    for key in ("environmental_values_read","soil_support_opened","answer_check_accessed","model_fitting_performed","prediction_metrics_read","process_states_read"):
        if any(x.get(key) is not False for x in metadata):
            raise RuntimeError(f"v3 information barrier crossed: {key}")
    for p,m in zip(sorted(partials,key=lambda x:int(x.stem.rsplit("_",1)[1])),sorted(metadata,key=lambda x:int(x["chunk_index"]))):
        if _sha256(p)!=m["partial_sha256"]:
            raise RuntimeError("v3 partial SHA mismatch")

    summary=combine_partials(partials)
    audit,roster=select_candidate_roster(summary,excluded_names=excluded)
    if len(roster)!=EXPECTED_CANDIDATES:
        raise RuntimeError("v3 roster did not freeze exactly 80 taxa")

    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    summary_path=out/"candidate_availability_summary.csv"
    audit_path=out/"candidate_selection_audit.csv"
    roster_path=out/"candidate_roster_v3.csv"
    summary.to_csv(summary_path,index=False)
    audit.to_csv(audit_path,index=False)
    roster.to_csv(roster_path,index=False)
    result={
      "program":PROGRAM,
      "status":"candidate_roster_frozen_outcomes_unopened",
      "candidate_count":int(len(roster)),
      "candidate_families":int(roster.family.nunique()),
      "candidate_genera":int(roster.genus.nunique()),
      "candidate_roster_sha256":_sha256(roster_path),
      "selection_audit_sha256":_sha256(audit_path),
      "availability_summary_sha256":_sha256(summary_path),
      "historical_exclusions":int(len(historical)),
      "predecessor50_exclusions":int(len(predecessor)),
      "environmental_values_read":False,"soil_support_opened":False,"answer_check_accessed":False,
      "model_fitting_performed":False,"prediction_metrics_read":False,"process_states_read":False,
      "next_gate":"freeze coordinate-only occurrence split and 300-km background for all 80 candidates",
    }
    (out/"candidate_roster_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    for name in ("chunk","aggregate"):
        q=sub.add_parser(name)
        q.add_argument("--design",required=True); q.add_argument("--historical",required=True); q.add_argument("--predecessor50",required=True)
        q.add_argument("--output-dir",required=True)
        if name=="chunk":
            q.add_argument("--chunk-index",type=int,required=True); q.add_argument("--chunk-count",type=int,default=EXPECTED_CHUNKS)
        else:
            q.add_argument("--parts-root",required=True)
    a=p.parse_args()
    if a.command=="chunk":
        result=run_chunk(design_path=a.design,historical_path=a.historical,predecessor_path=a.predecessor50,
                         chunk_index=a.chunk_index,chunk_count=a.chunk_count,output_dir=a.output_dir)
    else:
        result=run_aggregate(design_path=a.design,historical_path=a.historical,predecessor_path=a.predecessor50,
                             parts_root=a.parts_root,output_dir=a.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
