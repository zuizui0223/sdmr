"""NEON RELEASE-2026: optional-token FILE-MANIFEST-ONLY preflight, no tree rows.

A source-only pilot on two predeclared forest sites, two fixed archive months
per site. This stage never opens the returned CSV/download URLs. It only
checks the presence of the 2026 schema tables and whether the repository
has an API token, without printing the token or expiring signed URLs.
All biology (individuals, statuses, diameter, death, growth) stays UNKNOWN.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener

PRODUCT = "DP1.10098.001"
RELEASE = "RELEASE-2026"
ORIGINAL_PUBLIC_CATALOG_SHA = "0ba89ff5835ea54071e7a8f12f05b5ca928cec05a1dd424660727de4f94d9bcf"
ORIGINAL_PUBLIC_RECEIPT_SHA = "29699a799b5fc09411b952548f371b7f27545d4b0f73d479590576f63937021f"
PILOT = (("HARV", "2014-08"), ("HARV", "2024-08"),
         ("SCBI", "2014-08"), ("SCBI", "2024-09"))
REQUIRED_TABLES = ("vst_perplotperyear", "vst_apparentindividual", "vst_mappingandtagging")
MAX_MANIFEST_BYTES = 1_500_000
BASE_URL = "https://data.neonscience.org/api/v0/data"
NAME_PATTERN = re.compile(r"\.(vst_perplotperyear|vst_apparentindividual|vst_mappingandtagging)\.", re.I)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def audit_frozen_catalog(catalog: Path, receipt: Path) -> None:
    if sha_file(catalog) != ORIGINAL_PUBLIC_CATALOG_SHA:
        raise ValueError("original NEON public product metadata changed")
    if sha_file(receipt) != ORIGINAL_PUBLIC_RECEIPT_SHA:
        raise ValueError("original NEON public catalog receipt changed")
    raw = json.loads(catalog.read_text(encoding="utf-8"))
    proof = json.loads(receipt.read_text(encoding="utf-8"))
    if (raw.get("data", {}).get("productCode") != PRODUCT or
        proof.get("status") != "metadata_only_no_tree_response_observed" or
        proof.get("release") != RELEASE):
        raise ValueError("not the frozen public source-only NEON cohort")
    sites = {s.get("siteCode"): s for s in raw.get("data", {}).get("siteCodes", [])}
    for site, month in PILOT:
        record = sites.get(site)
        if not record:
            raise ValueError("pilot site absent from immutable public catalog")
        releases = [x for x in record.get("availableReleases", []) if x.get("release") == RELEASE]
        if len(releases) != 1 or month not in releases[0].get("availableMonths", []):
            raise ValueError("pilot month unavailable in frozen public source catalog")


class SameOriginOnly(HTTPRedirectHandler):
    """Do not forward an API token to redirected, third-party signed URLs."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        old, new = urlsplit(request.full_url), urlsplit(newurl)
        if new.scheme != "https" or old.hostname != new.hostname:
            raise ValueError("cross-origin redirect refused before any token forwarding")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def manifest_request(site: str, month: str, token: str, *, fetcher=None) -> dict:
    if (site, month) not in PILOT:
        raise ValueError("unregistered NEON site-month probe")
    if not token or "\r" in token or "\n" in token:
        raise ValueError("NEON auth token not present or malformed")
    url = f"{BASE_URL}/{PRODUCT}/{site}/{month}?{urlencode({'release': RELEASE, 'package': 'basic'})}"
    if fetcher is not None:
        response = fetcher(url, token)
    else:
        opener = build_opener(SameOriginOnly())
        req = Request(url, headers={"X-API-Token": token, "Accept": "application/json",
                                    "User-Agent": "sdmr-neon-source-manifest-no-raw-trees-v1"})
        with opener.open(req, timeout=35) as fp:
            raw = fp.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError("NEON source file manifest exceeds size cap")
        response = json.loads(raw)
    if not isinstance(response, dict) or not isinstance(response.get("data"), dict):
        raise ValueError("NEON source manifest has no data section")
    return response


