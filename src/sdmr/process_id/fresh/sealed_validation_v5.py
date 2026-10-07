"""One-shot sealed answer-check validation for fresh empirical v5.

This module is downstream of a frozen final50, a terminally passing numeric
feature gate, and a frozen model-pool artifact.  It never refits or reselects a
model.  The only newly opened information is the frozen outer answer-check
occurrence coordinates and their 46 environmental predictor values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal
from sdmr.process_id.evidence import _balanced_log_score
from sdmr.process_id.fresh.features import build_frozen_layer_specs
from sdmr.process_id.fresh.features_v3 import STRUCTURAL_RULES, SOIL_PREDICTORS
from sdmr.process_id.fresh.features_v5 import spatial_shard_bounds
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list
from sdmr.process_id.taxonomy import DEFAULT_PLANT_PROCESSES

PROGRAM="sdmr-fresh-empirical-v5-sealed-validation"
SNAPSHOT_DATE="2026-08-01"
SNAPSHOT_REGION="us-east-1"
YEAR_MIN=2010
YEAR_MAX=2025
EXPECTED_TAXA=50
EXPECTED_PREDICTORS=46
EXPECTED_PROCESSES=6
EXPECTED_CHUNKS=32
SOIL_SHARD_COUNT=16
PRIMARY_ROUTES=(
    "sdmr_process_first",
    "matched_learner_flat_predictive_selector",
)
REPORT_ROUTES=(
    "auc_oriented_flat_selector",
    "correlation_vif_flat_filter",
    "full_46_flat_hgb",
)
ALL_ROUTES=PRIMARY_ROUTES+REPORT_ROUTES
BOOTSTRAP_REPLICATES=20_000
BOOTSTRAP_SEED=20260926
EMP_A_MINIMUM=0.01
EMP_C_MINIMUM_AUC_DIFFERENCE=-0.02
EMP_D_MINIMUM_STABLE_FRACTION=0.80


def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_contract(path: str|Path)->dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("schema")!="sdmr.fresh_empirical_v5_sealed_validation.v1":
        raise ValueError("wrong v5 sealed-validation schema")
    if c.get("status")!="frozen_before_model_pool_results_and_answer_check_opening":
        raise ValueError("v5 sealed-validation contract status changed")
    if int(c["upstream_requirements"]["exact_taxa"])!=EXPECTED_TAXA:
        raise ValueError("v5 sealed-validation taxon denominator changed")
    features=c["answer_check_features"]
    if int(features["predictor_count"])!=EXPECTED_PREDICTORS:
        raise ValueError("v5 sealed-validation predictor denominator changed")
    if int(features["minimum_complete_occurrence_rows_for_evaluable_taxon"])!=1:
        raise ValueError("v5 answer-check occurrence evaluability threshold changed")
    if int(features["minimum_complete_background_rows_for_evaluable_taxon"])!=1:
        raise ValueError("v5 evaluation-background evaluability threshold changed")
    promotion=c["promotion"]
    if float(promotion["EMP_A"]["minimum"])!=EMP_A_MINIMUM:
        raise ValueError("EMP-A threshold changed")
    if int(promotion["EMP_B"]["bootstrap_replicates"])!=BOOTSTRAP_REPLICATES:
        raise ValueError("EMP-B bootstrap denominator changed")
    if int(promotion["EMP_B"]["bootstrap_seed"])!=BOOTSTRAP_SEED:
        raise ValueError("EMP-B bootstrap seed changed")
    if float(promotion["EMP_C"]["minimum_mean_auc_difference"])!=EMP_C_MINIMUM_AUC_DIFFERENCE:
        raise ValueError("EMP-C threshold changed")
    if promotion["EMP_C"]["require_all_taxa_evaluable"] is not True:
        raise ValueError("EMP-C denominator rule changed")
    if float(promotion["EMP_D"]["minimum_stable_fraction"])!=EMP_D_MINIMUM_STABLE_FRACTION:
        raise ValueError("EMP-D threshold changed")
    if int(promotion["EMP_D"]["denominator_cells"])!=EXPECTED_TAXA*EXPECTED_PROCESSES:
        raise ValueError("EMP-D denominator changed")
    if int(promotion["EMP_F"]["exact_taxa"])!=EXPECTED_TAXA:
        raise ValueError("EMP-F denominator changed")
    return c


def load_selected(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={"selection_rank","scientific_name"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v5 selected manifest missing columns: {sorted(missing)}")
    if len(df)!=EXPECTED_TAXA or df.scientific_name.astype(str).nunique()!=EXPECTED_TAXA:
        raise ValueError("v5 sealed validation requires exact final50")
    ranks=sorted(pd.to_numeric(df.selection_rank,errors="raise").astype(int).tolist())
    if ranks!=list(range(1,EXPECTED_TAXA+1)):
        raise ValueError("v5 selected ranks must be exactly 1..50")
    df["scientific_name"]=df.scientific_name.astype(str).str.strip()
    return df.sort_values("selection_rank").reset_index(drop=True)


def answer_id_table(*,selected_path: str|Path, outer_split_path: str|Path)->pd.DataFrame:
    selected=load_selected(selected_path)
    taxa=set(selected.scientific_name.astype(str))
    outer=pd.read_csv(outer_split_path)
    required={"scientific_name","occurrence_id","spatial_block","outer_role"}
    missing=required-set(outer.columns)
    if missing:
        raise ValueError(f"v5 outer split missing columns: {sorted(missing)}")
    answer=outer.loc[
        outer.scientific_name.astype(str).isin(taxa)
        & outer.outer_role.astype(str).eq("answer_check")
    ].copy()
    if answer.empty:
        raise ValueError("v5 sealed answer-check is empty")
    if answer.occurrence_id.astype(str).duplicated().any():
        raise ValueError("v5 sealed occurrence IDs must be unique")
    if set(answer.scientific_name.astype(str))!=taxa:
        raise ValueError("v5 sealed answer-check does not cover exact final50")
    occurrence_id=answer.occurrence_id.astype(str)
    parsed=occurrence_id.str.rsplit("|",n=1,expand=True)
    if parsed.shape[1]!=2:
        raise ValueError("v5 occurrence_id format changed")
    if not parsed[0].astype(str).eq(answer.scientific_name.astype(str)).all():
        raise ValueError("v5 occurrence_id taxon prefix changed")
    answer["gbifid"]=parsed[1].astype(str)
    if answer.gbifid.eq("").any():
        raise ValueError("v5 answer-check gbifid is empty")
    return answer[["scientific_name","occurrence_id","gbifid","spatial_block"]].sort_values(
        ["scientific_name","occurrence_id"],kind="mergesort"
    ).reset_index(drop=True)


def _where_sql()->str:
    return " AND ".join([
        "upper(g.taxonrank) = 'SPECIES'",
        f"g.year BETWEEN {YEAR_MIN} AND {YEAR_MAX}",
        "(g.occurrencestatus IS NULL OR upper(g.occurrencestatus) = 'PRESENT')",
        "(g.basisofrecord IS NULL OR upper(g.basisofrecord) <> 'FOSSIL_SPECIMEN')",
        "(g.coordinateuncertaintyinmeters IS NULL OR g.coordinateuncertaintyinmeters <= 10000)",
        "g.gbifid IS NOT NULL",
        "g.decimallatitude IS NOT NULL",
        "g.decimallongitude IS NOT NULL",
        "g.decimallatitude BETWEEN -90 AND 90",
        "g.decimallongitude BETWEEN -180 AND 180",
        "NOT (g.decimallatitude = 0 AND g.decimallongitude = 0)",
    ])


def materialize_answer_chunk(
    *,
    selected_path: str|Path,
    outer_split_path: str|Path,
    chunk_index: int,
    chunk_count: int,
    output_dir: str|Path,
)->dict:
    answer=answer_id_table(selected_path=selected_path,outer_split_path=outer_split_path)
    if int(chunk_count)!=EXPECTED_CHUNKS or not 0<=int(chunk_index)<EXPECTED_CHUNKS:
        raise ValueError("v5 sealed occurrence chunk denominator changed")

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
            raise RuntimeError("empty v5 sealed occurrence shard chunk")
        con.register("answer_ids",answer)
        source=f"read_parquet({_sql_list(shards)}, union_by_name=true)"
        query=f"""
        SELECT
          a.scientific_name,
          a.occurrence_id,
          a.spatial_block,
          CAST(g.gbifid AS VARCHAR) AS gbifid,
          g.decimallongitude AS longitude,
          g.decimallatitude AS latitude
        FROM {source} g
        INNER JOIN answer_ids a
          ON g.species = a.scientific_name
         AND CAST(g.gbifid AS VARCHAR) = a.gbifid
        WHERE {_where_sql()}
        ORDER BY a.scientific_name,a.occurrence_id
        """
        con.execute(
            f"COPY ({query}) TO {_sql_literal(str(partial.resolve()))} "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        rows=int(con.execute(
            f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(partial.resolve()))})"
        ).fetchone()[0])
    finally:
        con.close()
    meta={
      "program":PROGRAM,
      "stage":"answer_coordinate_materialization",
      "chunk_index":int(chunk_index),"chunk_count":EXPECTED_CHUNKS,
      "snapshot_shard_count":len(files),"chunk_shard_count":len(shards),
      "selected_sha256":_sha256(selected_path),
      "outer_split_sha256":_sha256(outer_split_path),
      "expected_answer_ids":int(len(answer)),
      "partial_rows":rows,"partial_sha256":_sha256(partial),
      "answer_check_accessed":True,"answer_check_coordinates_read":True,
      "answer_check_features_read":False,"model_refit_performed":False,
    }
    meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta


def aggregate_answer_coordinates(
    *,
    selected_path: str|Path,
    outer_split_path: str|Path,
    parts_root: str|Path,
    output_dir: str|Path,
)->dict:
    expected=answer_id_table(selected_path=selected_path,outer_split_path=outer_split_path)
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata_*.json"))
    partials=sorted(root.rglob("partial_*.parquet"))
    if len(metas)!=EXPECTED_CHUNKS or len(partials)!=EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected {EXPECTED_CHUNKS} v5 sealed occurrence chunks; "
            f"metadata={len(metas)} partials={len(partials)}"
        )
    metadata=[json.loads(p.read_text()) for p in metas]
    by_idx={int(m["chunk_index"]):m for m in metadata}
    part_idx={int(p.stem.rsplit("_",1)[1]):p for p in partials}
    if set(by_idx)!=set(range(EXPECTED_CHUNKS)) or set(part_idx)!=set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("v5 sealed occurrence chunk index set incomplete")
    for i in range(EXPECTED_CHUNKS):
        if _sha256(part_idx[i])!=by_idx[i]["partial_sha256"]:
            raise RuntimeError(f"v5 sealed occurrence partial SHA mismatch: {i}")
    for key in ("selected_sha256","outer_split_sha256","expected_answer_ids"):
        if len({str(m[key]) for m in metadata})!=1:
            raise RuntimeError(f"v5 sealed occurrence chunk invariant differs: {key}")
    if any(m.get("model_refit_performed") is not False for m in metadata):
        raise RuntimeError("model refit occurred during v5 answer coordinate opening")

    frames=[pd.read_parquet(part_idx[i]) for i in range(EXPECTED_CHUNKS)]
    observed=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    if observed.empty:
        raise RuntimeError("v5 sealed occurrence materialization returned zero rows")
    if observed.occurrence_id.astype(str).duplicated().any():
        dup=observed.loc[observed.occurrence_id.astype(str).duplicated(keep=False),"occurrence_id"].astype(str).unique()
        raise RuntimeError("duplicate v5 sealed IDs recovered: "+",".join(dup[:10]))
    if set(observed.occurrence_id.astype(str))!=set(expected.occurrence_id.astype(str)):
        missing=sorted(set(expected.occurrence_id.astype(str))-set(observed.occurrence_id.astype(str)))
        extra=sorted(set(observed.occurrence_id.astype(str))-set(expected.occurrence_id.astype(str)))
        raise RuntimeError(
            f"v5 sealed ID recovery not exact; missing={len(missing)} extra={len(extra)}"
        )
    if not np.isfinite(observed[["longitude","latitude"]].to_numpy(float)).all():
        raise RuntimeError("non-finite sealed answer-check coordinates recovered")
    observed=observed.sort_values(["scientific_name","occurrence_id"],kind="mergesort").reset_index(drop=True)

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    path=out/"answer_check_occurrences_v5.csv"
    observed.to_csv(path,index=False)
    per=observed.groupby(observed.scientific_name.astype(str)).size()
    result={
      "program":PROGRAM,"stage":"answer_coordinate_materialization",
      "status":"exact_sealed_answer_coordinates_materialized",
      "taxon_count":int(per.size),"answer_occurrence_rows":int(len(observed)),
      "minimum_answer_occurrences_per_taxon":int(per.min()),
      "answer_occurrences_sha256":_sha256(path),
      "answer_check_accessed":True,"answer_check_coordinates_read":True,
      "answer_check_features_read":False,"model_refit_performed":False,
      "next_gate":"extract_frozen_46_predictors_for_sealed_answer_occurrences_once",
    }
    (out/"answer_coordinate_result_v5.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n"
    )
    return result


def prepare_answer_locations(answer_path: str|Path):
    answer=pd.read_csv(answer_path)
    required={"scientific_name","occurrence_id","longitude","latitude"}
    missing=required-set(answer.columns)
    if missing:
        raise ValueError(f"v5 answer coordinate artifact missing columns: {sorted(missing)}")
    if answer.occurrence_id.astype(str).duplicated().any():
        raise ValueError("v5 answer occurrence IDs must be unique")
    if answer.scientific_name.astype(str).nunique()!=EXPECTED_TAXA:
        raise ValueError("v5 answer coordinate artifact does not cover exact 50 taxa")
    answer["longitude"]=pd.to_numeric(answer.longitude,errors="raise").astype(float)
    answer["latitude"]=pd.to_numeric(answer.latitude,errors="raise").astype(float)
    locations=(answer[["longitude","latitude"]].drop_duplicates()
               .sort_values(["longitude","latitude"],kind="mergesort").reset_index(drop=True))
    locations.insert(0,"location_id",np.arange(len(locations),dtype=np.int64))
    index=answer.merge(locations,on=["longitude","latitude"],how="left",validate="many_to_one")
    index["location_id"]=pd.to_numeric(index.location_id,errors="raise").astype("int64")
    return index,locations


def _location_sha(frame: pd.DataFrame)->str:
    c=frame[["location_id","longitude","latitude"]].copy()
    c["location_id"]=pd.to_numeric(c.location_id,errors="raise").astype("int64")
    return hashlib.sha256(
        c.to_csv(index=False,float_format="%.17g",lineterminator="\n").encode("utf-8")
    ).hexdigest()


def _spec_map(process_registry_path,chelsa_manifest_path):
    specs,_=build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    return {s.predictor:s for s in specs}


def extract_answer_chelsa(
    *,predictor,answer_path,process_registry_path,chelsa_manifest_path,output_dir
)->dict:
    _,locations=prepare_answer_locations(answer_path)
    by=_spec_map(process_registry_path,chelsa_manifest_path)
    predictor=str(predictor)
    if predictor not in by or by[predictor].source=="SoilGrids":
        raise ValueError("v5 sealed CHELSA job received non-CHELSA predictor")
    from sdmr.data.raster import extract_raster_values
    featured,provenance=extract_raster_values(
        locations,[by[predictor]],lon_col="longitude",lat_col="latitude",
        checksum_local_files=False,
    )
    part=featured[["location_id",predictor]].copy()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    fp=out/"feature.parquet";pp=out/"provenance.csv";mp=out/"metadata.json"
    part.to_parquet(fp,index=False);provenance.to_csv(pp,index=False)
    meta={
      "program":PROGRAM,"stage":"answer_feature_extraction",
      "predictor":predictor,"source_family":"CHELSA",
      "location_rows":int(len(part)),"location_index_sha256":_location_sha(locations),
      "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
      "answer_check_features_read":True,"model_refit_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta


def extract_answer_soil_shard(
    *,predictor,shard_index,shard_count,answer_path,process_registry_path,
    chelsa_manifest_path,output_dir
)->dict:
    predictor=str(predictor)
    if predictor not in SOIL_PREDICTORS or int(shard_count)!=SOIL_SHARD_COUNT:
        raise ValueError("v5 sealed SoilGrids shard contract changed")
    _,locations=prepare_answer_locations(answer_path)
    start,stop=spatial_shard_bounds(len(locations),int(shard_index),int(shard_count))
    shard=locations.iloc[start:stop].copy().reset_index(drop=True)
    spec=_spec_map(process_registry_path,chelsa_manifest_path)[predictor]
    if spec.source!="SoilGrids":
        raise ValueError("v5 sealed SoilGrids source changed")
    from sdmr.data.raster import extract_raster_values
    featured,provenance=extract_raster_values(
        shard,[spec],lon_col="longitude",lat_col="latitude",checksum_local_files=False
    )
    part=featured[["location_id",predictor]].copy()
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    fp=out/"feature.parquet";pp=out/"provenance.csv";mp=out/"metadata.json"
    part.to_parquet(fp,index=False);provenance.to_csv(pp,index=False)
    meta={
      "program":PROGRAM,"stage":"answer_feature_extraction",
      "predictor":predictor,"source_family":"SoilGrids",
      "shard_index":int(shard_index),"shard_count":SOIL_SHARD_COUNT,
      "start_row":int(start),"stop_row":int(stop),"shard_rows":int(len(part)),
      "full_location_rows":int(len(locations)),"location_index_sha256":_location_sha(locations),
      "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
      "answer_check_features_read":True,"model_refit_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta


def assemble_answer_soil(
    *,parts_root,answer_path,output_dir
)->dict:
    _,locations=prepare_answer_locations(answer_path)
    locsha=_location_sha(locations)
    metas=sorted(Path(parts_root).rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    expected=len(SOIL_PREDICTORS)*SOIL_SHARD_COUNT
    if len(metadata)!=expected:
        raise RuntimeError(f"expected {expected} v5 sealed SoilGrids shards; found {len(metadata)}")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for predictor in SOIL_PREDICTORS:
        rows=[m for m in metadata if m.get("predictor")==predictor]
        by={int(m["shard_index"]):m for m in rows}
        if set(by)!=set(range(SOIL_SHARD_COUNT)):
            raise RuntimeError(f"incomplete sealed SoilGrids shard set: {predictor}")
        frames=[];provs=[]
        for idx in range(SOIL_SHARD_COUNT):
            meta=by[idx]
            if meta.get("location_index_sha256")!=locsha:
                raise RuntimeError(f"sealed SoilGrids location fingerprint drift: {predictor}/{idx}")
            mp=next(
                p for p in metas
                if json.loads(p.read_text()).get("predictor")==predictor
                and int(json.loads(p.read_text())["shard_index"])==idx
            )
            fp=mp.with_name("feature.parquet");pp=mp.with_name("provenance.csv")
            if _sha256(fp)!=meta["feature_sha256"] or _sha256(pp)!=meta["provenance_sha256"]:
                raise RuntimeError(f"sealed SoilGrids SHA mismatch: {predictor}/{idx}")
            frames.append(pd.read_parquet(fp));provs.append(pd.read_csv(pp))
        f=pd.concat(frames,ignore_index=True).sort_values("location_id",kind="mergesort").reset_index(drop=True)
        if f.location_id.astype("int64").tolist()!=locations.location_id.astype("int64").tolist():
            raise RuntimeError(f"sealed SoilGrids shard coverage not exact: {predictor}")
        prov=pd.concat(provs,ignore_index=True).drop_duplicates()
        if len(prov)!=1:
            raise RuntimeError(f"sealed SoilGrids provenance differs across shards: {predictor}")
        d=out/predictor;d.mkdir(parents=True,exist_ok=True)
        fp=d/"feature.parquet";pp=d/"provenance.csv";mp=d/"metadata.json"
        f.to_parquet(fp,index=False);prov.to_csv(pp,index=False)
        meta={
          "program":PROGRAM,"stage":"answer_feature_extraction",
          "predictor":predictor,"source_family":"SoilGrids",
          "location_rows":int(len(f)),"location_index_sha256":locsha,
          "feature_sha256":_sha256(fp),"provenance_sha256":_sha256(pp),
          "answer_check_features_read":True,"model_refit_performed":False,
          "spatial_shards":SOIL_SHARD_COUNT,
        }
        mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return {"program":PROGRAM,"status":"sealed_soil_feature_assembly_passed","location_rows":len(locations)}


def apply_structural_decoding(features: pd.DataFrame):
    out=features.copy();ledger=[]
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


def aggregate_answer_features(
    *,parts_root,answer_path,process_registry_path,output_dir
)->dict:
    answer_index,locations=prepare_answer_locations(answer_path)
    predictors=tuple(pd.read_csv(process_registry_path).predictor.astype(str))
    if len(predictors)!=EXPECTED_PREDICTORS or len(set(predictors))!=EXPECTED_PREDICTORS:
        raise ValueError("v5 sealed predictor universe changed")
    metas=sorted(Path(parts_root).rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    by={str(m["predictor"]):m for m in metadata}
    if len(metadata)!=EXPECTED_PREDICTORS or set(by)!=set(predictors):
        raise RuntimeError("v5 sealed feature predictor set changed")
    locsha=_location_sha(locations)
    loc=locations[["location_id"]].copy().set_index("location_id")
    provs=[]
    for predictor in predictors:
        meta=by[predictor]
        if meta.get("location_index_sha256")!=locsha or int(meta.get("location_rows",-1))!=len(locations):
            raise RuntimeError(f"sealed feature location fingerprint changed: {predictor}")
        if meta.get("answer_check_features_read") is not True or meta.get("model_refit_performed") is not False:
            raise RuntimeError(f"sealed feature information boundary crossed: {predictor}")
        mp=next(p for p in metas if json.loads(p.read_text()).get("predictor")==predictor)
        fp=mp.with_name("feature.parquet");pp=mp.with_name("provenance.csv")
        if _sha256(fp)!=meta["feature_sha256"] or _sha256(pp)!=meta["provenance_sha256"]:
            raise RuntimeError(f"sealed feature part SHA mismatch: {predictor}")
        f=pd.read_parquet(fp)
        if list(f.columns)!=["location_id",predictor]:
            raise RuntimeError(f"sealed feature columns changed: {predictor}")
        f["location_id"]=pd.to_numeric(f.location_id,errors="raise").astype("int64")
        loc[predictor]=pd.to_numeric(f.set_index("location_id")[predictor].reindex(loc.index),errors="coerce")
        provs.append(pd.read_csv(pp))
    loc=loc.reset_index()
    decoded,ledger=apply_structural_decoding(loc)
    complete=set(decoded.loc[decoded[list(predictors)].notna().all(axis=1),"location_id"].astype(int))
    answer_index=answer_index.copy()
    answer_index["complete_case"]=answer_index.location_id.astype(int).isin(complete)
    per=(answer_index.groupby("scientific_name")
         .agg(answer_rows=("occurrence_id","size"),complete_answer_rows=("complete_case","sum"))
         .reset_index())

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    lp=out/"answer_location_features_v5.parquet"
    ip=out/"answer_occurrence_feature_index_v5.csv"
    dp=out/"answer_source_decoding_ledger_v5.csv"
    pp=out/"answer_raster_provenance_v5.csv"
    sp=out/"answer_feature_summary_v5.csv"
    decoded.to_parquet(lp,index=False);answer_index.to_csv(ip,index=False)
    ledger.to_csv(dp,index=False);pd.concat(provs,ignore_index=True).to_csv(pp,index=False)
    per.to_csv(sp,index=False)
    result={
      "program":PROGRAM,"stage":"answer_feature_extraction",
      "status":"sealed_answer_features_materialized",
      "taxon_count":int(per.shape[0]),
      "answer_occurrence_rows":int(len(answer_index)),
      "complete_answer_occurrence_rows":int(answer_index.complete_case.sum()),
      "taxa_with_zero_complete_answer_rows":int(per.complete_answer_rows.eq(0).sum()),
      "location_features_sha256":_sha256(lp),"answer_index_sha256":_sha256(ip),
      "decoding_ledger_sha256":_sha256(dp),"provenance_sha256":_sha256(pp),
      "answer_check_features_read":True,"model_refit_performed":False,
      "next_gate":"score_frozen_routes_once_and_apply_EMP_A_to_EMP_F",
    }
    (out/"answer_feature_result_v5.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result


def _find_one(root: Path, name: str)->Path:
    hits=list(root.rglob(name))
    if len(hits)!=1:
        raise RuntimeError(f"expected exactly one {name} under {root}; found {len(hits)}")
    return hits[0]


def _as_bool(series: pd.Series)->pd.Series:
    if series.dtype==bool:
        return series
    vals=series.astype(str).str.strip().str.lower()
    if not vals.isin({"true","false"}).all():
        raise ValueError("boolean column contains non-boolean values")
    return vals.eq("true")


def _predict_model(spec: dict, parent: Path, frame: pd.DataFrame):
    import joblib
    if spec.get("available") is not True:
        return None
    predictors=tuple(str(x) for x in spec.get("predictors",[]))
    model_file=spec.get("model_file")
    if not predictors or not model_file:
        return None
    path=parent/str(model_file)
    if _sha256(path)!=spec.get("model_sha256"):
        raise RuntimeError(f"frozen model SHA mismatch: {path}")
    x=frame.loc[:,list(predictors)].to_numpy(float)
    if not np.isfinite(x).all():
        raise RuntimeError("non-finite row passed sealed complete-case filter")
    model=joblib.load(path)
    return np.asarray(model.predict_proba(x)[:,1],dtype=float)


def _taxon_route_scores(
    *,taxon,answer_index,answer_locations,bg_index,bg_locations,model_receipt_path
)->dict:
    receipt=json.loads(Path(model_receipt_path).read_text(encoding="utf-8"))
    if str(receipt.get("scientific_name"))!=str(taxon):
        raise RuntimeError("taxon model receipt name mismatch")
    parent=Path(model_receipt_path).parent

    ans_idx=answer_index.loc[
        answer_index.scientific_name.astype(str).eq(str(taxon))
        & _as_bool(answer_index.complete_case)
    ].copy()
    bg_idx=bg_index.loc[
        bg_index.scientific_name.astype(str).eq(str(taxon))
        & _as_bool(bg_index.complete_case)
        & pd.to_numeric(bg_index.background_rank,errors="raise").astype(int).mod(5).eq(0)
    ].copy()
    ans=ans_idx.merge(answer_locations,on="location_id",how="left",validate="many_to_one")
    bg=bg_idx.merge(bg_locations,on="location_id",how="left",validate="many_to_one")
    eval_available=bool(len(ans)>=1 and len(bg)>=1)

    route_scores={}
    for route in ALL_ROUTES:
        spec=receipt["predictor_sets"][route]
        available=bool(eval_available and spec.get("available") is True)
        log_score=float("nan"); auc=float("nan")
        if available:
            p_occ=_predict_model(spec,parent,ans)
            p_bg=_predict_model(spec,parent,bg)
            if p_occ is None or p_bg is None:
                available=False
            else:
                y=np.concatenate([np.ones(len(p_occ),dtype=int),np.zeros(len(p_bg),dtype=int)])
                p=np.concatenate([p_occ,p_bg])
                log_score=float(_balanced_log_score(y,p))
                auc=float(roc_auc_score(y,p))
                if not (math.isfinite(log_score) and math.isfinite(auc)):
                    available=False
                    log_score=float("nan");auc=float("nan")
        route_scores[route]={
          "available":available,
          "log_score":log_score,
          "roc_auc":auc,
          "predictor_count":int(spec.get("predictor_count",0)),
        }

    a=route_scores["sdmr_process_first"]
    b=route_scores["matched_learner_flat_predictive_selector"]
    capacity=route_scores["full_46_flat_hgb"]
    primary_evaluable=bool(a["available"] and b["available"])
    capacity_evaluable=bool(a["available"] and capacity["available"])
    gain=float(a["log_score"]-b["log_score"]) if primary_evaluable else 0.0
    auc_diff=float(a["roc_auc"]-b["roc_auc"]) if primary_evaluable else float("nan")
    capacity_gain=float(a["log_score"]-capacity["log_score"]) if capacity_evaluable else 0.0
    capacity_auc_diff=(
        float(a["roc_auc"]-capacity["roc_auc"])
        if capacity_evaluable
        else float("nan")
    )
    return {
      "scientific_name":str(taxon),
      "answer_rows":int(len(ans_idx)),
      "evaluation_background_rows":int(len(bg_idx)),
      "primary_evaluable":primary_evaluable,
      "primary_gain":gain,
      "primary_auc_difference":auc_diff,
      "capacity_control_evaluable":capacity_evaluable,
      "capacity_control_gain":capacity_gain,
      "capacity_control_auc_difference":capacity_auc_diff,
      **{
        f"{route}__available":route_scores[route]["available"]
        for route in ALL_ROUTES
      },
      **{
        f"{route}__log_score":route_scores[route]["log_score"]
        for route in ALL_ROUTES
      },
      **{
        f"{route}__roc_auc":route_scores[route]["roc_auc"]
        for route in ALL_ROUTES
      },
    }


def _bootstrap_mean_ci(gains: np.ndarray)->tuple[float,float]:
    gains=np.asarray(gains,dtype=float)
    if gains.shape!=(EXPECTED_TAXA,) or not np.isfinite(gains).all():
        raise ValueError("EMP-B requires exactly 50 finite taxon gains")
    rng=np.random.default_rng(BOOTSTRAP_SEED)
    index=rng.integers(0,EXPECTED_TAXA,size=(BOOTSTRAP_REPLICATES,EXPECTED_TAXA))
    means=gains[index].mean(axis=1)
    lo,hi=np.quantile(means,[0.025,0.975])
    return float(lo),float(hi)


def abstention_integrity_violations(
    stable: pd.DataFrame,
    selected: pd.DataFrame,
) -> int:
    """Count fail-closed integrity violations on the exact final50 x 6 grid."""
    required={"scientific_name","process","stable_state","stable_sharp"}
    missing=required-set(stable.columns)
    if missing:
        return EXPECTED_TAXA*EXPECTED_PROCESSES

    names=tuple(selected.sort_values("selection_rank").scientific_name.astype(str))
    expected={(name,process) for name in names for process in DEFAULT_PLANT_PROCESSES}
    observed=list(zip(stable.scientific_name.astype(str),stable.process.astype(str),strict=True))
    observed_set=set(observed)

    violations=0
    violations+=len(observed)-len(observed_set)
    violations+=len(expected-observed_set)
    violations+=len(observed_set-expected)

    state=stable["stable_state"].astype(str)
    allowed_states={"replaceable","contributory","required","unresolved","unavailable"}
    violations+=int((~state.isin(allowed_states)).sum())

    sharp=_as_bool(stable["stable_sharp"])
    invalid_abstention=(
        state.isin({"unresolved","unavailable"})
        & sharp
    )
    invalid_sharp_flag=(
        state.isin({"replaceable","contributory","required"})
        & (~sharp)
    )
    violations+=int(invalid_abstention.sum())
    violations+=int(invalid_sharp_flag.sum())
    return int(violations)


def capacity_filtering_claim_supported(
    evaluable: Sequence[bool],
    bootstrap_lower: float,
) -> bool:
    """Require the exact 50-taxon capacity comparison before a filtering claim."""
    flags=np.asarray(tuple(evaluable),dtype=bool)
    if len(flags)!=EXPECTED_TAXA:
        raise ValueError("capacity-control evaluability denominator must remain exactly 50")
    lower=float(bootstrap_lower)
    return bool(flags.all() and math.isfinite(lower) and lower>0.0)


def score_and_promote(
    *,
    selected_path,
    answer_feature_root,
    model_feature_root,
    model_pool_root,
    sealed_contract_path,
    output_dir,
)->dict:
    validate_contract(sealed_contract_path)
    selected=load_selected(selected_path)
    ans_root=Path(answer_feature_root)
    feature_root=Path(model_feature_root)
    model_root=Path(model_pool_root)

    answer_result=json.loads((ans_root/"answer_feature_result_v5.json").read_text())
    if answer_result.get("status")!="sealed_answer_features_materialized":
        raise ValueError("sealed answer features are not frozen")
    if answer_result.get("model_refit_performed") is not False:
        raise ValueError("sealed answer feature stage refit a model")
    answer_locations=pd.read_parquet(ans_root/"answer_location_features_v5.parquet")
    answer_index=pd.read_csv(ans_root/"answer_occurrence_feature_index_v5.csv")

    feature_result=json.loads((feature_root/"feature_gate_result_v5.json").read_text())
    if feature_result.get("status")!="v5_feature_gate_passed":
        raise ValueError("v5 scoring requires passing model-pool feature gate")
    bg_locations=pd.read_parquet(feature_root/"location_features_v5.parquet")
    bg_index=pd.read_csv(feature_root/"background_300km_feature_index_v5.csv")

    pool_result_path=_find_one(model_root,"model_pool_freeze_result.json")
    pool_result=json.loads(pool_result_path.read_text())
    if pool_result.get("status")!="model_pool_states_and_comparator_sets_frozen":
        raise ValueError("v5 model-pool artifact is not frozen")
    if pool_result.get("answer_check_accessed") is not False:
        raise ValueError("v5 model-pool artifact already accessed answer-check")

    receipts=sorted(model_root.rglob("taxon_model_freeze.json"))
    if len(receipts)!=EXPECTED_TAXA:
        raise RuntimeError(f"expected 50 taxon model receipts; found {len(receipts)}")
    by_taxon={}
    for path in receipts:
        r=json.loads(path.read_text())
        by_taxon[str(r["scientific_name"])]=path
    if set(by_taxon)!=set(selected.scientific_name.astype(str)):
        raise RuntimeError("frozen taxon model set differs from final50")

    rows=[]
    for row in selected.itertuples(index=False):
        scores=_taxon_route_scores(
            taxon=str(row.scientific_name),
            answer_index=answer_index,
            answer_locations=answer_locations,
            bg_index=bg_index,
            bg_locations=bg_locations,
            model_receipt_path=by_taxon[str(row.scientific_name)],
        )
        scores["selection_rank"]=int(row.selection_rank)
        rows.append(scores)
    taxon=pd.DataFrame(rows).sort_values("selection_rank").reset_index(drop=True)
    if len(taxon)!=EXPECTED_TAXA:
        raise RuntimeError("v5 sealed evaluation denominator changed")

    gains=taxon.primary_gain.to_numpy(float)
    mean_gain=float(np.mean(gains))
    boot_lo,boot_hi=_bootstrap_mean_ci(gains)
    all_evaluable=bool(taxon.primary_evaluable.astype(bool).all())
    auc_values=pd.to_numeric(taxon.primary_auc_difference,errors="coerce")
    mean_auc_diff=float(auc_values.mean()) if all_evaluable and auc_values.notna().all() else float("nan")

    capacity_gains=pd.to_numeric(taxon.capacity_control_gain,errors="raise").to_numpy(float)
    capacity_mean_gain=float(np.mean(capacity_gains))
    capacity_boot_lo,capacity_boot_hi=_bootstrap_mean_ci(capacity_gains)
    capacity_all_evaluable=bool(taxon.capacity_control_evaluable.astype(bool).all())
    capacity_auc_values=pd.to_numeric(taxon.capacity_control_auc_difference,errors="coerce")
    capacity_mean_auc_diff=(
        float(capacity_auc_values.mean())
        if capacity_all_evaluable and capacity_auc_values.notna().all()
        else float("nan")
    )
    capacity_filtering_advantage_supported=bool(
        capacity_all_evaluable and capacity_boot_lo>0.0
    )

    stable_path=_find_one(model_root,"stable_states_all_taxa.csv")
    stable=pd.read_csv(stable_path)
    expected_cells=EXPECTED_TAXA*EXPECTED_PROCESSES
    stable_sharp=_as_bool(stable["stable_sharp"]) if "stable_sharp" in stable else pd.Series([],dtype=bool)
    abstention_violation=abstention_integrity_violations(stable,selected)
    stable_fraction=(
        float(stable_sharp.sum()/expected_cells)
        if len(stable)==expected_cells and abstention_violation==0
        else 0.0
    )

    emp_a=bool(mean_gain>=EMP_A_MINIMUM)
    emp_b=bool(boot_lo>0.0)
    emp_c=bool(all_evaluable and math.isfinite(mean_auc_diff) and mean_auc_diff>=EMP_C_MINIMUM_AUC_DIFFERENCE)
    emp_d=bool(stable_fraction>=EMP_D_MINIMUM_STABLE_FRACTION)
    emp_e=bool(abstention_violation==0)
    emp_f=bool(len(taxon)==EXPECTED_TAXA and taxon.selection_rank.tolist()==list(range(1,EXPECTED_TAXA+1)))
    promotion=bool(emp_a and emp_b and emp_c and emp_d and emp_e and emp_f)

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    taxon_path=out/"taxon_sealed_scores_v5.csv"
    taxon.to_csv(taxon_path,index=False)
    result={
      "program":PROGRAM,"stage":"sealed_scoring_and_promotion",
      "status":"promotion_passed" if promotion else "promotion_failed",
      "taxon_count":EXPECTED_TAXA,
      "primary_evaluable_taxa":int(taxon.primary_evaluable.sum()),
      "primary_unavailable_taxa":int((~taxon.primary_evaluable).sum()),
      "mean_primary_balanced_log_score_gain":mean_gain,
      "bootstrap_95pct_lower":boot_lo,"bootstrap_95pct_upper":boot_hi,
      "mean_primary_auc_difference":mean_auc_diff if math.isfinite(mean_auc_diff) else None,
      "capacity_control_evaluable_taxa":int(taxon.capacity_control_evaluable.sum()),
      "capacity_control_unavailable_taxa":int((~taxon.capacity_control_evaluable).sum()),
      "mean_capacity_control_balanced_log_score_gain":capacity_mean_gain,
      "capacity_control_bootstrap_95pct_lower":capacity_boot_lo,
      "capacity_control_bootstrap_95pct_upper":capacity_boot_hi,
      "mean_capacity_control_auc_difference":(
          capacity_mean_auc_diff if math.isfinite(capacity_mean_auc_diff) else None
      ),
      "capacity_control_filtering_advantage_supported":capacity_filtering_advantage_supported,
      "capacity_control_affects_emp_promotion":False,
      "stable_process_fraction":stable_fraction,
      "abstention_integrity_violations":int(abstention_violation),
      "EMP_A_pass":emp_a,"EMP_B_pass":emp_b,"EMP_C_pass":emp_c,
      "EMP_D_pass":emp_d,"EMP_E_pass":emp_e,"EMP_F_pass":emp_f,
      "strict_promotion_pass":promotion,
      "taxon_scores_sha256":_sha256(taxon_path),
      "answer_check_accessed":True,"answer_check_features_read":True,
      "model_refit_performed":False,"post_opening_reselection_performed":False,
    }
    (out/"sealed_promotion_result_v5.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)

    q=sub.add_parser("occurrence-chunk")
    q.add_argument("--selected",required=True);q.add_argument("--outer-split",required=True)
    q.add_argument("--chunk-index",type=int,required=True);q.add_argument("--chunk-count",type=int,default=EXPECTED_CHUNKS)
    q.add_argument("--output-dir",required=True)

    q=sub.add_parser("occurrence-aggregate")
    q.add_argument("--selected",required=True);q.add_argument("--outer-split",required=True)
    q.add_argument("--parts-root",required=True);q.add_argument("--output-dir",required=True)

    q=sub.add_parser("chelsa")
    q.add_argument("--predictor",required=True);q.add_argument("--answer",required=True)
    q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True)
    q.add_argument("--output-dir",required=True)

    q=sub.add_parser("soil-shard")
    q.add_argument("--predictor",required=True);q.add_argument("--shard-index",type=int,required=True)
    q.add_argument("--shard-count",type=int,default=SOIL_SHARD_COUNT);q.add_argument("--answer",required=True)
    q.add_argument("--process-registry",required=True);q.add_argument("--chelsa-manifest",required=True)
    q.add_argument("--output-dir",required=True)

    q=sub.add_parser("soil-assemble")
    q.add_argument("--parts-root",required=True);q.add_argument("--answer",required=True);q.add_argument("--output-dir",required=True)

    q=sub.add_parser("feature-aggregate")
    q.add_argument("--parts-root",required=True);q.add_argument("--answer",required=True)
    q.add_argument("--process-registry",required=True);q.add_argument("--output-dir",required=True)

    q=sub.add_parser("score")
    q.add_argument("--selected",required=True);q.add_argument("--answer-feature-root",required=True)
    q.add_argument("--model-feature-root",required=True);q.add_argument("--model-pool-root",required=True)
    q.add_argument("--sealed-contract",required=True);q.add_argument("--output-dir",required=True)

    a=p.parse_args()
    if a.command=="occurrence-chunk":
        result=materialize_answer_chunk(
            selected_path=a.selected,outer_split_path=a.outer_split,
            chunk_index=a.chunk_index,chunk_count=a.chunk_count,output_dir=a.output_dir)
    elif a.command=="occurrence-aggregate":
        result=aggregate_answer_coordinates(
            selected_path=a.selected,outer_split_path=a.outer_split,
            parts_root=a.parts_root,output_dir=a.output_dir)
    elif a.command=="chelsa":
        result=extract_answer_chelsa(
            predictor=a.predictor,answer_path=a.answer,
            process_registry_path=a.process_registry,chelsa_manifest_path=a.chelsa_manifest,
            output_dir=a.output_dir)
    elif a.command=="soil-shard":
        result=extract_answer_soil_shard(
            predictor=a.predictor,shard_index=a.shard_index,shard_count=a.shard_count,
            answer_path=a.answer,process_registry_path=a.process_registry,
            chelsa_manifest_path=a.chelsa_manifest,output_dir=a.output_dir)
    elif a.command=="soil-assemble":
        result=assemble_answer_soil(parts_root=a.parts_root,answer_path=a.answer,output_dir=a.output_dir)
    elif a.command=="feature-aggregate":
        result=aggregate_answer_features(
            parts_root=a.parts_root,answer_path=a.answer,
            process_registry_path=a.process_registry,output_dir=a.output_dir)
    else:
        result=score_and_promote(
            selected_path=a.selected,answer_feature_root=a.answer_feature_root,
            model_feature_root=a.model_feature_root,model_pool_root=a.model_pool_root,
            sealed_contract_path=a.sealed_contract,output_dir=a.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
