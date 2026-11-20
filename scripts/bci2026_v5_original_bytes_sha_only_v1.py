#!/usr/bin/env python3
"""BCI Dryad v5 original file SHA256 admission only; NO original row decoding.

Source is the previously resolved PUBLIC revised 2026-08-31 version ID 460507.
Metadata v1 proved five provider SHA256+sizes but did not extract file IDs
from the versioned _links; this distinctly precommitted successor fixes *that
metadata omission only* and then streams original files through SHA256.
No original data files are persisted, parsed, or included in GitHub artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError, URLError

from bci2026_source_provider_metadata_v1 import (
    _api_get_json, require_api_url, BASE, DOI, EXPECTED_FILES,
)

PROGRAM = "sdmr_bci2026_v5_original_five_files_sha256_only_v1"
VERSION_ID = 460507
MANIFEST_URL = f"{BASE}/versions/{VERSION_ID}/files"
CHECKPOINT = Path("evidence/bci2026_first_dryad_published_metadata_v1.json")
MAX_TOTAL_SOURCE_BYTES = 8*1024*1024
LOCK = "\n".join([
    f"program={PROGRAM}",
    "source_DOI=10.5061/dryad.1g1jwsvc3",
    "publisher_exact_version_id=460507",
    "publisher_version_number=5",
    "publisher_release_date=2026-08-31",
    "original_manifest=https://datadryad.org/api/v2/versions/460507/files",
    "five_file_full_byte_sha256_only_no_header_or_row_decoding=true",
    "read_download_links_only_from_exact_version_provider_manifest=true",
    "source_archive_files_and_biological_rows_not_saved=true",
    "no_alternate_version_retries_or_fallback_mirrors=true",
    "no_2025_exposure_predicts_2014_to_2025_survival=true",
    "BCI_missing_and_inferred_death_not_directly_observed_Y=true",
    "original_M5_ProductA_untouched_ProductB_blocked=true",
]) + "\n"


def require_file_download_link(href: str) -> tuple[str,int]:
    if not isinstance(href,str):
        raise ValueError("Dryad_download_link_missing")
    full = ("https://datadryad.org" + href) if href.startswith("/") else href
    require_api_url(full)
    parsed=urlsplit(full)
    match=re.fullmatch(r"/api/v2/files/(\d+)/download",parsed.path)
    if not match or parsed.query:
        raise ValueError("not_exact_original_Dryad_file_download_link")
    return full,int(match.group(1))


def strict_download_host(url: str)->str:
    p=urlsplit(url)
    host=p.hostname or ""
    if (p.scheme!="https" or
        not (host=="datadryad.org" or host.endswith(".datadryad.org") or
             host=="s3.amazonaws.com" or host.endswith(".amazonaws.com"))
        or p.username or p.password or p.fragment):
        raise ValueError("Dryad_original_file_redirect_outside_provider_or_S3")
    return host


class StrictOriginalByteRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        strict_download_host(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def precommitted_metadata(checkpoint:dict)->dict:
    if (checkpoint.get("schema")!="sdmr.bci2026_first_published_source_metadata_receipt.v1" or
        checkpoint.get("doi")!=DOI or
        checkpoint.get("Dryad_version_id")!=VERSION_ID or
        checkpoint.get("Dryad_version_number")!=5 or
        checkpoint.get("Dryad_exact_publication_date")!="2026-08-31" or
        checkpoint.get("first_metadata_one_shot_run_id")!=44758571119 or
        checkpoint.get("first_source_file_sha256_verified") is not False or
        checkpoint.get("all_biological_rows_still_unopened") is not True):
        raise ValueError("BCI_first_provider_metadata_receipt_not_immutable")
    entries=checkpoint.get("files",{})
    if set(entries)!=EXPECTED_FILES:
        raise ValueError("BCI_original_five_file_source_set_changed")
    for name, x in entries.items():
        if (type(x.get("bytes")) is not int or x["bytes"]<1 or
            type(x.get("sha256")) is not str or
            not re.fullmatch("[0-9a-f]{64}",x["sha256"])):
            raise ValueError("publisher_SHA256_or_size_missing:"+name)
    if sum(d["bytes"] for d in entries.values())>MAX_TOTAL_SOURCE_BYTES:
        raise ValueError("precommitted_original_bytes_exceed_cap")
    return entries


def parse_exact_publisher_manifest(raw:dict,expected:dict)->dict:
    records=(raw.get("_embedded") or {}).get("stash:files")
    if not isinstance(records,list) or len(records)!=5:
        raise ValueError("Dryad_original_manifest_five_files_missing")
    if raw.get("count",len(records))!=len(records):
        raise ValueError("Dryad_published_source_manifest_pagination_incomplete")
    output={}
    for x in records:
        name=x.get("path")
        if name not in expected or name in output:
            raise ValueError("Dryad_versioned_filename_or_duplicate_mismatch")
        if (x.get("size")!=expected[name]["bytes"] or
            x.get("digest")!=expected[name]["sha256"] or
            x.get("digestType")!="sha-256"):
            raise ValueError("Dryad_selected_version_published_SHA_drift")
        links=x.get("_links") or {}
        sl=(links.get("self") or {}).get("href")
        dl=(links.get("stash:download") or {}).get("href")
        vl=(links.get("stash:version") or {}).get("href")
        url,fileid=require_file_download_link(dl)
        if sl!=f"/api/v2/files/{fileid}" or vl!=f"/api/v2/versions/{VERSION_ID}":
            raise ValueError("Dryad_original_file_identity_not_version_pinned")
        output[name]={"download_url":url,"source_file_id":fileid,
                      "publisher_sha256":expected[name]["sha256"],
                      "publisher_bytes":expected[name]["bytes"]}
    return output


def stream_original_file_sha256(
    original_url:str,expected_bytes:int,expected_sha:str,*,opener=None
)->dict:
    strict_download_host(original_url)
    if not re.fullmatch(r"[0-9a-f]{64}",expected_sha):
        raise ValueError("original_expected_SHA256_not_valid")
    if type(expected_bytes) is not int or not 1<=expected_bytes<=MAX_TOTAL_SOURCE_BYTES:
        raise ValueError("original_publisher_file_byte_cap_invalid")
    opener=opener or build_opener(StrictOriginalByteRedirect())
    req=Request(original_url,headers={
        "Accept":"application/octet-stream, text/plain, */*",
        "Accept-Encoding":"identity",
        "User-Agent":"sdmr-bci-original-source-hash-only/1.0",
    })
    h=hashlib.sha256()
    seen=0
    with opener.open(req,timeout=60) as response:
        final_host=strict_download_host(response.geturl())
        length=response.headers.get("Content-Length")
        if length is not None and int(length)>expected_bytes:
            raise ValueError("original_publisher_file_size_exceeds_pinned_digest_frame")
        while True:
            buf=response.read(256*1024)
            if not buf:break
            if not isinstance(buf,bytes):
                raise TypeError("original_provider_binary_bytes_only")
            seen+=len(buf)
            if seen>expected_bytes:
                raise ValueError("original_provider_bytes_larger_than_published_size")
            h.update(buf)
    got=h.hexdigest()
    return {
        "status":("original_full_byte_sha256_matched" if seen==expected_bytes and got==expected_sha
                  else "original_provider_sha_or_size_drift_STOP"),
        "n_original_bytes":seen,
        "source_SHA256_checked":got,
        "published_SHA256_expected":expected_sha,
        "provider_size_expected":expected_bytes,
        "provider_final_host":final_host,
        "biological_rows_or_original_text_decoded":False,
        "original_file_saved_to_artifact":False,
    }


def execute_once(metadata_checkpoint:dict)->dict:
    expected=precommitted_metadata(metadata_checkpoint)
    manifest=parse_exact_publisher_manifest(_api_get_json(MANIFEST_URL),expected)
    per_file=[]
    status="all_original_five_file_sha256_matched_no_biological_rows_opened"
    # All names are source-frozen, so the order cannot be selected by the outcome.
    for filename in sorted(EXPECTED_FILES):
        m=manifest[filename]
        try:
            downloaded=stream_original_file_sha256(
                m["download_url"],m["publisher_bytes"],m["publisher_sha256"])
            per_file.append({
                "original_filename":filename,
                "original_file_id":m["source_file_id"],
                **downloaded,
            })
            if downloaded["status"]!="original_full_byte_sha256_matched":
                status="original_provider_file_sha256_or_size_drift_STOP"
                break
        except HTTPError as err:
            status="original_file_http_access_unavailable_STOP"
            per_file.append({"original_filename":filename,
                "original_file_id":m["source_file_id"],
                "status":status,"reason":f"http_{err.code}"})
            break
        except (URLError,OSError,TimeoutError):
            status="original_file_network_access_unavailable_STOP"
            per_file.append({"original_filename":filename,
                "original_file_id":m["source_file_id"],
                "status":status,"reason":"network_or_tls"})
            break
        except (ValueError,TypeError) as err:
            status="original_provider_file_integrity_or_redirect_STOP"
            per_file.append({"original_filename":filename,
                "original_file_id":m["source_file_id"],
                "status":status,"reason":type(err).__name__})
            break
    return {
        "status":status,
        "original_dataset_version_id":VERSION_ID,
        "original_published_exact_files":len(EXPECTED_FILES),
        "n_original_files_checked":len(per_file),
        "n_original_files_passed_SHA256":sum(
            x["status"]=="original_full_byte_sha256_matched" for x in per_file),
        "file_receipts":per_file,
        "downloaded_original_files_archived":0,
        "decoded_biological_rows":0,
        "original_tree_status_or_2025_exposure_inspected":False,
        "original_sampling_opportunity_audited":False,
        "new_ecological_model_results":0,
        "new_independent_field_process_validation":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint",type=Path,default=CHECKPOINT)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--execute-lock",type=Path)
    args=p.parse_args()
    if args.preflight_only==(args.execute_lock is not None):
        p.error("choose exactly one preflight or execute-lock")
    checkpoint=json.loads(args.checkpoint.read_text())
    precommitted_metadata(checkpoint)
    if args.execute_lock and args.execute_lock.read_text()!=LOCK:
        raise ValueError("BCI_original_full_byte_hash_only_second_stage_lock_changed")
    outcome=({"status":"preflight_metadata_sha_pinned_original_tree_rows_unopened"}
             if args.preflight_only else execute_once(checkpoint))
    artifact={
        "schema":"sdmr.bci2026_original_five_file_sha256_source_only.v1",
        "program":PROGRAM,
        "preflight":args.preflight_only,
        "doi":DOI,
        "original_version_id":VERSION_ID,
        "provider_release_date":"2026-08-31",
        "source_original_mainfile_stemfile_or_README_parsed":False,
        "biological_outcome_or_2025_exposure_opened":False,
        "original_CSV_or_text_bytes_archived":False,
        "new_biological_models_fit":0,
        "independent_field_validation_not_yet_done":True,
        "Product_B_unblocked":False,
        "result":outcome,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n")
    print("BCI source bytes-only original v5:",outcome["status"])

if __name__=="__main__":
    main()
