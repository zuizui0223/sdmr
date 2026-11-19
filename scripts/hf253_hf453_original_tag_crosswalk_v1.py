#!/usr/bin/env python3
"""Original HF253-2019 × HF453-2021 literal tag source-identity audit only.

HF453 prior biological status outcome is already consumed; none is reused here.
Reads *only* original tags and mechanical tree/stem identifiers. Does not
interpret species, diameter, demographic status, health, CP, growth, plot
coordinates or field response, and does not select a favorable key.
No original CSV is archived; all outputs are nonidentifying aggregate counts.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, Counter
import csv
from hashlib import sha256, md5
import json
from pathlib import Path
import tempfile
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from hf453_tag_year_identity_source_only_v2 import (
    _download_and_hash_original as get_frozen_hf453,
    EXPECTED_ORIGINAL_SHA256 as FROZEN_HF453_SHA,
    EXPECTED_ORIGINAL_NBYTES as FROZEN_HF453_SIZE,
    PUBLISHER_MD5 as FROZEN_HF453_MD5,
)

PROGRAM = "sdmr_hf253_2019_to_hf453_2021_exact_tag_source_only_v1"
HF253_ORIGINAL_URL = "https://harvardforest.fas.harvard.edu/data/p25/hf253/hf253-06-stems-2019.csv"
HF253_VERSION = "knb-lter-hfr.253.6"
HF253_DOI = "10.6073/pasta/818789a882a318c1d7f3fc43a2289e12"
HF253_MAX_BYTES = 268435456
ALLOWED_HOSTS = frozenset({"harvardforest.fas.harvard.edu","harvardforest1.fas.harvard.edu"})
CONFIG = Path("configs/hf253_hf453_source_identity_prefreeze_v1.json")
LOCK_CONTENT = "\n".join([
    f"program={PROGRAM}",
    "endpoint=source_only_exact_tag_identity_not_outcome",
    "post_HF453_first_outcome_opening=true",
    f"fixed_HF453_original_sha256={FROZEN_HF453_SHA}",
    f"HF253_publisher_version={HF253_VERSION}",
    f"HF253_exact_original_url={HF253_ORIGINAL_URL}",
    "HF253_prior_source_new_full_byte_sha_record_once=true",
    "source_columns=HF453_StemTag_year_HF253_tag_stem.tag_tree.id_stem.id",
    "all_species_dbh_status_CP_coordinates_not_interpreted=true",
    "no_favorable_outcome_driven_key_selection=true",
    "no_original_CSV_archived=true",
    "no_automatic_provider_retry=true",
    "single_forest_not_independent_replication=true",
    "ProductA_M5_unchanged_ProductB_blocked=true",
]) + "\n"


def source_url_verified(url: str) -> bool:
    p=urlsplit(url)
    if (p.scheme != "https" or p.hostname not in ALLOWED_HOSTS or
            p.username or p.password or p.query or p.fragment or
            p.port not in (None,443) or
            p.path != "/data/p25/hf253/hf253-06-stems-2019.csv"):
        raise ValueError("HF253_original_file_url_moved_or_unexpected")
    return True


class StrictPublisherRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        source_url_verified(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def validate_source_contract(config: dict) -> None:
    if config.get("schema") != "sdmr.hf253_hf453_original_tag_identity_crosswalk_prefreeze.v1":
        raise ValueError("unknown_HF253_HF453_source_design")
    a,b=config["HF453"],config["HF253"]
    if (a["raw_sha256"] != FROZEN_HF453_SHA or a["raw_md5"] != FROZEN_HF453_MD5
            or a["raw_bytes"] != FROZEN_HF453_SIZE
            or a["expected_unique_tag_count"] != 30808
            or a["extraction"] != ["StemTag","year"]
            or b["publisher_version"] != HF253_VERSION
            or b["raw_url"] != HF253_ORIGINAL_URL
            or b["original_data_fields_to_index"] != [
                "tag","stem.tag","tree.id","stem.id"
            ]
            or config["source_limit_bytes"] != HF253_MAX_BYTES):
        raise ValueError("original_source_or_allowed_identity_column_contract_changed")
    fields=config["admission"]
    if not all(fields[k] for k in (
        "exact_literal_tags_only","drop_ambiguous_matches",
        "do_not_select_best_join_using_HF453_Y","skip_outcome_fields"
    )) or fields["case_folding"] or fields["remove_leading_zeros"]:
        raise ValueError("literal_tag_matching_contract_changed")


def fetch_HF253_provider_bytes(path: Path) -> dict:
    source_url_verified(HF253_ORIGINAL_URL)
    opener=build_opener(StrictPublisherRedirect())
    req=Request(
        HF253_ORIGINAL_URL,
        headers={"Accept":"text/csv,application/octet-stream",
                 "User-Agent":"sdmr-hf253-hf453-original-tag-only/1.0"},
    )
    h=sha256();h5=md5();n=0
    with opener.open(req,timeout=65) as stream, path.open("wb") as out:
        source_url_verified(stream.geturl())
        size=stream.headers.get("Content-Length")
        if size is not None and int(size)>HF253_MAX_BYTES:
            raise ValueError("HF253_original_file_exceeds_predeclared_cap")
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            n+=len(chunk)
            if n>HF253_MAX_BYTES:
                raise ValueError("HF253_original_file_exceeds_predeclared_cap")
            h.update(chunk);h5.update(chunk);out.write(chunk)
    if n<1:
        raise ValueError("HF253_original_file_empty")
    return {"sha256":h.hexdigest(),"md5_recorded_not_publisher_verified":h5.hexdigest(),"bytes":n}


def original_HF453_2021_tag_source(stream, *, expected=30808) -> set[str]:
    read=csv.reader(stream)
    head=next(read,None)
    if head and head[0].startswith("\xef\xbb\xbf"):
        head[0]=head[0][3:]
    if not head or "StemTag" not in head or "year" not in head:
        raise ValueError("HF453_published_source_header_changed")
    tagi,yi=head.index("StemTag"),head.index("year")
    tags:set[str]=set()
    n=0
    for row in read:
        if len(row)!=len(head):
            raise ValueError("HF453_row_width_changed")
        if row[yi]=="2021":
            tag=row[tagi]
            if not tag.isascii() or not tag or tag != tag.strip() or tag in tags:
                raise ValueError("HF453_2021_tag_source_duplicate_or_invalid")
            tags.add(tag)
        n+=1
    if n!=expected*4 or len(tags)!=expected:
        raise ValueError("HF453_source_frame_changed")
    return tags


def scan_HF253_prior_identity(stream) -> tuple[dict[str,set[str]],dict[str,set[str]],dict]:
    read=csv.reader(stream)
    header=next(read,None)
    if header and header[0].startswith("\xef\xbb\xbf"):
        header[0]=header[0][3:]
    cols=("tag","stem.tag","tree.id","stem.id")
    if not header or len(set(header))!=len(header) or any(c not in header for c in cols):
        raise ValueError("HF253_source_identity_header_missing_or_duplicate")
    ti,si,trid,stid=(header.index(c) for c in cols)
    tree:dict[str,set[str]]=defaultdict(set)
    stem:dict[str,set[str]]=defaultdict(set)
    rows=0
    invalid=0
    for row in read:
        rows+=1
        if len(row)!=len(header):
            raise ValueError("HF253_original_row_width_invalid")
        t,st,tr,sid=(row[ti],row[si],row[trid],row[stid])
        # This four-field parser never touches species, dbh, or source status.
        vals=(t,st,tr,sid)
        if any(not value.isascii() or value!=value.strip() for value in vals):
            invalid+=1
            continue
        if t not in ("","NA"):
            tree[t].add(tr if tr not in ("","NA") else "<unknown_tree_id>")
        if st not in ("","NA"):
            stem[st].add(sid if sid not in ("","NA") else "<unknown_stem_id>")
    return tree,stem, {
        "n_HF253_original_rows":rows,
        "n_invalid_exact_identity_rows":invalid,
        "n_distinct_nonempty_tree_tags":len(tree),
        "n_distinct_nonempty_stem_tags":len(stem),
        "n_tree_tags_mapping_to_multiple_distinct_tree_ids":
            sum(len(v)>1 for v in tree.values()),
        "n_stem_tags_mapping_to_multiple_distinct_stem_ids":
            sum(len(v)>1 for v in stem.values()),
        "only_four_identity_columns_indexed":True,
        "species_size_status_plot_columns_interpreted":False,
    }


def compare_literal_tag_keys(
    HF453_tags:set[str], trees:dict[str,set[str]],
    stems:dict[str,set[str]],
) -> dict:
    tree_keys=set(trees);stem_keys=set(stems)
    both=HF453_tags & tree_keys & stem_keys
    only_tree=(HF453_tags & tree_keys)-stem_keys
    only_stem=(HF453_tags & stem_keys)-tree_keys
    none=HF453_tags-(tree_keys|stem_keys)
    if len(both)+len(only_tree)+len(only_stem)+len(none)!=len(HF453_tags):
        raise AssertionError("HF453_tag_frame_lost_during_identity_comparison")
    return {
        "n_HF453_original_2021_tags":len(HF453_tags),
        "n_exact_tag_column_matches":len(HF453_tags & tree_keys),
        "n_exact_stem_tag_column_matches":len(HF453_tags & stem_keys),
        "n_exact_match_both_columns":len(both),
        "n_exact_match_only_tag_column":len(only_tree),
        "n_exact_match_only_stem_tag_column":len(only_stem),
        "n_unmatched_in_both_2019_keys":len(none),
        "n_tag_column_ambiguous_tree_id_matches":
            sum(len(trees[t]) !=1 or "<unknown_tree_id>" in trees[t]
                for t in (both|only_tree)),
        "n_stem_tag_column_ambiguous_stem_id_matches":
            sum(len(stems[t]) !=1 or "<unknown_stem_id>" in stems[t]
                for t in (both|only_stem)),
        "zero_normalization_or_outcome_driven_key_selection":True,
        "identity_match_not_physical_tree_validation":True,
        "unmatched_2019_tag_not_biological_absence":True,
    }


def run(config:dict) -> dict:
    validate_source_contract(config)
    with tempfile.TemporaryDirectory(prefix="hf253_hf453_source_identity_") as root:
        folder=Path(root)
        hf453=folder/"HF453_preexisting_source_discarded.csv"
        hf253=folder/"HF253_first_original_provider_discarded.csv"
        old=get_frozen_hf453(hf453)
        if (old["sha256"]!=FROZEN_HF453_SHA or
                old["md5"]!=FROZEN_HF453_MD5 or
                old["n_bytes"]!=FROZEN_HF453_SIZE):
            raise ValueError("known_HF453_source_sha_not_identical")
        # Source HG253 first byte identity is acquired once. No biological row
        # is opened until matching the publisher path and the typed header.
        new=fetch_HF253_provider_bytes(hf253)
        with hf453.open("r",encoding="latin-1",newline="") as f:
            target=original_HF453_2021_tag_source(f)
        with hf253.open("r",encoding="latin-1",newline="") as f:
            tree,stem,src=scan_HF253_prior_identity(f)
        return {
            "status":"HF253_HF453_original_source_candidate_keys_screened_only",
            "HF453_original_sha256":old["sha256"],
            "HF253_new_source_first_byte_receipt":new,
            "HF253_original_identity_metadata":src,
            "exact_literal_crosswalk":compare_literal_tag_keys(target,tree,stem),
            "source_raw_microdata_archived":False,
            "new_biological_response_values_opened":False,
            "no_species_diameter_status_or_CP_scored":True,
            "no_independent_forest_replication":True,
            "no_causal_process_identification":True,
        }


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",type=Path,default=CONFIG)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--execute-lock",type=Path)
    opts=ap.parse_args()
    if opts.preflight_only==(opts.execute_lock is not None):
        ap.error("exactly one of --preflight-only or --execute-lock")
    config=json.loads(opts.config.read_text())
    validate_source_contract(config)
    if opts.execute_lock and opts.execute_lock.read_text()!=LOCK_CONTENT:
        raise ValueError("HF253_original_new_source_lock_mismatch")
    result={"status":"source_only_preflight_no_original_field_values"} if opts.preflight_only else run(config)
    out={
        "schema":"sdmr.hf253_hf453_first_tag_crosswalk_source_only.v1",
        "program":PROGRAM,
        "preflight":opts.preflight_only,
        "study_scope":"one_original_Harvard_Forest_35ha",
        "post_HF453_outcome_exploration_not_new_independent_confirmation":True,
        "species_or_size_values_opened":False,
        "HF453_status_CP_or_mortality_reopened":False,
        "biological_effect_estimated":False,
        "Product_B_unblocked":False,
        "result":result,
    }
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("HF253×HF453 original source-only crosswalk:",result["status"])


if __name__=="__main__":
    main()
