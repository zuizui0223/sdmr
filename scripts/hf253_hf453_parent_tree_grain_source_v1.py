#!/usr/bin/env python3
"""HF253→HF453 verified original source parent-tree grain audit v1.

Never reads biology (status, CP, species, dbh, mortality, growth). The exact
2019 first-provider SHA and earlier HF453 SHA are checked BEFORE extracting
mechanical stem.tag / stem.id / tree.id. No stem or tree ID is ever saved.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, Counter
import csv
import json
from pathlib import Path
import tempfile

from hf253_hf453_original_tag_crosswalk_v2 import (
    get_frozen_hf453, fetch_HF253_provider_bytes,
    original_HF453_2021_tag_source,
    FROZEN_HF453_SHA,FROZEN_HF453_MD5,FROZEN_HF453_SIZE,
    HF253_ORIGINAL_URL,HF253_VERSION,
)

PROGRAM="sdmr_hf253_hf453_source_only_parent_tree_grain_v1"
EXPECTED_HF253_SHA="bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7"
EXPECTED_HF253_BYTES=12687409
LOCK_CONTENT="\n".join([
    f"program={PROGRAM}",
    "source_stage=parent_tree_grain_only_no_biological_values",
    f"HF453_original_SHA256={FROZEN_HF453_SHA}",
    f"HF253_original_SHA256={EXPECTED_HF253_SHA}",
    f"HF253_original_bytes={EXPECTED_HF253_BYTES}",
    f"HF253_original_EML={HF253_VERSION}",
    f"HF253_original_URL={HF253_ORIGINAL_URL}",
    "read_only_fields=HF453_StemTag_year_HF253_stem.tag_stem.id_tree.id",
    "no_species_DBH_CP_status_growth_or_mortality_opening=true",
    "no_model_refit_or_causal_claim=true",
    "no_original_tree_or_stem_IDs_exported=true",
    "no_original_CSV_retained=true",
    "no_favorable_subset_or_key_normalization=true",
    "HF453_first_biological_result_not_reclassified=true",
    "ProductA_M5_unchanged_ProductB_blocked=true",
])+"\n"


def source_parent_map(stream) -> tuple[dict[str,set[tuple[str,str]]],dict]:
    reader=csv.reader(stream)
    head=next(reader,None)
    if head and head[0].startswith("\xef\xbb\xbf"):
        head[0]=head[0][3:]
    required=("stem.tag","stem.id","tree.id")
    if not head or len(set(head))!=len(head) or any(x not in head for x in required):
        raise ValueError("HF253_original_parent_identity_columns_invalid")
    tsi,si,ti=(head.index(c) for c in required)
    entries:dict[str,set[tuple[str,str]]]=defaultdict(set)
    n_rows=0
    invalid_ascii=0
    empty_stemtags=0
    for row in reader:
        n_rows+=1
        if len(row)!=len(head):
            raise ValueError("HF253_source_row_width_not_stable")
        tag,stem_id,tree_id=(row[tsi],row[si],row[ti])
        if any(not val.isascii() or val!=val.strip() for val in (tag,stem_id,tree_id)):
            invalid_ascii+=1
            continue
        if tag in ("","NA"):
            empty_stemtags+=1
            continue
        entries[tag].add((stem_id,tree_id))
    return entries,{
        "n_HF253_original_rows":n_rows,
        "n_nonASCII_or_trim_incompatible_parent_source_rows":invalid_ascii,
        "n_empty_stem_tag_rows":empty_stemtags,
        "only_mechanical_identity_columns_used":True,
        "species_diameter_status_and_canopy_values_not_read":True,
    }


def audit_parent_tree_grain(target:set[str],
                           source:dict[str,set[tuple[str,str]]]) -> dict:
    matched=target & set(source)
    unmatched=target-set(source)
    tree_candidate:set[str]=set()
    by_tree=Counter()
    ambiguous=0
    missing_parent=0
    matched_multirow=0
    for stem_tag in matched:
        pairs=source[stem_tag]
        if len(pairs)>1:
            matched_multirow+=1
        valid={
            (sid,tid) for sid,tid in pairs
            if sid not in ("","NA") and tid not in ("","NA")
        }
        if not valid:
            missing_parent+=1
            continue
        treeids={tid for _,tid in valid}
        stemids={sid for sid,_ in valid}
        if len(treeids)!=1 or len(stemids)!=1 or len(valid)!=len(pairs):
            ambiguous+=1
            continue
        parent=next(iter(treeids))
        by_tree[parent]+=1
        tree_candidate.add(parent)
    hist=Counter(by_tree.values())
    if unmatched or missing_parent or ambiguous or len(matched)!=30808:
        status="parent_tree_identity_incomplete_source_hold"
    else:
        status="parent_tree_identity_mapped_source_only"
    return {
        "status":status,
        "n_original_HF453_StemTag":len(target),
        "n_stem_tag_matches_in_original_HF253":len(matched),
        "n_unmatched_HF453_StemTag":len(unmatched),
        "n_matched_stem_tag_with_multiple_original_HF253_rows":matched_multirow,
        "n_missing_original_stem_or_tree_parentID":missing_parent,
        "n_ambiguous_original_stem_to_parent_treeID":ambiguous,
        "n_source_resolved_stem_tags":sum(by_tree.values()),
        "n_distinct_original_tree_ID_candidates":len(tree_candidate),
        "n_tree_IDs_with_at_least_two_matched_stems":
            sum(n for k,n in hist.items() if k>=2),
        "n_matched_stems_belonging_to_multi_stem_tree_IDs":
            sum(k*n for k,n in hist.items() if k>=2),
        "parent_stem_multiplicity_histogram":{
            "one":hist.get(1,0),
            "two":hist.get(2,0),
            "three":hist.get(3,0),
            "four":hist.get(4,0),
            "five_or_more":sum(n for k,n in hist.items() if k>=5),
        },
        "maximum_matched_stems_per_tree_ID":max(by_tree.values(),default=0),
        "physical_tree_independence_not_inferred_from_stem_tags":True,
        "no_biological_response_or_process_causal_inference":True,
    }


def run_source_only()->dict:
    with tempfile.TemporaryDirectory(prefix="sdmr_hf253_hf453_parent_source_") as root:
        a=Path(root)/"HF453_unchanged_source_discarded.csv"
        b=Path(root)/"HF253_unchanged_source_discarded.csv"
        r1=get_frozen_hf453(a)
        if r1!={"sha256":FROZEN_HF453_SHA,"md5":FROZEN_HF453_MD5,
               "n_bytes":FROZEN_HF453_SIZE}:
            raise ValueError("HF453_original_source_byte_identity_changed")
        r2=fetch_HF253_provider_bytes(b)
        if r2["sha256"]!=EXPECTED_HF253_SHA or r2["bytes"]!=EXPECTED_HF253_BYTES:
            raise ValueError("HF253_original_source_byte_identity_changed")
        with a.open("r",encoding="latin-1",newline="") as f:
            stems=original_HF453_2021_tag_source(f)
        with b.open("r",encoding="latin-1",newline="") as f:
            mapped,meta=source_parent_map(f)
        parent=audit_parent_tree_grain(stems,mapped)
        return {
            "original_HF453_sha256":r1["sha256"],
            "original_HF253_sha256":r2["sha256"],
            "original_HF253_bytes":r2["bytes"],
            "HF253_source_identity_metadata":meta,
            "parent_tree_grain":parent,
            "no_biological_source_columns_interpreted":True,
            "no_raw_source_rows_saved":True,
        }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--execute-lock",type=Path)
    x=p.parse_args()
    if x.preflight_only==(x.execute_lock is not None):
        p.error("exactly one of preflight or execute-lock required")
    if x.execute_lock and x.execute_lock.read_text()!=LOCK_CONTENT:
        raise ValueError("HF253_parent_tree_original_source_lock_changed")
    result={"status":"preflight_no_original_tree_or_stem_data_read"} if x.preflight_only else run_source_only()
    out={
        "schema":"sdmr.hf253_hf453_original_parent_tree_grain_source_only.v1",
        "program":PROGRAM,
        "preflight":x.preflight_only,
        "result":result,
        "new_biological_status_size_or_species_values_opened":False,
        "HF453_original_status_CP_effect_untouched":True,
        "one_forest_not_independent_replication":True,
        "Product_B_unblocked":False,
    }
    x.out.parent.mkdir(parents=True,exist_ok=True)
    x.out.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("HF253×HF453 source-only parent tree grain:",
          result.get("parent_tree_grain",result).get("status"))


if __name__=="__main__":
    main()
