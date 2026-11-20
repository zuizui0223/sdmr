#!/usr/bin/env python3
"""Coordinate-axis/source-grain diagnostic only after frozen spatial v1 STOP.

No 2021 CP, 2022 status, species, DBH or individual response values accessed.
Both exact original source files are SHA verified before tag/gx/gy extraction.
This diagnostic does NOT fit models, change original block gate or prove which
plot orientation is correct without publisher metadata.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import tempfile

from hf253_hf453_original_tag_crosswalk_v2 import (
    get_frozen_hf453,fetch_HF253_provider_bytes,
    original_HF453_2021_tag_source,
    FROZEN_HF453_SHA,FROZEN_HF453_MD5,FROZEN_HF453_SIZE,
)
from hf453_prior_species_size_confounding_postoutcome_v1 import (
    ORIGINAL_HF253_SHA, ORIGINAL_HF253_BYTES,
)

PROGRAM="sdmr_hf253_xy_source_axis_orientation_only_v1"
LOCK="\n".join([
    f"program={PROGRAM}",
    "cause=HF453_100m_spatial_first_source_coverage_0.6669576_stop",
    f"HF253_source_sha256={ORIGINAL_HF253_SHA}",
    f"HF453_source_sha256={FROZEN_HF453_SHA}",
    "zero_HF453_status_CP_or_biological_response_access=true",
    "source_columns=HF453_StemTag_year_HF253_stem.tag_tree.id_gx_gy_only",
    "compare_fixed_assumed_frames=x500_y700_and_x700_y500",
    "no_model_CV_or_outcome_driven_geometry_selection=true",
    "no_identifier_coordinate_microdata_archived=true",
    "ProductA_M5_unchanged_ProductB_blocked=true",
])+"\n"


def inspect_original_xy(stream,target:set[str],*,expected_rows:int=123218,
                        expected_targets:int=30808,expected_parents:int=27688)->dict:
    rdr=csv.reader(stream)
    head=next(rdr,None)
    if head and head[0].startswith("\xef\xbb\xbf"):head[0]=head[0][3:]
    cols=("stem.tag","tree.id","gx","gy")
    if not head or len(set(head))!=len(head) or any(k not in head for k in cols):
        raise ValueError("original_HF253_geographic_source_columns_unavailable")
    ix=[head.index(k) for k in cols]
    source={} # solely temporary original source metadata, no output identifiers
    n_rows=0;missing=0;invalid=0
    for row in rdr:
        n_rows+=1
        if len(row)!=len(head):
            raise ValueError("original_HF253_source_row_width_drift")
        tag,parent,xstr,ystr=(row[i] for i in ix)
        if tag not in target:continue
        if not tag.isascii() or not parent.isascii() or not parent or parent=="NA" or tag in source:
            raise ValueError("original_HF253_source_tag_or_parent_identity_drift")
        xy=None
        if xstr in ("","NA") or ystr in ("","NA"):missing+=1
        else:
            try:
                x,y=float(xstr),float(ystr)
                if math.isfinite(x) and math.isfinite(y):
                    xy=(x,y)
                else:invalid+=1
            except ValueError:invalid+=1
        source[tag]=(parent,xy)
    if n_rows!=expected_rows or len(target)!=expected_targets or set(source)!=target:
        raise ValueError("fixed_source_tag_or_source_row_denominator_changed")
    parent_coords=defaultdict(list)
    xvals=[];yvals=[]
    for parent,xy in source.values():
        parent_coords[parent].append(xy)
        if xy is not None:
            xvals.append(xy[0]);yvals.append(xy[1])
    if len(parent_coords)!=expected_parents:
        raise ValueError("original_parent_tree_ID_count_changed")
    geometries={}
    for width,height,label in ((500,700,"assumed_x500_y700"),
                               (700,500,"alternate_x700_y500")):
        valid_tags={tag for tag,(_,pt) in source.items()
                    if pt is not None and 0<=pt[0]<=width and 0<=pt[1]<=height}
        valid_parents={p for p,coords in parent_coords.items()
                       if all(xy is not None and 0<=xy[0]<=width and 0<=xy[1]<=height
                              for xy in coords)}
        bins=set()
        for p in valid_parents:
            pts=parent_coords[p]
            x=math.fsum(xy[0] for xy in pts)/len(pts)
            y=math.fsum(xy[1] for xy in pts)/len(pts)
            bins.add((min(int(x//100),width//100-1),
                      min(int(y//100),height//100-1)))
        geometries[label]={
            "plot_frame_x_m":width,"plot_frame_y_m":height,
            "n_source_valid_stems":len(valid_tags),
            "n_source_invalid_stems":len(target)-len(valid_tags),
            "n_full_original_parent_IDs_with_valid_source_positions":len(valid_parents),
            "n_full_original_parent_IDs_ineligible":len(parent_coords)-len(valid_parents),
            "n_source_original_parent_centroid_100m_cells":len(bins),
        }
    return {
        "status":"original_source_xy_axis_support_diagnosed_only",
        "n_original_2019_rows":n_rows,
        "n_HF453_fixed_original_2021_stems":len(target),
        "n_original_parent_tree_IDs":len(parent_coords),
        "n_missing_original_gx_or_gy":missing,
        "n_invalid_nonfinite_or_unparseable_gx_gy":invalid,
        "original_x_min":min(xvals,default=None),
        "original_x_max":max(xvals,default=None),
        "original_y_min":min(yvals,default=None),
        "original_y_max":max(yvals,default=None),
        "n_source_x_lt_0":sum(x<0 for x in xvals),
        "n_source_y_lt_0":sum(y<0 for y in yvals),
        "n_source_x_gt_500":sum(x>500 for x in xvals),
        "n_source_x_gt_700":sum(x>700 for x in xvals),
        "n_source_y_gt_500":sum(y>500 for y in yvals),
        "n_source_y_gt_700":sum(y>700 for y in yvals),
        "fixed_geometry_candidate_receipts":geometries,
        "zero_original_HF453_outcomes_or_covariate_models_opened":True,
        "axis_orientation_not_demonstrated_by_coordinate_ranges_alone":True,
    }


def run_source_axis_only()->dict:
    with tempfile.TemporaryDirectory(prefix="hf253_original_xy_axis_") as root:
        a=Path(root)/"HF453_source_not_retained.csv"
        b=Path(root)/"HF253_source_not_retained.csv"
        p=get_frozen_hf453(a)
        if p!={"sha256":FROZEN_HF453_SHA,"md5":FROZEN_HF453_MD5,
               "n_bytes":FROZEN_HF453_SIZE}:
            raise ValueError("original_HF453_byte_SHA_changed")
        q=fetch_HF253_provider_bytes(b)
        if q["sha256"]!=ORIGINAL_HF253_SHA or q["bytes"]!=ORIGINAL_HF253_BYTES:
            raise ValueError("original_HF253_byte_SHA_changed")
        with a.open(encoding="latin-1",newline="") as f:
            target=original_HF453_2021_tag_source(f)
        with b.open(encoding="latin-1",newline="") as f:
            result=inspect_original_xy(f,target)
        return {
            "source_HF453_sha256":p["sha256"],
            "source_HF253_sha256":q["sha256"],
            "source_coordinate_metadata":result,
            "source_original_CSVs_not_retained":True,
            "source_original_stem_and_parent_IDs_not_exported":True,
            "no_models_fit":True,
            "prior_first_spatial_CV_gate_not_reinterpreted":True,
        }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--execute-lock",type=Path)
    a=ap.parse_args()
    if a.preflight_only==(a.execute_lock is not None):
        ap.error("exactly one of preflight/execute-lock")
    if a.execute_lock and a.execute_lock.read_text()!=LOCK:
        raise ValueError("HF253_xy_axis_source_diagnostic_contract_changed")
    result={"status":"response_free_xy_source_preflight_only"} if a.preflight_only else run_source_axis_only()
    out={
        "schema":"sdmr.HF253_2019_xy_axis_source_only_v1",
        "program":PROGRAM,
        "preflight":a.preflight_only,
        "result":result,
        "previous_HF453_first_Y_untouched":True,
        "new_HF453_biological_outcome_read":False,
        "new_model_fits":0,
        "not_independent_forest_generalization":True,
        "Product_B_unblocked":False,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("HF253 original coordinate axis support:",result.get("source_coordinate_metadata",result).get("status"))


if __name__=='__main__':
    main()
