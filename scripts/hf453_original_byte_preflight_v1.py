#!/usr/bin/env python3
"""HF453 v1 original-file *byte identity* check; no biological row parsing.

One first-open original HTTPS GET, immutable endpoint/version/published MD5,
bounded streaming hash, no raw file persistence, and fail-closed receipt.
An observed MD5 match alone never licenses ecological response opening.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256, md5
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPRedirectHandler, Request, build_opener,
)

PROGRAM = "sdmr_hf453_first_publisher_byte_identity_v1"
SOURCE_ID = "harvard_forest_hf453_2026_v1"
DOI = "10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193"
PUBLISHER_VERSION = "knb-lter-hfr.453.1"
FILENAME = "hf453-01-tree-census-2021-2024.csv"
SOURCE_URL = (
    "https://harvardforest.fas.harvard.edu/data/p45/hf453/"
    + FILENAME
)
PUBLISHER_MD5 = "c6be7aa99e31ded2041a0aaea07c0205"
ALLOWED_HOSTS = frozenset({
    "harvardforest.fas.harvard.edu",
    "harvardforest1.fas.harvard.edu",
})
MAX_SOURCE_BYTES = 48 * 1024 * 1024
LOCK_CONTENT = "\n".join([
    f"program={PROGRAM}",
    f"source={SOURCE_ID}",
    f"publisher_version={PUBLISHER_VERSION}",
    f"doi={DOI}",
    f"filename={FILENAME}",
    f"published_md5={PUBLISHER_MD5}",
    "one_source_url_only=true",
    "parse_biological_rows=forbidden",
    "archive_raw_rows=forbidden",
    "no_automatic_network_retry=true",
    "model_fit=forbidden",
    "original_M5_ProductA_ProductB_unchanged=true",
]) + "\n"


class UnsafeSourceUrl(ValueError):
    pass


def require_provider_https(url: str) -> str:
    """Reject mutation to another host, HTTP, credentials, queries or fragments."""
    info = urlparse(url)
    if (info.scheme != "https" or info.hostname not in ALLOWED_HOSTS or
            info.username or info.password or info.query or info.fragment or
            info.port not in (None, 443) or
            not info.path.endswith("/" + FILENAME)):
        raise UnsafeSourceUrl("out-of-contract source host/url")
    return str(info.hostname)


class ProviderOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_provider_https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def byte_digests(chunks, *, max_bytes: int = MAX_SOURCE_BYTES) -> dict:
    """Stream arbitrary byte chunks without keeping them or parsing rows."""
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("positive byte cap required")
    sha, d5 = sha256(), md5()
    size = 0
    for chunk in chunks:
        if not isinstance(chunk, bytes):
            raise TypeError("binary source stream required")
        size += len(chunk)
        if size > max_bytes:
            raise ValueError("raw_provider_file_exceeds_predeclared_byte_cap")
        sha.update(chunk)
        d5.update(chunk)
    if size < 1:
        raise ValueError("raw_provider_file_empty")
    return {"sha256": sha.hexdigest(), "md5": d5.hexdigest(), "bytes": size}


def read_chunks(stream):
    """Only yield raw bytes; do not decode or split CSV rows."""
    while True:
        block = stream.read(1024 * 1024)
        if not block:
            break
        yield block


def check_publisher_bytes() -> dict:
    require_provider_https(SOURCE_URL)
    req = Request(
        SOURCE_URL,
        headers={"User-Agent": "sdmr-hf453-source-byte-proof/1.0",
                 "Accept": "text/csv,application/octet-stream"},
    )
    opener = build_opener(ProviderOnlyRedirect())
    try:
        with opener.open(req, timeout=45) as response:
            final_host = require_provider_https(response.geturl())
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > MAX_SOURCE_BYTES:
                raise ValueError("raw_provider_file_exceeds_predeclared_byte_cap")
            out = byte_digests(read_chunks(response))
            return {
                "status": (
                    "original_byte_md5_matched_source_only"
                    if out["md5"] == PUBLISHER_MD5
                    else "publisher_md5_drift_stop"
                ),
                "bytes_complete": True,
                "provider_host": final_host,
                "sha256": out["sha256"],
                "md5": out["md5"],
                "n_original_bytes": out["bytes"],
                "publisher_md5_matched": out["md5"] == PUBLISHER_MD5,
                "stop_reason": None if out["md5"] == PUBLISHER_MD5 else "md5_mismatch",
            }
    except HTTPError as exc:
        return {
            "status": "original_source_unavailable_stop",
            "bytes_complete": False,
            "stop_reason": f"http_status_{exc.code}",
        }
    except (URLError, TimeoutError, ConnectionError, OSError):
        return {
            "status": "original_source_unavailable_stop",
            "bytes_complete": False,
            "stop_reason": "network_or_tls_unavailable",
        }
    except (ValueError, UnsafeSourceUrl):
        return {
            "status": "original_source_integrity_stop",
            "bytes_complete": False,
            "stop_reason": "source_url_or_size_contract_failed",
        }


def source_receipt(*, preflight_only: bool, source: dict | None = None) -> dict:
    if source is None:
        source = {
            "status": "preflight_unopened",
            "bytes_complete": False,
            "stop_reason": None,
        }
    return {
        "schema": "sdmr.hf453_original_byte_first_open.v1",
        "program": PROGRAM,
        "study": SOURCE_ID,
        "source_doi": DOI,
        "source_eml_version": PUBLISHER_VERSION,
        "fixed_filename": FILENAME,
        "fixed_original_url": SOURCE_URL,
        "published_md5_expected": PUBLISHER_MD5,
        "source_commit": os.getenv("GITHUB_SHA"),
        "requested_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_only": preflight_only,
        "original_network_get_attempted": not preflight_only,
        "no_second_provider_or_version_fallback": True,
        "raw_bytes_retained": False,
        "source_rows_decoded": False,
        "biological_responses_inspected": False,
        "n_new_biological_models": 0,
        "new_biological_endpoint_test_authorized": False,
        "same_frozen_M5_and_ProductA": True,
        "Product_B_unblocked": False,
        "result": source,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--execute-lock", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only == (args.execute_lock is not None):
        parser.error("exactly one of --preflight-only and --execute-lock required")
    require_provider_https(SOURCE_URL)
    if args.execute_lock is not None:
        if args.execute_lock.read_text(encoding="utf-8") != LOCK_CONTENT:
            raise ValueError("one-shot source-only lock mismatch")
    receipt = source_receipt(
        preflight_only=args.preflight_only,
        source=None if args.preflight_only else check_publisher_bytes(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print("HF453_PROVIDER_BYTE_STATUS:", receipt["result"]["status"])
    print("NO biological rows decoded, no source CSV archived, no model fits")


if __name__ == "__main__":
    main()
