"""Source-only independent NEON RELEASE-2026 vegetation metadata gate.

Unlike FIA DataMart snapshots used in the previous SDMR growth analyses, the
NEON release is a distinct provider/survey. Only the public product catalog is
accessed; no data/table endpoint, API token, plant individual, DBH or status
is downloaded or inspected. Calendar availability is not repeated individuals.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PRODUCT = "DP1.10098.001"
RELEASE = "RELEASE-2026"
URL = "https://data.neonscience.org/api/v0/products/" + PRODUCT
DOI = "10.48443/pypa-qf12"
MIN_YEAR_SPAN = 4
MAX_METADATA_BYTES = 5_000_000
SITE_RE = re.compile(r"^[A-Z]{4}$")
MONTH_RE = re.compile(r"^(20[0-3][0-9])-(0[1-9]|1[0-2])$")


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def source_catalog(fetcher=None) -> dict:
    """A single GET of the public product METADATA. Not a NEON data endpoint."""
    if fetcher:
        payload = fetcher(URL)
    else:
        req = Request(URL, headers={"User-Agent": "sdmr-independent-neon-source-metadata-v1",
                                    "Accept": "application/json"})
        with urlopen(req, timeout=40) as response:
            raw = response.read(MAX_METADATA_BYTES + 1)
        if len(raw) > MAX_METADATA_BYTES:
            raise ValueError("public metadata exceeded declared size cap")
        payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("NEON public metadata response has missing data object")
    return payload


def audit_public_catalog(payload: dict) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("missing NEON catalog data")
    data = payload["data"]
    if data.get("productCode") != PRODUCT:
        raise ValueError("wrong NEON vegetation structure product")
    sites = data.get("siteCodes")
    if not isinstance(sites, list) or not sites:
        raise ValueError("NEON site catalog unavailable, not zero eligible sites")
    seen_sites: set[str] = set()
    complete = []
    for item in sites:
        if not isinstance(item, dict):
            raise ValueError("invalid NEON site record")
        code = item.get("siteCode")
        if not isinstance(code, str) or not SITE_RE.fullmatch(code):
            raise ValueError("invalid or missing four-letter NEON site code")
        if code in seen_sites:
            raise ValueError("duplicate NEON site identifier")
        seen_sites.add(code)
        releases = item.get("availableReleases", [])
        if releases is None:
            releases = []
        if not isinstance(releases, list):
            raise ValueError("invalid release list")
        matching = [z for z in releases if isinstance(z, dict) and z.get("release") == RELEASE]
        if len(matching) > 1:
            raise ValueError("duplicate same-release availability at one site")
        months: list[str] = []
        if matching:
            v = matching[0].get("availableMonths", [])
            if not isinstance(v, list):
                raise ValueError("invalid release-month availability")
            for m in v:
                if not isinstance(m, str) or not MONTH_RE.fullmatch(m):
                    raise ValueError("invalid month in released NEON site availability")
                months.append(m)
        if len(months) != len(set(months)):
            raise ValueError("duplicate NEON site-month in release catalog")
        years = sorted({int(m[:4]) for m in months})
        span = years[-1] - years[0] if years else None
        complete.append({
            "site": code, "release_months": sorted(months),
            "n_release_months": len(months),
            "n_release_years": len(years),
            "earliest_release_year": years[0] if years else None,
            "latest_release_year": years[-1] if years else None,
            "release_year_span": span,
            "candidate_time_span_ge_four_years": span is not None and span >= MIN_YEAR_SPAN,
            "n_verified_repeat_tree_individuals": None,
            "available_release_months_are_not_verified_survey_events": True,
        })
    complete.sort(key=lambda d: d["site"])
    if not any(item["n_release_months"] > 0 for item in complete):
        raise ValueError("target NEON release unavailable; cannot infer zero candidate sites")
    n_span = sum(x["candidate_time_span_ge_four_years"] for x in complete)
    return {
        "program": "sdmr_independent_NEON_vegetation_structure_public_catalog_v1",
        "status": "metadata_only_no_tree_response_observed",
        "source_provider": "NSF_NEON_distinct_from_USDA_FIA",
        "product_code": PRODUCT, "release": RELEASE, "release_doi": DOI,
        "public_metadata_url": URL,
        "n_sites_catalog_total": len(complete),
        "n_sites_with_released_months": sum(x["n_release_months"] > 0 for x in complete),
        "n_sites_with_2_plus_distinct_release_years": sum(x["n_release_years"] >= 2 for x in complete),
        "n_sites_with_available_release_year_span_ge_four": n_span,
        "n_sites_with_verified_repeated_individuals": None,
        "sites": complete,
        "frozen_fia_species_of_interest": ["129","316","802","833","837"],
        "neon_taxonomy_and_FIA_species_crosswalk_verified": False,
        "forest_plot_revisit_coverage_verified": False,
        "survey_effort_plot_area_verified": False,
        "multi_stem_tempStemID_not_longitudinally_stable": True,
        "later_growth_and_survival_data_accessed": False,
        "NEON_raw_file_endpoint_requires_account_token": True,
        "no_biological_promotion_authorized": True,
        "prior_FIA_product_A_M5_and_product_B_unchanged": True,
    }


def run(output_dir: Path, *, fetcher=None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        payload = source_catalog(fetcher=fetcher)
        result = audit_public_catalog(payload)
        data_bytes = canonical_bytes(payload)
        if len(data_bytes) > MAX_METADATA_BYTES:
            raise ValueError("canonical NEON metadata size exceeded cap")
        result["source_metadata_canonical_json_sha256"] = hashlib.sha256(data_bytes).hexdigest()
        result["source_accession_measured_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        (output_dir/"neon_release_2026_public_product_metadata.json").write_bytes(data_bytes + b"\n")
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
        result = {
            "program": "sdmr_independent_NEON_vegetation_structure_public_catalog_v1",
            "status": "public_metadata_unavailable_not_zero_sites",
            "error_class": type(exc).__name__,
            "error_message_excerpt": str(exc)[:160],
            "n_sites_with_verified_repeated_individuals": None,
            "no_raw_data_accessed": True,
            "no_biological_promotion_authorized": True,
        }
    (output_dir/"neon_release_2026_source_gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    a = parser.parse_args()
    result = run(a.out_dir)
    print(result["status"], "sites", result.get("n_sites_catalog_total"),
          "four-year available spans", result.get("n_sites_with_available_release_year_span_ge_four"),
          "verified repeated individuals", result.get("n_sites_with_verified_repeated_individuals"))
    if result["status"] != "metadata_only_no_tree_response_observed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
