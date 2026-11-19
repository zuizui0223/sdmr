#!/usr/bin/env python3
"""HF453 v2 source-identity audit after first UTF-8 decoding STOP.

Independent of the prior provider-byte check, which must be reproduced
exactly. This successor can index original tree tags/years only *after*
full-file SHA256 AND publisher MD5 equal frozen source receipts. It does
not access status, CP, health, growth, species, forest effects or Y.
Original rows are NOT archived; only aggregate identity/opportunity counts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256, md5
import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from hf453_original_byte_preflight_v1 import (
    DOI, SOURCE_ID, SOURCE_URL, PUBLISHER_VERSION,
    PUBLISHER_MD5, MAX_SOURCE_BYTES, LOCK_CONTENT as ORIGINAL_LOCK,
    ProviderOnlyRedirect, require_provider_https,
)

PROGRAM = "sdmr_hf453_original_tag_year_identity_source_only_v2"
EXPECTED_ORIGINAL_SHA256 = "0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74"
EXPECTED_ORIGINAL_NBYTES = 5524386
YEARS = (2021, 2022, 2023, 2024)
LOCK_CONTENT = "\n".join([
    f"program={PROGRAM}",
    f"source={SOURCE_ID}",
    f"publisher_version={PUBLISHER_VERSION}",
    f"doi={DOI}",
    f"exact_previous_sha256={EXPECTED_ORIGINAL_SHA256}",
    f"exact_previous_bytes={EXPECTED_ORIGINAL_NBYTES}",
    f"published_md5={PUBLISHER_MD5}",
    "only_original_StemTag_and_year_indexed=true",
    "first_identity_attempt_stop=UnicodeDecodeError_run_44476932274",
    "byte_decode=latin1_only_ASCII_identifiers",
    "do_not_index_status_CP_health_taxon_death=true",
    "no_raw_CSV_archived=true",
    "no_automatic_retry=true",
    "source_only_not_biological_effect=true",
    "M5_and_ProductA_unchanged_ProductB_blocked=true",
]) + "\n"


def scan_identity_only(datafile) -> dict:
    """Index only StemTag and year; other CSV cells are transiently tokenized.

    The source includes non-UTF-8 bytes in an unspecified column. Latin-1
    reversibly maps all raw bytes and leaves ASCII tag/year unchanged.
    Never interpret or retain any biological text or non-ASCII identifier.
    """
    reader = csv.reader(datafile)
    header = next(reader, None)
    # Preserve only the ASCII CSV header; allow an optional UTF-8 BOM at start.
    if header and header[0].startswith("\xef\xbb\xbf"):
        header[0] = header[0][3:]
    if header is None or len(set(header)) != len(header):
        raise ValueError("empty_or_duplicated_CSV_header")
    if "StemTag" not in header or "year" not in header:
        raise ValueError("original_StemTag_year_fields_missing")
    tag_i, year_i = header.index("StemTag"), header.index("year")
    present: dict[str, set[int]] = {}
    seen: set[tuple[str, int]] = set()
    year_counts: Counter[int] = Counter()
    duplicate_tag_year = 0
    invalid_tag_or_year = 0
    n_rows = 0
    for row in reader:
        n_rows += 1
        if len(row) != len(header):
            invalid_tag_or_year += 1
            continue
        tag = row[tag_i]
        year_txt = row[year_i]
        if (not tag or not tag.isascii() or tag != tag.strip() or
                not year_txt.isascii() or year_txt not in tuple(map(str, YEARS))):
            invalid_tag_or_year += 1
            continue
        year = int(year_txt)
        key = (tag, year)
        if key in seen:
            duplicate_tag_year += 1
        seen.add(key)
        present.setdefault(tag, set()).add(year)
        year_counts[year] += 1
    census_tag_sets = {yr: {tag for tag, ys in present.items() if yr in ys} for yr in YEARS}
    overlap = {
        f"{y}_to_{y+1}": len(census_tag_sets[y] & census_tag_sets[y + 1])
        for y in YEARS[:-1]
    }
    if invalid_tag_or_year:
        status = "identity_source_fields_invalid_stop"
    elif duplicate_tag_year:
        status = "duplicate_original_tag_year_stop"
    elif not present or not all(year_counts[y] > 0 for y in YEARS):
        status = "identity_year_frame_incomplete_stop"
    else:
        status = "tag_year_source_identity_indexed_only"

    return {
        "status": status,
        "n_original_rows": n_rows,
        "n_distinct_tag_year": len(seen),
        "n_distinct_StemTag": len(present),
        "n_duplicate_tag_year": duplicate_tag_year,
        "n_invalid_StemTag_year": invalid_tag_or_year,
        "n_record_rows_by_year": {str(y):year_counts[y] for y in YEARS},
        "n_tag_year_matched_by_adjacent_census": overlap,
        "n_tags_recorded_two_plus_years": sum(len(ys) >= 2 for ys in present.values()),
        "n_tags_recorded_all_four_years": sum(len(ys) == 4 for ys in present.values()),
        "physical_tag_stability_author_verified": False,
        "actual_survey_effort_verified": False,
        "alive_at_risk_denominator_estimated": False,
        "not_present_next_census_is_not_observed_death": True,
        "status_or_CP_columns_indexed": False,
        "biological_outcome_rows_interpreted": False,
        "taxon_or_forest_effect_estimated": False,
    }


def _download_and_hash_original(temp_path: Path) -> dict:
    require_provider_https(SOURCE_URL)
    request = Request(
        SOURCE_URL,
        headers={"User-Agent":"sdmr-hf453-tag-year-source-audit/1.0",
                 "Accept":"text/csv,application/octet-stream"},
    )
    sha, d5 = sha256(), md5()
    size = 0
    opener = build_opener(ProviderOnlyRedirect())
    with opener.open(request, timeout=45) as f, temp_path.open("wb") as w:
        require_provider_https(f.geturl())
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_SOURCE_BYTES:
                raise ValueError("source_byte_limit_stop")
            sha.update(chunk); d5.update(chunk)
            w.write(chunk)
    return {"sha256":sha.hexdigest(),"md5":d5.hexdigest(),"n_bytes":size}


def audit_first_tag_year_source() -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix="sdmr_hf453_source_v1_") as temp:
            path = Path(temp) / "raw_source_not_retained.csv"
            checksum = _download_and_hash_original(path)
            if (checksum["sha256"] != EXPECTED_ORIGINAL_SHA256 or
                    checksum["md5"] != PUBLISHER_MD5 or
                    checksum["n_bytes"] != EXPECTED_ORIGINAL_NBYTES):
                return {
                    "status":"original_frozen_source_byte_mismatch_stop",
                    "source_digests":checksum,
                    "source_identity_opened":False,
                    "reason":"cannot parse original identity after source-version drift",
                }
            # The file has passed the frozen complete-byte identity barrier.
            with path.open("r", encoding="latin-1", newline="") as h:
                indexed = scan_identity_only(h)
            return {
                "status":indexed["status"],
                "source_digests":checksum,
                "source_identity_opened":True,
                "identity_only":indexed,
            }
    except HTTPError as ex:
        return {
            "status":"original_source_fetch_unavailable_stop",
            "source_identity_opened":False,
            "reason":f"http_{ex.code}",
        }
    except (URLError, TimeoutError, ConnectionError, OSError):
        return {
            "status":"original_source_fetch_unavailable_stop",
            "source_identity_opened":False,
            "reason":"network_or_tls_unavailable",
        }
    except (UnicodeError, csv.Error, ValueError) as ex:
        # Exact error category only; never print any raw source row.
        return {
            "status":"original_source_identity_read_stop",
            "source_identity_opened":False,
            "reason":type(ex).__name__,
        }


def receipt(*, preflight: bool, result: dict | None = None) -> dict:
    return {
        "schema":"sdmr.hf453_tag_year_source_only.v1",
        "program":PROGRAM,
        "source":SOURCE_ID,
        "publisher_version":PUBLISHER_VERSION,
        "source_doi":DOI,
        "frozen_source_sha256":EXPECTED_ORIGINAL_SHA256,
        "frozen_source_md5":PUBLISHER_MD5,
        "source_commit":os.getenv("GITHUB_SHA"),
        "preflight":preflight,
        "network_get_attempted":not preflight,
        "only_StemTag_year_indexed":True,
        "non_ASCII_biological_fields_not_interpreted": True,
        "latin1_decoding_applied_only_to_locate_ASCII_columns": True,
        "status_CP_health_taxon_columns_not_used":True,
        "original_source_file_archived":False,
        "new_tree_response_opened":False,
        "new_biological_models_fit":0,
        "new_biological_inference_authorized":False,
        "Product_B_unblocked":False,
        "result":result if result is not None else {"status":"preflight_unopened"},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute-lock", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    opts = parser.parse_args()
    if opts.preflight_only == (opts.execute_lock is not None):
        parser.error("exactly one of --execute-lock or --preflight-only required")
    if opts.execute_lock is not None:
        if opts.execute_lock.read_text(encoding="utf-8") != LOCK_CONTENT:
            raise ValueError("frozen second-stage original-source lock mismatch")
    data = receipt(preflight=opts.preflight_only,
                   result=None if opts.preflight_only else audit_first_tag_year_source())
    opts.out.parent.mkdir(parents=True, exist_ok=True)
    opts.out.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    print("HF453 original source-only tag/year:",data["result"]["status"])
    print("No source status, CP, outcome, taxon or growth values indexed")


if __name__ == "__main__":
    main()
