"""All-46 usable-support eligibility runtime for fresh empirical v4.

This stage runs before v4 final50 selection. It may open raster values in memory
for the 90 predeclared candidates' model-pool occurrences and frozen 300-km
backgrounds, but it persists only boolean usable-support bits and candidate-level
support counts. Answer-check coordinates/features and model fitting remain
forbidden.

For the six structural CHELSA predictors, usability includes only the six
predeclared deterministic source-decoding conditions frozen before candidate
selection. No numeric environmental values are written to artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.data.raster import extract_raster_values
from sdmr.process_id.fresh.features import build_frozen_layer_specs


PROGRAM="sdmr-fresh-empirical-v4-all46-support-runtime"
EXPECTED_CANDIDATES=90
EXPECTED_FINAL=50
EXPECTED_PREDICTORS=46
EXPECTED_CHELSA=42
EXPECTED_SOIL=4
SOIL_SHARD_COUNT=32
BACKGROUND_ROWS_PER_CANDIDATE=5000
MODEL_MIN_FRACTION=0.80
MODEL_MIN_ROWS=50
BACKGROUND_MIN_ROWS=4000
PRIMARY_M_KM=300

SOIL_PREDICTORS=(
    "sg_phh2o_0_5",
    "sg_clay_0_5",
    "sg_soc_0_5",
    "sg_nitrogen_0_5",
)

STRUCTURAL_RULES={
    "fcf":("bio6","gt",0.0),
    "swe":("scd","eq",0.0),
    "fgd":("gsl","eq",365.0),
    "lgd":("gsl","eq",365.0),
    "gdgfgd5":("ngd5","eq",365.0),
    "gdgfgd10":("ngd10","eq",365.0),
}


def _sha256(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _location_sha(frame: pd.DataFrame)->str:
    required=["location_id","longitude","latitude"]
    if list(frame.columns)!=required:
        raise ValueError("v4 support location-index columns changed")
    canonical=frame.copy()
    canonical["location_id"]=pd.to_numeric(
        canonical["location_id"],errors="raise"
    ).astype("int64")
    payload=canonical.to_csv(
        index=False,float_format="%.17g",lineterminator="\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_candidates(path: str|Path)->pd.DataFrame:
    df=pd.read_csv(path)
    required={
        "candidate_rank","scientific_name","family","genus","selection_hash"
    }
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"v4 candidate roster missing columns: {sorted(missing)}")
    if (
        len(df)!=EXPECTED_CANDIDATES
        or df["scientific_name"].astype(str).nunique()!=EXPECTED_CANDIDATES
    ):
        raise ValueError("v4 all46 support requires exactly 90 unique candidates")
    ranks=sorted(
        pd.to_numeric(df["candidate_rank"],errors="raise").astype(int).tolist()
    )
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("v4 candidate ranks must be exactly 1..90")
    df["scientific_name"]=df["scientific_name"].astype(str).str.strip()
    if df["scientific_name"].eq("").any():
        raise ValueError("v4 candidate names must be non-empty")
    return df.sort_values("candidate_rank").reset_index(drop=True)


def validate_contract(path: str|Path)->dict:
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program")!="sdmr-fresh-empirical-v4-all46-support":
        raise ValueError("wrong v4 all46-support design program")
    if c.get("status")!="design_frozen_before_v4_candidate_selection":
        raise ValueError("v4 all46-support design was not frozen before selection")
    block=c.get("all46_support_eligibility",{})
    if int(block.get("predictor_count",-1))!=EXPECTED_PREDICTORS:
        raise ValueError("v4 support predictor denominator changed")
    if block.get("persist_numeric_environmental_values") is not False:
        raise ValueError("v4 support numeric persistence became allowed")
    if block.get("answer_check_support_read") is not False:
        raise ValueError("v4 support answer-check access became allowed")
    if block.get("final_selection")!="first_50_eligible_in_frozen_candidate_order":
        raise ValueError("v4 final-selection rule changed")
    if int(block.get("final_taxa",-1))!=EXPECTED_FINAL:
        raise ValueError("v4 final taxon denominator changed")
    gate=block.get("gate",{})
    if float(gate.get("model_pool_minimum_joint_usable_fraction",-1))!=MODEL_MIN_FRACTION:
        raise ValueError("v4 model-pool support fraction changed")
    if int(gate.get("model_pool_minimum_joint_usable_rows",-1))!=MODEL_MIN_ROWS:
        raise ValueError("v4 model-pool support rows changed")
    if int(gate.get("background_denominator_rows",-1))!=BACKGROUND_ROWS_PER_CANDIDATE:
        raise ValueError("v4 background denominator changed")
    if int(gate.get("background_minimum_joint_usable_rows",-1))!=BACKGROUND_MIN_ROWS:
        raise ValueError("v4 background support gate changed")
    rules=block.get("structural_decoding_rules",[])
    expected=[
        ("fcf","bio6"),
        ("swe","scd"),
        ("fgd","gsl"),
        ("lgd","gsl"),
        ("gdgfgd5","ngd5"),
        ("gdgfgd10","ngd10"),
    ]
    if [(r.get("predictor"),r.get("companion")) for r in rules]!=expected:
        raise ValueError("v4 structural support-rule set changed")
    return c


def prepare_support_points(
    *,
    candidate_path: str|Path,
    model_pool_path: str|Path,
    background_path: str|Path,
)->tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    candidates=load_candidates(candidate_path)
    taxa=set(candidates["scientific_name"].astype(str))

    model=pd.read_csv(model_pool_path)
    required_m={"scientific_name","occurrence_id","longitude","latitude"}
    missing=required_m-set(model.columns)
    if missing:
        raise ValueError(f"v4 model-pool artifact missing columns: {sorted(missing)}")
    if set(model["scientific_name"].astype(str))!=taxa:
        raise ValueError("v4 model-pool does not cover exact candidate90")
    if model["occurrence_id"].astype(str).duplicated().any():
        raise ValueError("v4 model-pool occurrence IDs must be unique")

    bg=pd.read_csv(background_path)
    required_b={
        "scientific_name","m_km","background_rank","longitude","latitude"
    }
    missing=required_b-set(bg.columns)
    if missing:
        raise ValueError(f"v4 background artifact missing columns: {sorted(missing)}")
    bg=bg.loc[
        pd.to_numeric(bg["m_km"],errors="raise").astype(int).eq(PRIMARY_M_KM)
    ].copy()
    if set(bg["scientific_name"].astype(str))!=taxa:
        raise ValueError("v4 primary background does not cover exact candidate90")
    per=bg.groupby(bg["scientific_name"].astype(str)).size()
    if (
        len(per)!=EXPECTED_CANDIDATES
        or not per.eq(BACKGROUND_ROWS_PER_CANDIDATE).all()
    ):
        raise ValueError("v4 support requires exactly 5000 background rows per candidate")

    model_index=model[
        ["scientific_name","occurrence_id","longitude","latitude"]
    ].copy()
    model_index.insert(1,"point_role","model_pool")
    model_index["point_id"]=model_index["occurrence_id"].astype(str)

    bg_index=bg[
        ["scientific_name","background_rank","longitude","latitude"]
    ].copy()
    bg_index.insert(1,"point_role","background_300km")
    bg_index["point_id"]=(
        bg_index["scientific_name"].astype(str)
        +"|bg300|"
        +pd.to_numeric(
            bg_index["background_rank"],errors="raise"
        ).astype(int).astype(str)
    )
    if bg_index["point_id"].duplicated().any():
        raise ValueError("v4 background point IDs must be unique")

    combined=pd.concat(
        [
            model_index[
                ["scientific_name","point_role","point_id","longitude","latitude"]
            ],
            bg_index[
                ["scientific_name","point_role","point_id","longitude","latitude"]
            ],
        ],
        ignore_index=True,
    )
    combined["longitude"]=pd.to_numeric(
        combined["longitude"],errors="raise"
    ).astype(float)
    combined["latitude"]=pd.to_numeric(
        combined["latitude"],errors="raise"
    ).astype(float)
    if not np.isfinite(
        combined[["longitude","latitude"]].to_numpy(float)
    ).all():
        raise ValueError("v4 support coordinates must be finite")

    locations=(
        combined[["longitude","latitude"]]
        .drop_duplicates()
        .sort_values(["longitude","latitude"],kind="mergesort")
        .reset_index(drop=True)
    )
    locations.insert(0,"location_id",np.arange(len(locations),dtype=np.int64))
    model_index=model_index.merge(
        locations,on=["longitude","latitude"],how="left",validate="many_to_one"
    )
    bg_index=bg_index.merge(
        locations,on=["longitude","latitude"],how="left",validate="many_to_one"
    )
    model_index["location_id"]=pd.to_numeric(
        model_index["location_id"],errors="raise"
    ).astype("int64")
    bg_index["location_id"]=pd.to_numeric(
        bg_index["location_id"],errors="raise"
    ).astype("int64")
    return candidates,model_index,bg_index,locations


def spatial_shard_bounds(
    n_rows:int,shard_index:int,shard_count:int
)->tuple[int,int]:
    if n_rows<1 or shard_count<1 or not 0<=shard_index<shard_count:
        raise ValueError("invalid v4 support shard bounds")
    start=(n_rows*shard_index)//shard_count
    stop=(n_rows*(shard_index+1))//shard_count
    if stop<=start:
        raise ValueError("empty v4 support shard")
    return start,stop


def _specs(
    *,
    process_registry_path: str|Path,
    chelsa_manifest_path: str|Path,
):
    specs,registry=build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    if len(specs)!=EXPECTED_PREDICTORS:
        raise ValueError("v4 support layer denominator changed")
    by={spec.predictor:spec for spec in specs}
    if len(by)!=EXPECTED_PREDICTORS:
        raise ValueError("v4 support predictor names are not unique")
    return by,registry


def _usable_from_values(
    *,
    predictor:str,
    featured:pd.DataFrame,
)->np.ndarray:
    values=pd.to_numeric(featured[predictor],errors="coerce")
    usable=values.notna().to_numpy(bool)
    if predictor not in STRUCTURAL_RULES:
        return usable
    companion,operator,condition=STRUCTURAL_RULES[predictor]
    companion_values=pd.to_numeric(featured[companion],errors="coerce")
    if operator=="eq":
        decoded=values.isna() & companion_values.eq(condition)
    elif operator=="gt":
        decoded=values.isna() & companion_values.gt(condition)
    else:
        raise ValueError(f"unsupported structural support operator: {operator}")
    return (values.notna() | decoded).to_numpy(bool)


def extract_chelsa_support(
    *,
    predictor:str,
    candidate_path:str|Path,
    model_pool_path:str|Path,
    background_path:str|Path,
    process_registry_path:str|Path,
    chelsa_manifest_path:str|Path,
    output_dir:str|Path,
)->dict:
    predictor=str(predictor)
    candidates,model,bg,locations=prepare_support_points(
        candidate_path=candidate_path,
        model_pool_path=model_pool_path,
        background_path=background_path,
    )
    del candidates,model,bg
    specs,_=_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    if predictor not in specs or specs[predictor].source=="SoilGrids":
        raise ValueError("v4 CHELSA-support job received non-CHELSA predictor")
    layers=[specs[predictor]]
    if predictor in STRUCTURAL_RULES:
        companion=STRUCTURAL_RULES[predictor][0]
        layers.append(specs[companion])
    featured,_=extract_raster_values(
        locations,
        layers,
        lon_col="longitude",
        lat_col="latitude",
        checksum_local_files=False,
    )
    usable=_usable_from_values(predictor=predictor,featured=featured)
    support=pd.DataFrame(
        {
            "location_id":locations["location_id"].astype("int64"),
            "is_usable":usable.astype(bool),
        }
    )
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    sp=out/"support.parquet";mp=out/"metadata.json"
    support.to_parquet(sp,index=False)
    meta={
        "program":PROGRAM,
        "predictor":predictor,
        "source_family":"CHELSA",
        "location_rows":int(len(support)),
        "location_index_sha256":_location_sha(locations),
        "support_sha256":_sha256(sp),
        "usable_rows":int(support["is_usable"].sum()),
        "unusable_rows":int((~support["is_usable"]).sum()),
        "structural_rule_applied":predictor in STRUCTURAL_RULES,
        "persisted_information":"location_id_plus_boolean_usable_bit_only",
        "numeric_environmental_values_persisted":False,
        "answer_check_support_read":False,
        "model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta


def extract_soil_support_shard(
    *,
    predictor:str,
    shard_index:int,
    shard_count:int,
    candidate_path:str|Path,
    model_pool_path:str|Path,
    background_path:str|Path,
    process_registry_path:str|Path,
    chelsa_manifest_path:str|Path,
    output_dir:str|Path,
)->dict:
    predictor=str(predictor)
    if predictor not in SOIL_PREDICTORS:
        raise ValueError("v4 SoilGrids-support predictor outside frozen set")
    if int(shard_count)!=SOIL_SHARD_COUNT:
        raise ValueError("v4 SoilGrids-support shard count changed")
    candidates,model,bg,locations=prepare_support_points(
        candidate_path=candidate_path,
        model_pool_path=model_pool_path,
        background_path=background_path,
    )
    del candidates,model,bg
    start,stop=spatial_shard_bounds(
        len(locations),int(shard_index),int(shard_count)
    )
    shard=locations.iloc[start:stop].copy().reset_index(drop=True)
    specs,_=_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    spec=specs[predictor]
    if spec.source!="SoilGrids":
        raise ValueError("v4 SoilGrids-support source changed")
    featured,_=extract_raster_values(
        shard,
        [spec],
        lon_col="longitude",
        lat_col="latitude",
        checksum_local_files=False,
    )
    usable=pd.to_numeric(
        featured[predictor],errors="coerce"
    ).notna().to_numpy(bool)
    support=pd.DataFrame(
        {
            "location_id":shard["location_id"].astype("int64"),
            "is_usable":usable.astype(bool),
        }
    )
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    sp=out/"support.parquet";mp=out/"metadata.json"
    support.to_parquet(sp,index=False)
    meta={
        "program":PROGRAM,
        "predictor":predictor,
        "source_family":"SoilGrids",
        "shard_index":int(shard_index),
        "shard_count":SOIL_SHARD_COUNT,
        "start_row":int(start),
        "stop_row":int(stop),
        "shard_rows":int(len(support)),
        "full_location_rows":int(len(locations)),
        "location_index_sha256":_location_sha(locations),
        "support_sha256":_sha256(sp),
        "usable_rows":int(support["is_usable"].sum()),
        "unusable_rows":int((~support["is_usable"]).sum()),
        "persisted_information":"location_id_plus_boolean_usable_bit_only",
        "numeric_environmental_values_persisted":False,
        "answer_check_support_read":False,
        "model_fitting_performed":False,
    }
    mp.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta


def assemble_soil_support(
    *,
    parts_root:str|Path,
    candidate_path:str|Path,
    model_pool_path:str|Path,
    background_path:str|Path,
    output_dir:str|Path,
)->dict:
    _,_,_,locations=prepare_support_points(
        candidate_path=candidate_path,
        model_pool_path=model_pool_path,
        background_path=background_path,
    )
    locsha=_location_sha(locations)
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    expected=EXPECTED_SOIL*SOIL_SHARD_COUNT
    if len(metadata)!=expected:
        raise RuntimeError(
            f"expected {expected} v4 SoilGrids support shard metadata files; "
            f"found {len(metadata)}"
        )
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for predictor in SOIL_PREDICTORS:
        rows=[m for m in metadata if m.get("predictor")==predictor]
        byidx={int(m["shard_index"]):m for m in rows}
        if set(byidx)!=set(range(SOIL_SHARD_COUNT)):
            raise RuntimeError(
                f"incomplete v4 SoilGrids support shard set: {predictor}"
            )
        frames=[]
        for idx in range(SOIL_SHARD_COUNT):
            meta=byidx[idx]
            if meta.get("location_index_sha256")!=locsha:
                raise RuntimeError(
                    f"v4 support location fingerprint drift: {predictor}/{idx}"
                )
            if (
                meta.get("numeric_environmental_values_persisted") is not False
                or meta.get("answer_check_support_read") is not False
                or meta.get("model_fitting_performed") is not False
            ):
                raise RuntimeError(
                    f"v4 SoilGrids support boundary crossed: {predictor}/{idx}"
                )
            meta_path=next(
                p
                for p in metas
                if json.loads(p.read_text()).get("predictor")==predictor
                and int(json.loads(p.read_text())["shard_index"])==idx
            )
            sp=meta_path.with_name("support.parquet")
            if _sha256(sp)!=meta["support_sha256"]:
                raise RuntimeError(
                    f"v4 SoilGrids support shard SHA mismatch: {predictor}/{idx}"
                )
            frames.append(pd.read_parquet(sp))
        full=(
            pd.concat(frames,ignore_index=True)
            .sort_values("location_id",kind="mergesort")
            .reset_index(drop=True)
        )
        if (
            full["location_id"].astype("int64").tolist()
            != locations["location_id"].astype("int64").tolist()
        ):
            raise RuntimeError(
                f"v4 SoilGrids support coverage is not exact: {predictor}"
            )
        d=out/predictor;d.mkdir(parents=True,exist_ok=True)
        sp=d/"support.parquet";mp=d/"metadata.json"
        full.to_parquet(sp,index=False)
        final_meta={
            "program":PROGRAM,
            "predictor":predictor,
            "source_family":"SoilGrids",
            "location_rows":int(len(full)),
            "location_index_sha256":locsha,
            "support_sha256":_sha256(sp),
            "usable_rows":int(full["is_usable"].sum()),
            "unusable_rows":int((~full["is_usable"]).sum()),
            "spatial_shards":SOIL_SHARD_COUNT,
            "persisted_information":"location_id_plus_boolean_usable_bit_only",
            "numeric_environmental_values_persisted":False,
            "answer_check_support_read":False,
            "model_fitting_performed":False,
        }
        mp.write_text(json.dumps(final_meta,indent=2,sort_keys=True)+"\n")
    return {
        "program":PROGRAM,
        "status":"v4_soil_support_assembly_passed",
        "predictor_count":EXPECTED_SOIL,
        "location_rows":int(len(locations)),
        "numeric_environmental_values_persisted":False,
        "answer_check_support_read":False,
        "model_fitting_performed":False,
    }


def aggregate_support(
    *,
    parts_root:str|Path,
    candidate_path:str|Path,
    model_pool_path:str|Path,
    background_path:str|Path,
    contract_path:str|Path,
    output_dir:str|Path,
)->dict:
    contract=validate_contract(contract_path)
    del contract
    candidates,model,bg,locations=prepare_support_points(
        candidate_path=candidate_path,
        model_pool_path=model_pool_path,
        background_path=background_path,
    )
    locsha=_location_sha(locations)
    root=Path(parts_root)
    metas=sorted(root.rglob("metadata.json"))
    metadata=[json.loads(p.read_text()) for p in metas]
    if len(metadata)!=EXPECTED_PREDICTORS:
        raise RuntimeError(
            f"v4 support metadata denominator changed: {len(metadata)} != {EXPECTED_PREDICTORS}"
        )
    by={str(m["predictor"]):m for m in metadata}
    if len(by)!=EXPECTED_PREDICTORS:
        raise RuntimeError(
            f"v4 support predictor set changed: {len(by)} != {EXPECTED_PREDICTORS}"
        )
    expected_predictors=set(
        pd.read_csv(
            "configs/sdmr_fresh_empirical_process_registry_v1.csv"
        )["predictor"].astype(str)
    )
    if set(by)!=expected_predictors:
        raise RuntimeError("v4 support predictor names changed")

    joint=pd.DataFrame({"location_id":locations["location_id"].astype("int64")})
    predictor_summary=[]
    for predictor in sorted(by):
        meta=by[predictor]
        if (
            meta.get("location_index_sha256")!=locsha
            or int(meta.get("location_rows",-1))!=len(locations)
        ):
            raise RuntimeError(
                f"v4 support location fingerprint/denominator changed: {predictor}"
            )
        if (
            meta.get("numeric_environmental_values_persisted") is not False
            or meta.get("answer_check_support_read") is not False
            or meta.get("model_fitting_performed") is not False
        ):
            raise RuntimeError(f"v4 support boundary crossed: {predictor}")
        meta_path=next(
            p
            for p in metas
            if json.loads(p.read_text()).get("predictor")==predictor
        )
        sp=meta_path.with_name("support.parquet")
        if _sha256(sp)!=meta["support_sha256"]:
            raise RuntimeError(f"v4 support SHA mismatch: {predictor}")
        support=pd.read_parquet(sp)
        if list(support.columns)!=["location_id","is_usable"]:
            raise RuntimeError(f"v4 support columns changed: {predictor}")
        support["location_id"]=pd.to_numeric(
            support["location_id"],errors="raise"
        ).astype("int64")
        support=(
            support.sort_values("location_id",kind="mergesort")
            .reset_index(drop=True)
        )
        if (
            support["location_id"].tolist()
            != locations["location_id"].astype("int64").tolist()
        ):
            raise RuntimeError(f"v4 support row coverage changed: {predictor}")
        joint[predictor]=support["is_usable"].astype(bool).to_numpy()
        predictor_summary.append(
            {
                "predictor":predictor,
                "usable_rows":int(support["is_usable"].sum()),
                "unusable_rows":int((~support["is_usable"]).sum()),
            }
        )

    predictor_order=pd.read_csv(
        "configs/sdmr_fresh_empirical_process_registry_v1.csv"
    )["predictor"].astype(str).tolist()
    joint["joint_usable"]=joint[predictor_order].all(axis=1)

    model2=model.merge(
        joint[["location_id","joint_usable"]],
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    bg2=bg.merge(
        joint[["location_id","joint_usable"]],
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    rows=[]
    for taxon in candidates["scientific_name"].astype(str):
        m=model2.loc[model2["scientific_name"].astype(str).eq(taxon)]
        b=bg2.loc[bg2["scientific_name"].astype(str).eq(taxon)]
        m_usable=int(m["joint_usable"].sum())
        b_usable=int(b["joint_usable"].sum())
        m_fraction=float(m_usable/len(m)) if len(m) else 0.0
        eligible=(
            m_fraction>=MODEL_MIN_FRACTION
            and m_usable>=MODEL_MIN_ROWS
            and len(b)==BACKGROUND_ROWS_PER_CANDIDATE
            and b_usable>=BACKGROUND_MIN_ROWS
        )
        rows.append(
            {
                "scientific_name":taxon,
                "model_pool_rows":int(len(m)),
                "model_pool_joint_usable_rows":m_usable,
                "model_pool_joint_usable_fraction":m_fraction,
                "background_300km_rows":int(len(b)),
                "background_300km_joint_usable_rows":b_usable,
                "all46_support_eligible":bool(eligible),
                "answer_check_support_read":False,
                "numeric_environmental_values_persisted":False,
            }
        )
    audit=pd.DataFrame(rows)
    if len(audit)!=EXPECTED_CANDIDATES:
        raise RuntimeError("v4 support audit denominator changed")
    eligible=set(
        audit.loc[audit["all46_support_eligible"],"scientific_name"].astype(str)
    )
    ordered=candidates.loc[
        candidates["scientific_name"].astype(str).isin(eligible)
    ].copy()
    support_eligible_count=int(len(ordered))

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    ap=out/"candidate_all46_support_audit_v4.csv"
    pp=out/"predictor_support_summary_v4.csv"
    audit.to_csv(ap,index=False)
    pd.DataFrame(predictor_summary).to_csv(pp,index=False)

    result={
        "program":"sdmr-fresh-empirical-v4-all46-support",
        "candidate_count":EXPECTED_CANDIDATES,
        "support_eligible_count":support_eligible_count,
        "final_selected_count":0,
        "status":"terminal_unavailable_before_final50_freeze",
        "support_audit_sha256":_sha256(ap),
        "predictor_support_summary_sha256":_sha256(pp),
        "numeric_environmental_values_persisted":False,
        "answer_check_support_read":False,
        "model_fitting_performed":False,
        "taxon_replacement_performed":False,
        "predictor_deletion_performed":False,
        "threshold_relaxation_performed":False,
    }
    if support_eligible_count>=EXPECTED_FINAL:
        final=ordered.head(EXPECTED_FINAL).copy().reset_index(drop=True)
        final.insert(0,"selection_rank",range(1,EXPECTED_FINAL+1))
        final=final.merge(
            audit,
            on="scientific_name",
            how="left",
            validate="one_to_one",
        )
        fp=out/"selected_fresh_taxa_v4.csv"
        final.to_csv(fp,index=False)
        result.update(
            {
                "status":"final50_frozen_after_all46_support_eligibility",
                "final_selected_count":EXPECTED_FINAL,
                "selected_manifest_sha256":_sha256(fp),
            }
        )
    (out/"all46_support_selection_result_v4.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n"
    )
    return result


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)

    q=sub.add_parser("chelsa")
    q.add_argument("--predictor",required=True)
    q.add_argument("--candidates",required=True)
    q.add_argument("--model-pool",required=True)
    q.add_argument("--background",required=True)
    q.add_argument("--process-registry",required=True)
    q.add_argument("--chelsa-manifest",required=True)
    q.add_argument("--output-dir",required=True)

    q=sub.add_parser("soil-shard")
    q.add_argument("--predictor",required=True)
    q.add_argument("--shard-index",type=int,required=True)
    q.add_argument("--shard-count",type=int,default=SOIL_SHARD_COUNT)
    q.add_argument("--candidates",required=True)
    q.add_argument("--model-pool",required=True)
    q.add_argument("--background",required=True)
    q.add_argument("--process-registry",required=True)
    q.add_argument("--chelsa-manifest",required=True)
    q.add_argument("--output-dir",required=True)

    q=sub.add_parser("soil-assemble")
    q.add_argument("--parts-root",required=True)
    q.add_argument("--candidates",required=True)
    q.add_argument("--model-pool",required=True)
    q.add_argument("--background",required=True)
    q.add_argument("--output-dir",required=True)

    q=sub.add_parser("aggregate")
    q.add_argument("--parts-root",required=True)
    q.add_argument("--candidates",required=True)
    q.add_argument("--model-pool",required=True)
    q.add_argument("--background",required=True)
    q.add_argument("--contract",required=True)
    q.add_argument("--output-dir",required=True)

    a=p.parse_args()
    if a.command=="chelsa":
        result=extract_chelsa_support(
            predictor=a.predictor,
            candidate_path=a.candidates,
            model_pool_path=a.model_pool,
            background_path=a.background,
            process_registry_path=a.process_registry,
            chelsa_manifest_path=a.chelsa_manifest,
            output_dir=a.output_dir,
        )
    elif a.command=="soil-shard":
        result=extract_soil_support_shard(
            predictor=a.predictor,
            shard_index=a.shard_index,
            shard_count=a.shard_count,
            candidate_path=a.candidates,
            model_pool_path=a.model_pool,
            background_path=a.background,
            process_registry_path=a.process_registry,
            chelsa_manifest_path=a.chelsa_manifest,
            output_dir=a.output_dir,
        )
    elif a.command=="soil-assemble":
        result=assemble_soil_support(
            parts_root=a.parts_root,
            candidate_path=a.candidates,
            model_pool_path=a.model_pool,
            background_path=a.background,
            output_dir=a.output_dir,
        )
    else:
        result=aggregate_support(
            parts_root=a.parts_root,
            candidate_path=a.candidates,
            model_pool_path=a.model_pool,
            background_path=a.background,
            contract_path=a.contract,
            output_dir=a.output_dir,
        )
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
