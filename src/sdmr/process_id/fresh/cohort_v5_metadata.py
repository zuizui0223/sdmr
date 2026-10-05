"""Metadata-only 120-candidate execution for SDMR fresh empirical v5."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list
from .cohort import combine_partials
from .cohort_v5_candidates import select_candidate_roster

PROGRAM="sdmr-fresh-empirical-v5-candidate-roster"
SNAPSHOT_DATE="2026-08-01"
SNAPSHOT_DOI="10.15468/dl.fs3btq"
SNAPSHOT_REGION="us-east-1"
YEAR_MIN=2010
YEAR_MAX=2025
GRID_DEGREES=1.0
EXPECTED_CHUNKS=32
EXPECTED_EXCLUSIONS=304
EXPECTED_CANDIDATES=120

def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _load_exclusions(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    if "scientific_name" not in df.columns:
        raise ValueError("v5 exclusion manifest missing scientific_name")
    names=df["scientific_name"].astype(str).str.strip()
    if len(df)!=EXPECTED_EXCLUSIONS or names.eq("").any() or names.duplicated().any():
        raise ValueError("v5 exclusion manifest denominator/identity invalid")
    return df.assign(scientific_name=names)

def validate_design(path: str|Path)->dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program")!="sdmr-fresh-empirical-v5-preeligibility":
        raise ValueError("wrong v5 design contract")
    if c.get("status")!="design_frozen_before_v5_candidate_selection":
        raise ValueError("v5 design status changed")
    if int(c["independence"]["prior_taxa"])!=EXPECTED_EXCLUSIONS:
        raise ValueError("v5 exclusion denominator changed")
    if int(c["candidate_roster"]["exact_candidates"])!=EXPECTED_CANDIDATES:
        raise ValueError("v5 candidate denominator changed")
    if int(c["final_selection"]["final_taxa"])!=50:
        raise ValueError("v5 final denominator changed")
    if c["all46_support_eligibility"]["persist_numeric_environmental_values"] is not False:
        raise ValueError("v5 support stage opened numeric values")
    if c["geometry_eligibility"]["whole_program_failure_on_one_geometry_ineligible"] is not False:
        raise ValueError("v5 geometry eligibility reverted to v4 failure semantics")
    return c

def _where_sql(excluded: Iterable[str])->str:
    names=sorted({str(x).strip() for x in excluded if str(x).strip()})
    if len(names)!=EXPECTED_EXCLUSIONS:
        raise ValueError("v5 exclusion universe changed")
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

def run_chunk(*,design_path,exclusion_path,chunk_index,chunk_count,output_dir):
    validate_design(design_path)
    exclusion=_load_exclusions(exclusion_path)
    if int(chunk_count)!=EXPECTED_CHUNKS or not 0<=int(chunk_index)<EXPECTED_CHUNKS:
        raise ValueError("v5 chunk denominator changed")
    import duckdb
    con=duckdb.connect()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    partial=out/f"partial_{int(chunk_index):02d}.parquet"
    meta_path=out/f"metadata_{int(chunk_index):02d}.json"
    try:
        _configure_duckdb_cloud(con,cloud_provider="aws",region=SNAPSHOT_REGION)
        files=_list_snapshot_shards(con,SNAPSHOT_DATE,SNAPSHOT_REGION)
        selected=_chunk_files(files,int(chunk_index),int(chunk_count))
        if not selected:
            raise RuntimeError("empty v5 GBIF shard chunk")
        source=f"read_parquet({_sql_list(selected)}, union_by_name=true)"
        query=f"""
        WITH filtered AS (
          SELECT species AS scientific_name, family, genus,
            CAST(FLOOR((decimallongitude + 180.0) / {GRID_DEGREES}) AS BIGINT) AS cell_x,
            CAST(FLOOR((decimallatitude + 90.0) / {GRID_DEGREES}) AS BIGINT) AS cell_y
          FROM {source}
          WHERE {_where_sql(exclusion.scientific_name)}
        )
        SELECT scientific_name,family,genus,cell_x,cell_y,
          COUNT(*)::BIGINT AS n_occurrences_in_cell
        FROM filtered
        GROUP BY scientific_name,family,genus,cell_x,cell_y
        ORDER BY scientific_name,family,genus,cell_x,cell_y
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
      "snapshot_shard_count":len(files),"chunk_shard_count":len(selected),
      "design_sha256":_sha256(design_path),"exclusion_sha256":_sha256(exclusion_path),
      "excluded_names":len(exclusion),"partial_rows":partial_rows,"partial_sha256":_sha256(partial),
      "environmental_values_read":False,"eligibility_bits_opened":False,
      "answer_check_accessed":False,"model_fitting_performed":False,
      "prediction_metrics_read":False,"process_states_read":False,
    }
    meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta

