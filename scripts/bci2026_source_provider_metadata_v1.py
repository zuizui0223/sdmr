#!/usr/bin/env python3
"""BCI 2026 Dryad independent original *metadata* first-open (no data files).

One data-provider API read for dataset, version list and five file manifests.
No download URLs are followed; no README data contents, organism observation
rows, status, census or 2025 exposure are read. All source claims fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError, URLError

PROGRAM = "sdmr_bci2026_dryad_original_metadata_first_version_v1"
CONFIG_PATH = Path("configs/bci2026_independent_source_metadata_prefreeze_v1.json")
BASE = "https://datadryad.org/api/v2"
DOI = "10.5061/dryad.1g1jwsvc3"
VERSION_DATE = "2026-08-31"
EXPECTED_FILES = {
    "Key_sp6.txt", "mainfile.txt", "Plot_UTM_coordinates.txt",
    "README.md", "stemfile.txt",
}
API_MAX_BYTES = 512 * 1024
LOCK_TEXT = "\n".join([
    f"program={PROGRAM}",
    f"doi={DOI}",
    f"edition_date={VERSION_DATE}",
    "role=independent_BCI_original_provider_metadata_no_biological_data",
    "files=Key_sp6.txt,mainfile.txt,Plot_UTM_coordinates.txt,README.md,stemfile.txt",
    "version_selection=exact_publication_date_not_latest",
    "no_download_of_original_main_stem_README_or_species_files=true",
    "no_auto_retry_or_alternate_editions=true",
    "no_2014_2025_exposure_as_baseline_survival_predictor=true",
    "missing_not_observed_death_future_recruit_not_observed_zero=true",
    "one_island_not_six_independent_ecosystems=true",
    "M5_ProductA_unchanged_ProductB_blocked=true",
]) + "\n"


class ProviderRedirectOnly(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_api_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def require_api_url(url: str) -> str:
    urlp = urlsplit(url)
    if (urlp.scheme != "https" or urlp.netloc != "datadryad.org" or
            not urlp.path.startswith("/api/v2/") or
            urlp.username or urlp.password or urlp.fragment):
        raise ValueError("source_API_URL_or_redirect_outside_Dryad")
    return url


def _api_get_json(url: str) -> dict:
    require_api_url(url)
    q = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "sdmr-bci-original-metadata-only/1.0",
    })
    with build_opener(ProviderRedirectOnly()).open(q, timeout=45) as resp:
        require_api_url(resp.geturl())
        # Limit metadata to avoid accidental retrieval of original source bytes.
        raw = resp.read(API_MAX_BYTES + 1)
        if len(raw) > API_MAX_BYTES:
            raise ValueError("provider_metadata_exceeds_fixed_byte_cap")
        if not raw.startswith(b"{"):
            raise ValueError("provider_API_did_not_return_JSON")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("provider_API_expected_JSON_object")
        return result


def validate_config(d: dict) -> None:
    if d.get("schema") != "sdmr.bci2026_independent_provider_metadata_gate.v1":
        raise ValueError("unknown_BCI_original_source_contract")
    if d.get("doi") != DOI or d.get("exact_api_base") != BASE:
        raise ValueError("BCI_DOI_or_API_domain_not_fixed")
    if d.get("exact_edition_publication_date") != VERSION_DATE:
        raise ValueError("source_edition_changed_after_frozen_protocol")
    if set(d.get("expected_original_filenames", [])) != EXPECTED_FILES or (
        len(d["expected_original_filenames"]) != 5
    ):
        raise ValueError("source_file_set_changed")
    if (d.get("census_labels") != [2004, 2014, 2025] or
            d.get("published_unique_tree_author_reported") != 15562 or
            d.get("expected_original_file_count") != 5):
        raise ValueError("BCI_original_published_study_grain_changed")
    if not d["semantically_protected_fields"]["exposure"].startswith(
            "measured in 2025 only"):
        raise ValueError("post_outcome_exposure_leakage_gate_changed")
    if (d.get("outcome_preadmission") !=
            "BLOCKED until full original publisher-file digest and sampling opportunity/attrition is audited and response protocol frozen" or
            d.get("product_B_blocked") is not True or
            d.get("original_file_sha256_verified") is not False or
            d.get("unobserved_forest_biological_data_opened") is not False):
        raise ValueError("original_BCI_response_admission_changed")


def _raw_embedded(source: dict, key: str) -> list:
    obj = source.get("_embedded") or {}
    records = obj.get(key)
    if not isinstance(records, list):
        raise ValueError("Dryad_API_embedded_collection_missing:" + key)
    return records


def _publication_date(x: dict) -> str | None:
    for name in ("publicationDate", "publication_date", "datePublished"):
        date = x.get(name)
        if isinstance(date, str):
            return date[:10]
    return None


def exact_version_descriptor(raw: dict) -> dict:
    # Page 1 response must contain the complete version list (normally 2).
    vers = _raw_embedded(raw, "stash:versions")
    total = raw.get("count", len(vers))
    if type(total) is int and total != len(vers):
        raise ValueError("Dryad_version_list_incomplete_no_automatic_pagination")
    selected = [v for v in vers if _publication_date(v) == VERSION_DATE]
    if len(selected) != 1:
        raise ValueError("target_revised_Aug31_2026_Dryad_edition_not_unique")
    v = selected[0]
    version_number = v.get("versionNumber")
    if type(version_number) is not int or version_number < 2:
        raise ValueError("revised_Dryad_version_number_missing_or_not_versioned")
    href = (v.get("_links") or {}).get("stash:files", {}).get("href")
    if not isinstance(href, str):
        raise ValueError("versioned_original_files_manifest_link_absent")
    if href.startswith("/"):
        full = "https://datadryad.org" + href
    else:
        full = href
    require_api_url(full)
    if not re.search(r"/versions/\d+/files(?:\?|$)", full):
        raise ValueError("Dryad_manifest_link_not_pinned_to_specific_version")
    return {
        "version_number": version_number,
        "publication_date": _publication_date(v),
        "file_manifest_api_url": full,
        "exact_version_url": str((v.get("_links") or {}).get("self", {}).get("href", "")),
        "number_of_provider_versions": len(vers),
    }


def manifest_summary(raw: dict) -> dict:
    entries = _raw_embedded(raw, "stash:files")
    total = raw.get("count", len(entries))
    if type(total) is int and total != len(entries):
        raise ValueError("Dryad_original_file_manifest_pagination_incomplete")
    by_name = {}
    for r in entries:
        name = r.get("path") or r.get("filename")
        if isinstance(name, str):
            name = name.rsplit("/", 1)[-1]
        if name not in EXPECTED_FILES or name in by_name:
            raise ValueError("unexpected_or_duplicate_Dryad_original_file")
        size = r.get("size", r.get("fileSize"))
        digest = r.get("digest")
        dtype = r.get("digestType")
        file_id = r.get("id")
        if (size is not None and (type(size) is not int or size < 1)):
            raise ValueError("Dryad_original_file_size_invalid")
        by_name[name] = {
            "name": name,
            "source_file_id": file_id if type(file_id) is int else None,
            "provider_file_bytes": size,
            "provider_digest": digest if isinstance(digest, str) else None,
            "provider_digest_type": dtype if isinstance(dtype, str) else None,
        }
    if set(by_name) != EXPECTED_FILES:
        raise ValueError("incomplete_exact_BCI_original_5file_release")
    fully_hash_pinned = all(
        isinstance(q["provider_digest"], str) and
        isinstance(q["provider_file_bytes"], int) and
        q["source_file_id"] is not None
        for q in by_name.values()
    )
    return {
        "status": ("provider_original_file_manifest_with_published_checksums"
                   if fully_hash_pinned else
                   "provider_original_file_manifest_missing_checksums_hold"),
        "files": [by_name[k] for k in sorted(by_name)],
        "n_original_source_files": len(by_name),
        "all_provider_digests_and_sizes_present": fully_hash_pinned,
        "raw_source_file_contents_opened": False,
    }


def metadata_gate_run() -> dict:
    api_doi = quote("doi:" + DOI, safe="")
    dataset_url = f"{BASE}/datasets/{api_doi}"
    versions_url = dataset_url + "/versions"
    dataset = _api_get_json(dataset_url)
    if dataset.get("identifier") not in ("doi:" + DOI, DOI):
        raise ValueError("Dryad_dataset_DOI_identity_mismatch")
    license_ = dataset.get("license")
    versions = exact_version_descriptor(_api_get_json(versions_url))
    m = manifest_summary(_api_get_json(versions["file_manifest_api_url"]))
    return {
        "status": m["status"],
        "dataset_doi": DOI,
        "provider_dataset_license": license_,
        "provider_dataset_version_currently_reported": dataset.get("versionNumber"),
        "selected_original_version": versions,
        "original_file_manifest": m,
        "source_API_exact_version_immutability_subject_to_Dryad_provider": True,
        "source_original_byte_SHA256_checked": False,
        "biological_tree_response_or_2025_exposure_opened": False,
    }


def run_once(d: dict) -> dict:
    validate_config(d)
    try:
        return metadata_gate_run()
    except HTTPError as exc:
        return {"status": "provider_API_unavailable_STOP",
                "reason": f"provider_http_{exc.code}",
                "original_source_rows_opened": False}
    except (URLError, OSError, TimeoutError):
        return {"status": "provider_API_unavailable_STOP",
                "reason": "network_or_tls_unavailable",
                "original_source_rows_opened": False}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        # Generic scientific validation category, never leak source payloads.
        return {"status": "provider_metadata_integrity_STOP",
                "reason": type(exc).__name__ + ":" + str(exc)[:120],
                "original_source_rows_opened": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=CONFIG_PATH)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--execute-lock", type=Path)
    o = p.parse_args()
    if o.preflight_only == (o.execute_lock is not None):
        p.error("exactly one preflight or execute-lock")
    conf = json.loads(o.config.read_text())
    validate_config(conf)
    if o.execute_lock and o.execute_lock.read_text() != LOCK_TEXT:
        raise ValueError("BCI_source_metadata_first_attempt_lock_changed")
    result = {"status": "preflight_source_unopened"} if o.preflight_only else run_once(conf)
    payload = {
        "schema": "sdmr.bci2026_original_source_provider_metadata_first_receipt.v1",
        "program": PROGRAM,
        "preflight": o.preflight_only,
        "provider": "Dryad",
        "fixed_doi": DOI,
        "fixed_edition_date": VERSION_DATE,
        "source_biological_rows_opened": False,
        "source_original_files_downloaded": 0,
        "new_ecological_models_fit": 0,
        "independent_forest_biological_validation_performed": False,
        "post2025_exposure_pre2025_survival_leakage_forbidden": True,
        "Product_B_unblocked": False,
        "result": result,
    }
    o.out.parent.mkdir(parents=True, exist_ok=True)
    o.out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print("BCI fixed original Dryad provider metadata:", result["status"])


if __name__ == "__main__":
    main()
