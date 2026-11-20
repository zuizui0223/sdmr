#!/usr/bin/env python3
"""SCBI public census snapshot metadata + scientific-use gate; NO CSV GET.

Independent forest from Harvard, but neither public GitHub source snapshot
nor CC BY 4.0 alone establishes an APPROVED, versioned ForestGEO master for
scientific analysis of SCBI tree census data. This script reads only immutable
Git trees to check file paths, *Git blob SHA-1* and byte sizes. Git blob SHA-1
is not a complete raw-byte SHA-256; no data, tree tags, mortality values,
effort or original source rows are accessed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

PROGRAM="sdmr_scbi_original_public_snapshot_governance_metadata_v1"
CFG=Path("configs/scbi_independent_forest_governance_prefreeze_v1.json")
SOURCE_OLD="SCBI-ForestGEO/SCBI-ForestGEO-Data"
OLD_SHA="9c6437afed3da292741840ab5ce327a4b54eff98"
SOURCE_2023="SCBI-ForestGEO/2023census"
TAG_COMMIT="6ac8718dcab0c5c653c56d55a1e093a6c20150e2"
BASE="https://api.github.com/repos"
MAX_METADATA_BYTES=5*1024*1024
LOCK="\n".join([
    f"program={PROGRAM}",
    f"public_2008_to_2018_git_commit={OLD_SHA}",
    f"public_2023_release_tag=2024.05",
    f"public_2023_release_git_commit={TAG_COMMIT}",
    "independent_forest=SCBI_Virginia_25.6ha",
    "only_exact_Git_tree_metadata_no_CSV_text_bytes=true",
    "no_tree_stem_status_species_or_mortality_columns_opened=true",
    "Git_blob_SHA1_not_raw_SHA256=true",
    "official_ForestGEO_master_data_request_required=true",
    "approved_master_version_not_available=true",
    "publication_use_blocked_before_approval_and_collaboration=true",
    "annual_mortality_2022plus_custom_terms_separate=true",
    "original_M5_ProductA_unchanged_ProductB_blocked=true",
])+"\n"


def validate_config(c:dict)->None:
    if c.get("schema")!="sdmr.scbi_independent_forest_governance_v1":
        raise ValueError("unknown_SCBI_governance_contract")
    if c.get("plot_area_ha")!=25.6 or c.get("physical_ecosystem_replicates")!=1:
        raise ValueError("physical_plot_grain_not_fixed")
    if (c.get("analysis_using_original_SCBI_tree_data_authorized") is not False
        or c.get("approval_or_scbi_version_from_PIs") is not None
        or c.get("original_approved_ForestGEO_master_data_available") is not False
        or c.get("original_public_CSV_bytes_not_opened") is not True
        or c.get("Git_blob_SHA1_is_NOT_raw_file_SHA256") is not True):
        raise ValueError("false_authorization_or_digest_claim")
    prev=c["provider_sources"]["earlier_public_copies"]
    nxt=c["provider_sources"]["public_2023_release"]
    if (prev["repository"]!=SOURCE_OLD or prev["exact_git_commit"]!=OLD_SHA
        or nxt["repository"]!=SOURCE_2023
        or nxt["published_release_tag"]!="2024.05"
        or nxt["published_release_tag_commit"]!=TAG_COMMIT
        or nxt["zenodo_doi"]!="10.5281/zenodo.11192302"
        or nxt["original_source_approved_for_this_research"] is not False):
        raise ValueError("exact_public_snapshot_lineage_changed")
    if len(prev["files"])!=3:
        raise ValueError("expected_2008_2013_2018_source_files_missing")
    if [p["period"] for p in prev["files"]] != [
        "2008-2010","2013","2018",
    ]:
        raise ValueError("original_census_time_operator_changed")
    approved=c["source_use_rules"]
    necessary=(
        "require_data_request_and_approved_master_version_before_analysis",
        "require_PI_collaborator_and_authorship_terms_per_official_site",
        "require_nontransferability_and_no_redistribution",
        "require_request_for_each_new_study_use",
        "citation_requires_approved_dataset_version",
        "separate_custom_mortality_use_agreement_for_years_2022_and_later",
    )
    if not all(approved.get(k) is True for k in necessary):
        raise ValueError("original_SCBI_PI_use_terms_weakened")
    if (c["scientific_admission"]["future_biological_analyses_blocked"] is not True
        or c["scientific_admission"]["2018_2023_census_status_opened"] is not False
        or c["scientific_admission"]["direct_HF453_CP_mortality_replication_not_permitted_with_current_crown_cohort"] is not True
        or c["frozen_methods_and_results"]["product_B_blocked"] is not True):
        raise ValueError("SCBI_response_access_or_mortality_promotion_without_approval")


class APIOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        require_api_path(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def require_api_path(url:str)->None:
    p=urlsplit(url)
    if (p.scheme!="https" or p.netloc!="api.github.com"
        or p.username or p.password or p.fragment
        or not p.path.startswith("/repos/SCBI-ForestGEO/")
        or "/git/trees/" not in p.path
        or p.query not in ("recursive=1","")):
        raise ValueError("not_frozen_GitHub_public_Git_tree_metadata_only")


def metadata_get(url:str)->dict:
    require_api_path(url)
    req=Request(url,headers={
        "Accept":"application/vnd.github+json",
        "User-Agent":"sdmr-scbi-original-metadata-only/1.0",
        "X-GitHub-Api-Version":"2022-11-28",
    })
    with build_opener(APIOnlyRedirect()).open(req,timeout=55) as r:
        require_api_path(r.geturl())
        body=r.read(MAX_METADATA_BYTES+1)
        if len(body)>MAX_METADATA_BYTES:
            raise ValueError("public_Git_tree_metadata_exceeds_byte_cap")
        result=json.loads(body)
        if not isinstance(result,dict):
            raise ValueError("public_Git_tree_expected_JSON_object")
        return result


def exact_public_git_tree(source:dict,expected_sha:str,
                          files:list[dict])->dict:
    if source.get("sha")!=expected_sha or source.get("truncated") is not False:
        raise ValueError("frozen_public_Git_tree_SHA_or_completeness_mismatch")
    raw=source.get("tree")
    if not isinstance(raw,list) or not raw:
        raise ValueError("original_public_Git_tree_entries_unavailable")
    by_path={x.get("path"):x for x in raw if isinstance(x,dict)}
    out=[]
    for f in files:
        row=by_path.get(f["path"])
        if row is None:
            raise ValueError("selected_original_Git_blob_missing:"+f["path"])
        if (row.get("type")!="blob" or row.get("mode")!="100644"
            or row.get("sha")!=f["git_blob_sha1"]
            or row.get("size")!=f["bytes"]):
            raise ValueError("selected_original_Git_blob_SHA1_or_bytes_changed:"+f["path"])
        out.append({
            "public_source_relative_path":f["path"],
            "public_Git_blob_SHA1":row["sha"],
            "public_Git_object_size_bytes":row["size"],
            "is_raw_complete_file_SHA256":False,
            "is_approved_original_ForestGEO_master":False,
        })
    return {"frozen_commit":expected_sha,
            "Git_tree_entries":len(raw),
            "selected_files":out,
            "selected_original_CSV_bytes_opened":False}


def run_metadata_only(cfg:dict)->dict:
    validate_config(cfg)
    prev=cfg["provider_sources"]["earlier_public_copies"]
    nxt=cfg["provider_sources"]["public_2023_release"]
    older_url=(f"{BASE}/{SOURCE_OLD}/git/trees/{OLD_SHA}?recursive=1")
    newer_url=(f"{BASE}/{SOURCE_2023}/git/trees/{TAG_COMMIT}?recursive=1")
    old=exact_public_git_tree(metadata_get(older_url),OLD_SHA,prev["files"])
    recent=exact_public_git_tree(metadata_get(newer_url),TAG_COMMIT,[{
        "path":nxt["source_path"],
        "bytes":nxt["bytes"],
        "git_blob_sha1":nxt["git_blob_sha1"],
    }])
    return {
        "status":"public_snapshots_Git_tree_metadata_verified_but_master_approval_pending",
        "first_source_public_history":old,
        "2023_published_Zenodo_tag_source":recent,
        "official_master_version_currently_approved":None,
        "source_full_byte_sha256_verified":False,
        "source_tree_stem_status_rows_opened":False,
        "new_independent_forest_biological_validation":False,
        "manuscript_ready_original_SCBI_data":False,
        "separate_2022plus_mortality_agreement_needed":True,
        "same_physical_forest_for_all_four_censuses":True,
        "Product_B_unblocked":False,
    }


def source_receipt(cfg:dict,*,preflight:bool)->dict:
    validate_config(cfg)
    if preflight:
        x={"status":"source_free_preflight_governance_contract_only"}
    else:
        try:
            x=run_metadata_only(cfg)
        except HTTPError as e:
            x={"status":"public_original_Git_metadata_HTTP_STOP",
               "reason":f"http_{e.code}"}
        except (URLError,TimeoutError,OSError):
            x={"status":"public_original_Git_metadata_access_STOP",
               "reason":"network_or_tls"}
        except (ValueError,KeyError,TypeError) as e:
            x={"status":"public_original_Git_metadata_integrity_STOP",
               "reason":type(e).__name__+":"+str(e)[:100]}
    return {
        "schema":"sdmr.scbi_independent_provider_metadata_only_first_v1",
        "program":PROGRAM,
        "preflight":preflight,
        "metadata_only":True,
        "raw_original_CSV_downloaded":False,
        "original_tree_data_approved_for_scientific_use":False,
        "full_original_biological_response_opened":False,
        "original_authorized_master_version_verified":False,
        "new_ecological_models_fit":0,
        "independent_field_process_test_performed":False,
        "original_M5_and_HF453_unchanged":True,
        "Product_B_unblocked":False,
        "result":x,
    }


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",type=Path,default=CFG)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--execute-lock",type=Path)
    a=ap.parse_args()
    if a.preflight_only==(a.execute_lock is not None):
        ap.error("choose exactly one --preflight-only or --execute-lock")
    cfg=json.loads(a.config.read_text())
    validate_config(cfg)
    if a.execute_lock and a.execute_lock.read_text()!=LOCK:
        raise ValueError("SCBI_original_source_metadata_authorization_lock_mismatch")
    result=source_receipt(cfg,preflight=a.preflight_only)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("SCBI original public snapshot vs official master gate:",result["result"]["status"])


if __name__=="__main__":
    main()
