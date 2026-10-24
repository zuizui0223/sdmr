"""Outcome-blind, climate-only common-support preflight for geographic constraint turnover.

Fixed exogenous rectangles are geographic source frames, *not* species-specific
accessible-area M. Never read occurrence/effort columns or GBIF evidence here.
Rank predeclared pair candidates by support; do not manufacture an eligible pair.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import itertools
import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from sdmr.data.chelsa import build_chelsa_cog_uri
from sdmr.data.raster import RasterLayerSpec, extract_raster_values

STATUS = "climate_only_source_selection_not_process_identification"
NEEDED = ("region", "taxon", "cell_id", "spatial_block", "longitude", "latitude", "temperature", "moisture")


def validate_design(config: dict) -> None:
    if config.get("study_status") != STATUS or config.get("raster_axes") != {"temperature":"bio1", "moisture":"bio12"}:
        raise ValueError("Source status / predictor universe does not match frozen climate-only contract")
    if config.get("cell_side_km") != 25:
        raise ValueError("25-km equal-area grid required")
    for name in ("minimum_primary_overlap", "minimum_sensitivity_overlap", "minimum_symmetric_nn_coverage"):
        if not 0 < float(config[name]) <= 1:
            raise ValueError(f"Invalid gate: {name}")
    if config["bins_primary"] < 3 or config["bins_sensitivity"] < 3 or config["minimum_separation_km"] < 0:
        raise ValueError("Invalid climate histogram or geographic separation design")
    if config["nn_radius_pooled_sd"] <= 0 or config["minimum_spatial_blocks"] < 2:
        raise ValueError("Invalid nearest-neighbor support/blocks")
    rows = config["candidate_windows"]
    if len(rows) < 6 or len(set(x["region"] for x in rows)) != len(rows):
        raise ValueError("Need multiple unique predeclared source windows")
    counts = Counter(w["taxon"] for w in rows)
    if any(n < 3 for n in counts.values()):
        raise ValueError("At least 3 independent region options per taxon")
    for w in rows:
        if not (-180 <= w["west"] < w["east"] <= 180 and -85 <= w["south"] < w["north"] <= 85):
            raise ValueError("Invalid candidate window coordinates")
        if len(w["country"]) != 2 or not w["native_range_reference"].startswith("https://powo.science.kew.org/"):
            raise ValueError("Missing country-level taxon native status reference")


def _equal_area_grid(w: dict, cell_km: float) -> pd.DataFrame:
    # Reuse the source-contract grid generator, imported from an exact sibling path.
    sibling = Path(__file__).with_name("geographic_turnover_native_windows_v1.py")
    spec = importlib.util.spec_from_file_location("_sdmr_previous_climate_grid", sibling)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.equal_area_grid(w, cell_km)


def _geo_km(x: pd.DataFrame, y: pd.DataFrame) -> float:
    lat1, lon1 = radians(float(x.latitude.mean())), radians(float(x.longitude.mean()))
    lat2, lon2 = radians(float(y.latitude.mean())), radians(float(y.longitude.mean()))
    a = sin((lat1-lat2)/2)**2 + cos(lat1)*cos(lat2)*sin((lon1-lon2)/2)**2
    return 2 * 6371.0088 * asin(min(1.0, sqrt(a)))


def _pooled_bins(a: pd.DataFrame, b: pd.DataFrame, *, bins: int) -> float:
    x = pd.concat([a[["temperature", "moisture"]], b[["temperature", "moisture"]]], ignore_index=True)
    categories=[]
    for col in ("temperature", "moisture"):
        edges = np.unique(np.quantile(x[col].to_numpy(float), np.linspace(0, 1, bins+1)[1:-1]))
        categories.append(np.searchsorted(edges, x[col], side="right"))
    joint = categories[0] * bins + categories[1]
    h1 = np.bincount(joint[:len(a)], minlength=bins*bins).astype(float)/len(a)
    h2 = np.bincount(joint[len(a):], minlength=bins*bins).astype(float)/len(b)
    return float(np.minimum(h1,h2).sum())


def _nn_coverage(a: pd.DataFrame, b: pd.DataFrame, radius: float) -> dict:
    x = pd.concat([a[["temperature", "moisture"]],b[["temperature", "moisture"]]],ignore_index=True).to_numpy(float)
    std = x.std(axis=0)
    if np.any(std <= 1e-12):
        return {"minimum":0.0, "from_a":0.0, "from_b":0.0, "status":"degenerate_axis"}
    x = (x-x.mean(axis=0))/std
    xa, xb=x[:len(a)],x[len(a):]
    a_hits=float(np.mean(cKDTree(xb).query(xa,k=1)[0]<=radius))
    b_hits=float(np.mean(cKDTree(xa).query(xb,k=1)[0]<=radius))
    return {"minimum":min(a_hits,b_hits),"from_a":a_hits,"from_b":b_hits,"status":"ok"}


def evaluate_pairs(climate: pd.DataFrame, config: dict, *, region_status: dict[str,str]) -> dict:
    """Pure source-geometry evaluation. Any appended occurrence columns ignored."""
    validate_design(config)
    missing=set(NEEDED)-set(climate.columns)
    if missing:
        raise ValueError(f"Missing required climate-only fields {sorted(missing)}")
    frame=climate[list(NEEDED)].sort_values(["region", "cell_id"], kind="mergesort").reset_index(drop=True)
    if frame.duplicated(["region","cell_id"]).any():
        raise ValueError("Duplicate equal-area source cells")
    for name in ("temperature", "moisture", "longitude", "latitude"):
        if len(frame) and not np.isfinite(frame[name].to_numpy(float)).all():
            raise ValueError(f"Nonfinite environmental source {name}")
    known={x["region"] for x in config["candidate_windows"]}
    if set(frame.region)-known:
        raise ValueError("Unexpected post-outcome selected geographical source")
    grouped={name: group.reset_index(drop=True) for name,group in frame.groupby("region",sort=True)}
    windows=config["candidate_windows"]
    rows=[]
    for i,j in itertools.combinations(range(len(windows)),2):
        wa,wb=windows[i],windows[j]
        if wa["taxon"]!=wb["taxon"]:
            continue
        a,b=grouped.get(wa["region"]),grouped.get(wb["region"])
        out={"taxon":wa["taxon"],"region_a":wa["region"],"region_b":wb["region"],
             "n_available_cells_a":0 if a is None else len(a),"n_available_cells_b":0 if b is None else len(b),
             "eligible":False,"reasons":[]}
        if region_status.get(wa["region"])!="climate_complete" or a is None:
            out["reasons"].append("region_a_source_unavailable")
        if region_status.get(wb["region"])!="climate_complete" or b is None:
            out["reasons"].append("region_b_source_unavailable")
        if out["reasons"]:
            rows.append(out);continue
        out["n_spatial_blocks_a"]=int(a.spatial_block.nunique())
        out["n_spatial_blocks_b"]=int(b.spatial_block.nunique())
        out["geographic_separation_km"]=float(_geo_km(a,b))
        out["environment_overlap_bins6"]=float(_pooled_bins(a,b,bins=config["bins_primary"]))
        out["environment_overlap_bins8"]=float(_pooled_bins(a,b,bins=config["bins_sensitivity"]))
        out["nearest_shared_environment"]= _nn_coverage(a,b,float(config["nn_radius_pooled_sd"]))
        checks={
            "too_few_climate_cells": min(len(a),len(b))<config["minimum_cells_per_region"],
            "too_few_spatial_blocks":min(a.spatial_block.nunique(),b.spatial_block.nunique())<config["minimum_spatial_blocks"],
            "geographic_distance_below_minimum":out["geographic_separation_km"]<config["minimum_separation_km"],
            "primary_environment_overlap_below_minimum":out["environment_overlap_bins6"]<config["minimum_primary_overlap"],
            "sensitivity_environment_overlap_below_minimum":out["environment_overlap_bins8"]<config["minimum_sensitivity_overlap"],
            "nearest_environment_coverage_below_minimum":out["nearest_shared_environment"]["minimum"]<config["minimum_symmetric_nn_coverage"]
        }
        out["reasons"]=[k for k,v in checks.items() if v]
        out["eligible"]=not bool(out["reasons"])
        rows.append(out)
    selected=[]
    for taxon in sorted(set(w["taxon"] for w in windows)):
        eligible=[r for r in rows if r["taxon"]==taxon and r["eligible"]]
        eligible.sort(key=lambda v:(-v["environment_overlap_bins6"],-v["environment_overlap_bins8"],
                                    -v["nearest_shared_environment"]["minimum"],v["region_a"],v["region_b"]))
        selected.append({"taxon":taxon,"selected_pair":({"region_a":eligible[0]["region_a"],
                     "region_b":eligible[0]["region_b"]} if eligible else None),
                     "eligible_pair_count":len(eligible),"source_only":True})
    return {"analysis":"geographic_turnover_common_support_v1","selection_uses_occurrence_or_effort":False,
            "paired_environment_only":True,"n_declared_windows":len(windows),"n_pairs":len(rows),
            "n_eligible_pairs":sum(x["eligible"] for x in rows),"selected_per_taxon":selected,
            "candidates":rows,"source_boundary":"available-climate rectangles only; not taxon accessible M or ecological drivers"}


def assemble(config: dict, *, grid_builder:Callable|None=None, extractor:Callable|None=None) -> tuple[dict,pd.DataFrame]:
    validate_design(config)
    grid_builder=grid_builder or _equal_area_grid
    extractor=extractor or extract_raster_values
    layers=[RasterLayerSpec(predictor=alias,uri=build_chelsa_cog_uri(remote_name=code,retrieval="annual_bio_cog"),
                            source="CHELSA-bioclim",version="2.1") for alias,code in config["raster_axes"].items()]
    grids=[];statuses={};metadata=[]
    for w in config["candidate_windows"]:
        row={"region":w["region"],"taxon":w["taxon"],"country":w["country"],
             "native_country_reference":w["native_range_reference"],"uses_gbif_occurrences":False}
        try:
            points=grid_builder(w,config["cell_side_km"])
            row["n_geometry_cells"]=len(points)
            if len(points)==0:raise ValueError("empty fixed rectangular grid")
            sample,provenance=extractor(points,layers,lon_col="longitude",lat_col="latitude")
            mask=np.isfinite(sample[["temperature","moisture"]].to_numpy(float)).all(axis=1)
            row["n_climate_complete_cells"]=int(mask.sum())
            if mask.sum()==0:raise ValueError("zero two-axis climate-complete cells")
            retained=sample.loc[mask].copy()
            retained["taxon"]=w["taxon"]
            grids.append(retained[list(NEEDED)])
            row["raster_provenance"]=provenance.to_dict("records")
            row["status"]="climate_complete"
        except Exception as e:
            row["status"]="climate_unavailable"
            row["error"]=f"{type(e).__name__}: {e}"
        metadata.append(row)
        statuses[w["region"]]=row["status"]
    cells=pd.concat(grids,ignore_index=True) if grids else pd.DataFrame(columns=NEEDED)
    output=evaluate_pairs(cells,config,region_status=statuses)
    output["source_windows"]=metadata
    return output,cells


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=Path("configs/geographic_turnover_common_support_v1.json"))
    parser.add_argument("--output-dir",type=Path,default=Path("artifacts/geographic_common_support_v1"))
    args=parser.parse_args()
    config=json.loads(args.config.read_text())
    result,cells=assemble(config)
    result["config_file_sha256"]=hashlib.sha256(args.config.read_bytes()).hexdigest()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"source_selection.json").write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    cells.to_csv(args.output_dir/"all_candidate_climate_cells.csv",index=False)
    print("source windows",sum(x["status"]=="climate_complete" for x in result["source_windows"]),"/",result["n_declared_windows"])
    print("eligible climate-only pairs",result["n_eligible_pairs"],"/",result["n_pairs"])
    print("selected",result["selected_per_taxon"])
    print("NO GBIF/presence, physiology, occupancy, or ecological process conclusions from climate screening")


if __name__ == "__main__":
    main()
