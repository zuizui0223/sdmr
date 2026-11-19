"""Hash-only original-source provenance guard for new forest process protocols.

This follow-up is distinct from frozen forest_source_gate_v1 decisions. It
does not parse source rows, open outcome values, estimate a model, or promote
previous field or synthetic results. A matching hash is necessary, not
sufficient, for a valid source sampling/observation audit.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5, sha256
from pathlib import Path
from urllib.parse import urlsplit

from sdmr.forest_source_gate_v1 import ForestSourceProfile, assess_forest_source


@dataclass(frozen=True)
class OriginalSourceByteAudit:
    source_id: str
    status: str
    reasons: tuple[str, ...]
    publisher_version: str | None
    raw_sha256_matched: bool
    publisher_md5_matched: bool | None
    inherited_metadata_gate_status: str
    source_content_parsed: bool = False
    ecological_responses_opened: bool = False
    independent_biological_test: bool = False
    source_only: bool = True
    response_opening_authorized: bool = False


def audit_original_source_bytes(
    source: ForestSourceProfile,
    *,
    publisher_version: str | None,
    original_file_url: str | None,
    original_file_path: str | Path | None,
    publisher_md5: str | None = None,
) -> OriginalSourceByteAudit:
    """Check an independently pinned raw file without inspecting its records.

    The original SHA-256 must be independently declared in the new source
    profile with receipt_role='original_source'. Reusing a derived-analysis
    artifact digest or already exposed response never authorizes admission.
    Publisher MD5 is optional; if given, it must match the *same bytes*.
    This procedure cannot verify that a publisher URL served those bytes:
    publisher/version identity still requires a separate authenticated or
    provider-supported source receipt.
    """
    reasons: list[str] = []
    if source.receipt_role != "original_source":
        reasons.append("derived_or_metadata_receipt_is_not_original_source")
    if source.response_state != "unopened" or source.design_state != "outcome_blind":
        reasons.append("previously_exposed_or_unfrozen_response_design")
    if not source.source_identity_verified:
        reasons.append("original_source_identity_not_verified")
    if not isinstance(publisher_version, str) or (
        not publisher_version.strip() or
        publisher_version.strip().lower() in {"latest", "unknown", "unversioned"}
    ):
        reasons.append("publisher_version_not_pinned")
    if not isinstance(original_file_url, str):
        reasons.append("publisher_original_file_url_missing")
    else:
        url = urlsplit(original_file_url)
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            reasons.append("publisher_original_file_url_invalid")
    if publisher_md5 is not None and (
        len(publisher_md5) != 32 or
        any(c not in "0123456789abcdef" for c in publisher_md5)
    ):
        reasons.append("publisher_md5_format_invalid")

    inherited = assess_forest_source(source).status
    verified_sha = False
    verified_md5: bool | None = None
    if original_file_path is None:
        reasons.append("original_file_bytes_not_available")
    # Never read the putative biological source if its pre-response provenance
    # and permission guards are already inconsistent.
    elif not reasons:
        path = Path(original_file_path)
        if not path.is_file():
            reasons.append("original_file_bytes_not_available")
        else:
            h_sha, h_md5 = sha256(), md5()
            try:
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h_sha.update(chunk)
                        h_md5.update(chunk)
            except OSError:
                reasons.append("original_file_read_failed")
            else:
                verified_sha = h_sha.hexdigest() == source.receipt_sha256
                if not verified_sha:
                    reasons.append("original_file_sha256_mismatch")
                if publisher_md5 is not None:
                    verified_md5 = h_md5.hexdigest() == publisher_md5
                    if not verified_md5:
                        reasons.append("original_file_publisher_md5_mismatch")

    if reasons:
        status = "raw_source_receipt_hold"
    elif inherited != "metadata_ready_for_separate_protocol_freeze":
        status = "raw_bytes_match_but_sampling_design_unresolved"
    else:
        status = "raw_bytes_match_for_separate_source_opportunity_audit"

    return OriginalSourceByteAudit(
        source_id=source.source_id,
        status=status,
        reasons=tuple(reasons),
        publisher_version=publisher_version if isinstance(publisher_version, str) else None,
        raw_sha256_matched=verified_sha,
        publisher_md5_matched=verified_md5,
        inherited_metadata_gate_status=inherited,
    )
