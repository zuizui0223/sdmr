import pytest

from sdmr.data.snapshot_citation import (
    extract_snapshot_doi,
    gbif_snapshot_citation_url,
    validate_snapshot_citation,
)


def test_snapshot_citation_url_is_versioned_and_regional():
    assert gbif_snapshot_citation_url("2026-08-01", region="us-east-1") == (
        "https://gbif-open-data-us-east-1.s3.us-east-1.amazonaws.com/occurrence/2026-08-01/citation.txt"
    )
    with pytest.raises(ValueError, match="first day"):
        gbif_snapshot_citation_url("2026-08-14")


def test_extract_snapshot_doi_from_citation_text():
    text = "Please cite GBIF occurrence data using https://doi.org/10.15468/dl.Ab12Cd."
    assert extract_snapshot_doi(text) == "10.15468/dl.ab12cd"


def test_validate_snapshot_citation_requires_exact_doi_match():
    def reader(url):
        assert url.endswith("/occurrence/2026-08-01/citation.txt")
        return "Citation DOI: 10.15468/dl.abc123\n"

    citation = validate_snapshot_citation(
        "2026-08-01",
        "10.15468/DL.ABC123",
        fetch_text=reader,
    )
    assert citation.doi == "10.15468/dl.abc123"
    assert len(citation.citation_sha256) == 64

    with pytest.raises(ValueError, match="DOI mismatch"):
        validate_snapshot_citation(
            "2026-08-01",
            "10.15468/dl.wrong",
            fetch_text=reader,
        )


def test_extract_snapshot_doi_rejects_citation_without_download_doi():
    with pytest.raises(ValueError, match="does not contain"):
        extract_snapshot_doi("No DOI here")