def run_aggregate(*,design_path,exclusion_path,parts_root,output_dir):
    validate_design(design_path)
    exclusion=_load_exclusions(exclusion_path)
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata_*.json"))
    partials=sorted(root.rglob("partial_*.parquet"))
    if len(metas)!=EXPECTED_CHUNKS or len(partials)!=EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected {EXPECTED_CHUNKS} v5 chunks; metadata={len(metas)} partials={len(partials)}"
        )
    metadata=[json.loads(p.read_text()) for p in metas]
    if {int(x["chunk_index"]) for x in metadata}!=set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("v5 chunk index set incomplete")
    for key in (
        "environmental_values_read","eligibility_bits_opened","answer_check_accessed",
        "model_fitting_performed","prediction_metrics_read","process_states_read",
    ):
        if any(x.get(key) is not False for x in metadata):
            raise RuntimeError(f"v5 candidate information boundary crossed: {key}")
    by_idx={int(x["chunk_index"]):x for x in metadata}
    part_by_idx={int(p.stem.rsplit("_",1)[1]):p for p in partials}
    for i in range(EXPECTED_CHUNKS):
        if _sha256(part_by_idx[i])!=by_idx[i]["partial_sha256"]:
            raise RuntimeError(f"v5 partial SHA mismatch: {i}")
    if len({x["exclusion_sha256"] for x in metadata})!=1 or metadata[0]["exclusion_sha256"]!=_sha256(exclusion_path):
        raise RuntimeError("v5 exclusion fingerprint changed across chunks")

    summary=combine_partials([part_by_idx[i] for i in range(EXPECTED_CHUNKS)])
    audit,roster=select_candidate_roster(
        summary,excluded_names=set(exclusion.scientific_name.astype(str))
    )
    if len(roster)!=EXPECTED_CANDIDATES:
        raise RuntimeError("v5 candidate roster did not freeze exactly 120 taxa")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    sp=out/"candidate_availability_summary_v5.csv"
    ap=out/"candidate_selection_audit_v5.csv"
    rp=out/"candidate_roster_v5.csv"
    summary.to_csv(sp,index=False);audit.to_csv(ap,index=False);roster.to_csv(rp,index=False)
    result={
      "program":PROGRAM,"status":"candidate120_frozen_outcomes_unopened",
      "candidate_count":int(len(roster)),
      "candidate_families":int(roster.family.nunique()),
      "candidate_genera":int(roster.genus.nunique()),
      "candidate_roster_sha256":_sha256(rp),
      "selection_audit_sha256":_sha256(ap),
      "availability_summary_sha256":_sha256(sp),
      "prior_taxa_excluded":int(len(exclusion)),
      "environmental_values_read":False,"eligibility_bits_opened":False,
      "answer_check_accessed":False,"model_fitting_performed":False,
      "prediction_metrics_read":False,"process_states_read":False,
      "next_gate":"freeze occurrence split then geometry eligibility and all46 support before final50 selection",
    }
    (out/"candidate_roster_result_v5.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n"
    )
    return result

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("chunk")
    q.add_argument("--design",required=True);q.add_argument("--exclusions",required=True)
    q.add_argument("--chunk-index",type=int,required=True);q.add_argument("--chunk-count",type=int,default=32)
    q.add_argument("--output-dir",required=True)
    q=sub.add_parser("aggregate")
    q.add_argument("--design",required=True);q.add_argument("--exclusions",required=True)
    q.add_argument("--parts-root",required=True);q.add_argument("--output-dir",required=True)
    a=p.parse_args()
    result=(
      run_chunk(design_path=a.design,exclusion_path=a.exclusions,chunk_index=a.chunk_index,chunk_count=a.chunk_count,output_dir=a.output_dir)
      if a.command=="chunk"
      else run_aggregate(design_path=a.design,exclusion_path=a.exclusions,parts_root=a.parts_root,output_dir=a.output_dir)
    )
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
