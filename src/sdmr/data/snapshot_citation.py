"""Validate a GBIF monthly snapshot DOI against that snapshot's own citation.txt."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .snapshot import GBIF_AWS_REGIONS

_DOI_RE = re.compile(r"10\.15468/dl\.[A-Za-z0-9]+", flags=re.IGNORECASE)


@dataclass(frozen=True)
class SnapshotCitation:
    snapshot_date: str
    region: str
    citation_url: str
    doi: str
    citation_sha256: str
    citation_text: str


def _validate_date(value: str) -> str:
    parsed = date.fromisoformat(str(value))
    if parsed.day != 1:
        raise ValueError("GBIF monthly snapshot date must be the first day of a month (YYYY-MM-01)")
    return parsed.isoformat()


def gbif_snapshot_citation_url(snapshot_date: str, *, region: str = "us-east-1") -> str:
    snapshot_date = _validate_date(snapshot_date)
    if region not in GBIF_AWS_REGIONS:
        raise ValueError(f"Unsupported GBIF AWS region: {region!r}")
    bucket = f"gbif-open-data-{region}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/occurrence/{snapshot_date}/citation.txt"


def extract_snapshot_doi(citation_text: str) -> str:
    match = _DOI_RE.search(str(citation_text))
    if not match:
        raise ValueError("GBIF snapshot citation.txt does not contain a 10.15468/dl.* DOI")
    return match.group(0).lower()


def _fetch_text(url: str, *, attempts: int = 5) -> str:
    headers = {"User-Agent": "sdmr-snapshot-citation/1.0", "Accept": "text/plain,*/*;q=0.1"}
    last: Exception | None = None
    for attempt in range(int(attempts)):
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            last = exc
            if exc.code == 404 or exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
        except URLError as exc:
            last = exc
            if attempt == attempts - 1:
                raise
        time.sleep(min(16, 2**attempt))
    assert last is not None
    raise last


def validate_snapshot_citation(
    snapshot_date: str,
    snapshot_doi: str,
    *,
    region: str = "us-east-1",
    fetch_text=None,
) -> SnapshotCitation:
    """Require the supplied DOI to occur in the exact snapshot's citation.txt.

    The citation file is stored beside the snapshot Parquet files by GBIF. This
    makes DOI validation independent of portal indexing and prevents a DOI for a
    different occurrence download from being attached to the snapshot evidence.
    """
    expected = str(snapshot_doi).strip().lower()
    if not expected:
        raise ValueError("snapshot_doi is required")
    url = gbif_snapshot_citation_url(snapshot_date, region=region)
    reader = fetch_text or _fetch_text
    text = reader(url)
    actual = extract_snapshot_doi(text)
    if actual != expected:
        raise ValueError(
            f"Snapshot DOI mismatch for {snapshot_date}: citation.txt has {actual}, supplied {expected}"
        )
    return SnapshotCitation(
        snapshot_date=_validate_date(snapshot_date),
        region=region,
        citation_url=url,
        doi=actual,
        citation_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        citation_text=text,
    )
