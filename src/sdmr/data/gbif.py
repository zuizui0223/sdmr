"""Small, reproducible GBIF API client for SDMR pilot datasets.

The search API is intentionally treated as a *pilot* route. GBIF caps individual
search pages at 300 records and search pagination at 100,000 records; corpus-scale
runs should therefore use a versioned GBIF occurrence download instead of trying
to crawl the search endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

GBIF_API = "https://api.gbif.org"
GBIF_SEARCH_PAGE_MAX = 300
GBIF_SEARCH_HARD_MAX = 100_000


class GBIFBulkDownloadRequired(RuntimeError):
    """Raised when the occurrence-search route cannot retrieve a full query."""


@dataclass(frozen=True)
class GBIFTaxonMatch:
    query_name: str
    taxon_key: str
    canonical_name: str
    rank: str
    status: str
    raw: Mapping[str, Any]


@dataclass
class GBIFSearchResult:
    records: pd.DataFrame
    query: dict[str, Any]
    total_count: int
    retrieved_count: int
    truncated: bool
    query_sha256: str


def _http_get_json(url: str, params: Mapping[str, Any], *, timeout: int = 60) -> dict[str, Any]:
    query = urlencode(params, doseq=True)
    request = Request(
        f"{url}?{query}",
        headers={"User-Agent": "sdmr/0.2 (+https://github.com/zuizui0223/sdmr)"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS API host by default
        return json.loads(response.read().decode("utf-8"))


def _fingerprint_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def match_taxon(
    scientific_name: str,
    *,
    get_json: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> GBIFTaxonMatch:
    """Resolve a scientific name through GBIF's v2 species-match service.

    If the response contains an accepted usage, the accepted usage is preferred
    for the occurrence query while the complete response is retained for audit.
    """

    if not scientific_name.strip():
        raise ValueError("scientific_name must not be empty")
    fetch = get_json or _http_get_json
    raw = dict(fetch(f"{GBIF_API}/v2/species/match", {"scientificName": scientific_name.strip()}))
    usage = raw.get("acceptedUsage") or raw.get("usage") or {}
    key = usage.get("key")
    if key in (None, ""):
        raise ValueError(f"GBIF did not return a usable taxon key for {scientific_name!r}")
    return GBIFTaxonMatch(
        query_name=scientific_name.strip(),
        taxon_key=str(key),
        canonical_name=str(usage.get("canonicalName") or usage.get("name") or scientific_name.strip()),
        rank=str(usage.get("rank") or ""),
        status=str(usage.get("status") or ""),
        raw=raw,
    )


def _normalize_search_records(records: list[Mapping[str, Any]]) -> pd.DataFrame:
    """Map selected GBIF search fields onto SDMR's stable occurrence schema."""

    rows: list[dict[str, Any]] = []
    for rec in records:
        rows.append(
            {
                "gbifID": rec.get("key") or rec.get("gbifID"),
                "taxonKey": rec.get("taxonKey"),
                "acceptedTaxonKey": rec.get("acceptedTaxonKey"),
                "scientificName": rec.get("scientificName"),
                "acceptedScientificName": rec.get("acceptedScientificName"),
                "species": rec.get("species") or rec.get("acceptedScientificName") or rec.get("scientificName"),
                "taxonRank": rec.get("taxonRank"),
                "family": rec.get("family"),
                "genus": rec.get("genus"),
                "longitude": rec.get("decimalLongitude"),
                "latitude": rec.get("decimalLatitude"),
                "coordinateUncertaintyInMeters": rec.get("coordinateUncertaintyInMeters"),
                "year": rec.get("year"),
                "eventDate": rec.get("eventDate"),
                "basisOfRecord": rec.get("basisOfRecord"),
                "occurrenceStatus": rec.get("occurrenceStatus"),
                "datasetKey": rec.get("datasetKey"),
                "institutionCode": rec.get("institutionCode"),
                "countryCode": rec.get("countryCode"),
                "issues": rec.get("issues"),
            }
        )
    return pd.DataFrame(rows)


def fetch_occurrence_search(
    taxon_key: str | int,
    *,
    max_records: int | None = 3_000,
    page_size: int = GBIF_SEARCH_PAGE_MAX,
    extra_params: Mapping[str, Any] | None = None,
    get_json: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> GBIFSearchResult:
    """Fetch a reproducible GBIF occurrence-search pilot for one resolved taxon.

    ``max_records=None`` requests the full result *only if* GBIF reports <=100k
    matches. Larger queries raise :class:`GBIFBulkDownloadRequired` instead of
    silently truncating the biological dataset.
    """

    if page_size < 1 or page_size > GBIF_SEARCH_PAGE_MAX:
        raise ValueError(f"page_size must be in [1, {GBIF_SEARCH_PAGE_MAX}]")
    if max_records is not None and (max_records < 1 or max_records > GBIF_SEARCH_HARD_MAX):
        raise ValueError(f"max_records must be in [1, {GBIF_SEARCH_HARD_MAX}] or None")

    base_params: dict[str, Any] = {
        "taxonKey": str(taxon_key),
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
    }
    if extra_params:
        base_params.update(dict(extra_params))

    fetch = get_json or _http_get_json
    query_for_fingerprint = {**base_params, "max_records": max_records, "page_size": page_size}
    query_sha = _fingerprint_json(query_for_fingerprint)

    rows: list[Mapping[str, Any]] = []
    offset = 0
    total_count: int | None = None
    while True:
        request_limit = page_size
        if max_records is not None:
            request_limit = min(request_limit, max_records - len(rows))
            if request_limit <= 0:
                break
        payload = dict(
            fetch(
                f"{GBIF_API}/v1/occurrence/search",
                {**base_params, "limit": int(request_limit), "offset": int(offset)},
            )
        )
        if total_count is None:
            total_count = int(payload.get("count", 0))
            if max_records is None and total_count > GBIF_SEARCH_HARD_MAX:
                raise GBIFBulkDownloadRequired(
                    f"GBIF query reports {total_count:,} records; use an asynchronous occurrence download "
                    f"rather than the search API hard limit of {GBIF_SEARCH_HARD_MAX:,}."
                )
        page = list(payload.get("results") or [])
        rows.extend(page)
        offset += len(page)
        if not page or bool(payload.get("endOfRecords", False)):
            break
        if max_records is not None and len(rows) >= max_records:
            break
        if offset >= GBIF_SEARCH_HARD_MAX:
            if total_count and offset < total_count:
                raise GBIFBulkDownloadRequired(
                    "GBIF search pagination reached 100,000 records before the query was exhausted; "
                    "use an asynchronous occurrence download."
                )
            break

    total_count = int(total_count or 0)
    frame = _normalize_search_records(rows)
    return GBIFSearchResult(
        records=frame,
        query=base_params,
        total_count=total_count,
        retrieved_count=len(frame),
        truncated=len(frame) < total_count,
        query_sha256=query_sha,
    )