def summarize_manifest(data: dict, site: str, month: str) -> dict:
    """Public file metadata only. Deliberately remove ALL signed file URLs."""
    payload = data["data"]
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("no file manifest entries; this is not zero tree records")
    inventory = []
    counts = Counter()
    for file in files:
        if not isinstance(file, dict):
            raise ValueError("invalid file metadata entry")
        name = file.get("name")
        if not isinstance(name, str) or not name.startswith("NEON.") or f".{site}." not in name or f".{PRODUCT}." not in name:
            raise ValueError("file metadata source/site/product inconsistency")
        if name in {x["name"] for x in inventory}:
            raise ValueError("duplicate source file name in one manifest")
        match = NAME_PATTERN.search(name)
        table = match.group(1).lower() if match else None
        if table:
            counts[table] += 1
        n = file.get("size")
        if isinstance(n, bool) or (n is not None and (not isinstance(n, (int, float)) or n < 0)):
            raise ValueError("invalid file size for NEON source")
        inventory.append({"name": name, "size_bytes": int(n) if n is not None else None,
                          "table": table})
    return {
        "site": site, "month": month, "n_files": len(inventory),
        "required_table_counts": {x: counts[x] for x in REQUIRED_TABLES},
        "required_tables_each_present_once": all(counts[x] == 1 for x in REQUIRED_TABLES),
        "file_metadata_manifest_sha256": hashlib.sha256(canonical(data)).hexdigest(),
        "files_without_URLs": inventory,
        "any_signed_file_urls_archived": False,
        "individualID_or_growth_data_read": False,
    }


def run(catalog: Path, source_receipt: Path, outdir: Path,
        token: str | None = None, *, fetcher=None) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    base = {
        "program": "sdmr_NEON_2026_independent_first_file_manifest_pilot_v1",
        "product": PRODUCT, "release": RELEASE,
        "n_planned_site_months": len(PILOT),
        "pilot_site_months": [{"site": s, "month": m} for s, m in PILOT],
        "n_distinct_pilot_sites": 2,
        "original_public_catalog_sha256": ORIGINAL_PUBLIC_CATALOG_SHA,
        "original_public_catalog_receipt_sha256": ORIGINAL_PUBLIC_RECEIPT_SHA,
        "raw_vegetation_tables_downloaded": False,
        "per_tree_response_status_diameter_evaluated": False,
        "individual_repeat_status_verified": None,
        "prior_five_tree_species_presence_verified": None,
        "plot_area_and_sampling_design_verified": None,
        "NEON_2026_mappingandtagging_lacks_eventID": True,
        "TEMP_individualID_not_longitudinally_stable": True,
        "multi_stem_tempStemID_not_longitudinally_stable": True,
        "pilot_sites_not_source_independent_replication": True,
        "previous_FIA_results_and_Product_A_M5_unchanged_Product_B_blocked": True,
        "biological_promotion_authorized": False,
    }
    try:
        audit_frozen_catalog(catalog, source_receipt)
        base["frozen_catalog_verified"] = True
        if not token:
            base.update({"status": "no_NEON_API_TOKEN_secret_configured_no_network_data_request",
                         "n_manifest_requests": 0, "n_manifest_table_sets_confirmed": None})
        else:
            items = []
            for site, month in PILOT:
                try:
                    metadata = manifest_request(site, month, token, fetcher=fetcher)
                    result = summarize_manifest(metadata, site, month)
                    result["status"] = ("table_manifest_ready" if result["required_tables_each_present_once"]
                                       else "required_source_table_missing_or_ambiguous")
                except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as exc:
                    result = {"site": site, "month": month, "status": "manifest_unavailable_not_zero_trees",
                              "error_class": type(exc).__name__,
                              "http_status": int(exc.code) if isinstance(exc, HTTPError) else None}
                items.append(result)
            base["site_month_manifests"] = items
            base["n_manifest_requests"] = len(items)
            base["n_manifest_table_sets_confirmed"] = sum(
                x["status"] == "table_manifest_ready" for x in items)
            base["status"] = ("all_pilot_file_manifests_available_no_raw_data"
                              if base["n_manifest_table_sets_confirmed"] == len(PILOT)
                              else "pilot_file_manifest_incomplete_stop_before_any_raw_data")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        base.update({"status": "frozen_public_source_catalog_unavailable_stop",
                     "error_class": type(exc).__name__,
                     "error_message_excerpt": str(exc)[:150],
                     "n_manifest_requests": 0,
                     "n_manifest_table_sets_confirmed": None})
    outfile = outdir / "neon_2026_file_manifest_source_gate.json"
    outfile.write_text(json.dumps(base, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-catalog", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.public_catalog, args.public_receipt, args.out_dir,
                 token=os.getenv("NEON_API_TOKEN"))
    print(result["status"], "pilot site-months", result["n_planned_site_months"],
          "source table sets", result.get("n_manifest_table_sets_confirmed"),
          "biological tests 0")
    # Authentication, source/missingness, and validity all require an explicit
    # STOP result. No retry or implicit biological continuation is authorized.


if __name__ == "__main__":
    main()
