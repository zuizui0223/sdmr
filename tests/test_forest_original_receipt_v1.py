"""New-source raw-byte admission tests; synthetic file contents ONLY."""
from dataclasses import replace
from hashlib import md5, sha256

from sdmr.forest_source_gate_v1 import ForestSourceProfile
from sdmr.forest_original_receipt_v1 import audit_original_source_bytes


CONTENT = b"fixture: published forest sampling protocol metadata, not organism responses\n"


def _source():
    return ForestSourceProfile(
        source_id="new_fixture_source", study_reference="https://example.org/study",
        evidence_family_id="new_independent_fixture",
        publisher_source="https://example.org/provider", receipt_role="original_source",
        receipt_sha256=sha256(CONTENT).hexdigest(),
        endpoint="tree_health_transition", operator="annual_field_observation",
        observation_mode="unconditional",
        sampling_frame="complete_including_zeros", effort_status="verified",
        attrition_status="accounted", taxon_status="verified_for_declared_response",
        block_status="verified_independent", process_carriers="complete",
        response_state="unopened", design_state="outcome_blind",
        n_source_units=24, n_eligible_units=24, n_blocks_reported=6,
        min_block_units=4, source_identity_verified=True,
        temporal_alignment_verified=True, notes="source-only synthetic fixture",
    )


def _audit(source, file, *, digest=None, version="v1"):
    return audit_original_source_bytes(
        source, publisher_version=version,
        original_file_url="https://example.org/immutable/source-v1.txt",
        original_file_path=file, publisher_md5=digest,
    )


def test_positive_original_bytes_only_authorize_next_source_audit(tmp_path):
    original = tmp_path / "raw.txt"
    original.write_bytes(CONTENT)
    receipt = _audit(_source(), original, digest=md5(CONTENT).hexdigest())
    assert receipt.status == "raw_bytes_match_for_separate_source_opportunity_audit"
    assert receipt.reasons == ()
    assert receipt.raw_sha256_matched is True
    assert receipt.publisher_md5_matched is True
    assert receipt.inherited_metadata_gate_status == "metadata_ready_for_separate_protocol_freeze"
    assert not receipt.source_content_parsed
    assert not receipt.ecological_responses_opened
    assert not receipt.independent_biological_test
    assert not receipt.response_opening_authorized


def test_legacy_analysis_artifact_cannot_substitute_for_original(tmp_path):
    file = tmp_path / "artifact.zip"
    file.write_bytes(CONTENT)
    receipt = _audit(replace(_source(), receipt_role="analysis_artifact"), file)
    assert receipt.status == "raw_source_receipt_hold"
    assert "derived_or_metadata_receipt_is_not_original_source" in receipt.reasons
    assert receipt.raw_sha256_matched is False


def test_original_digest_and_publisher_checksum_must_match_same_bytes(tmp_path):
    file = tmp_path / "raw.txt"
    file.write_bytes(CONTENT + b"changed")
    fail_sha = _audit(_source(), file)
    assert "original_file_sha256_mismatch" in fail_sha.reasons
    assert not fail_sha.response_opening_authorized
    file.write_bytes(CONTENT)
    fail_md5 = _audit(_source(), file, digest="a" * 32)
    assert fail_md5.raw_sha256_matched
    assert fail_md5.publisher_md5_matched is False
    assert "original_file_publisher_md5_mismatch" in fail_md5.reasons


def test_absence_and_mutable_provider_version_remain_explicit_unknown():
    receipt = _audit(_source(), None, version="latest")
    assert "original_file_bytes_not_available" in receipt.reasons
    assert "publisher_version_not_pinned" in receipt.reasons
    assert not receipt.raw_sha256_matched


def test_previous_response_or_missing_independent_identity_is_not_new_test(tmp_path):
    path = tmp_path / "raw.txt"
    path.write_bytes(CONTENT)
    for edited in (
        replace(_source(), response_state="previously_opened",
                design_state="historical_outcome_exposed"),
        replace(_source(), source_identity_verified=False),
    ):
        receipt = _audit(edited, path)
        assert receipt.status == "raw_source_receipt_hold"
        assert not receipt.raw_sha256_matched
        assert not receipt.independent_biological_test


def test_matching_raw_bytes_do_not_bypass_sampling_selection_gate(tmp_path):
    file = tmp_path / "raw.txt"
    file.write_bytes(CONTENT)
    partial = replace(
        _source(), observation_mode="capture_conditional",
        sampling_frame="detected_only", effort_status="unknown",
        process_carriers="partial",
    )
    receipt = _audit(partial, file)
    assert receipt.raw_sha256_matched is True
    assert receipt.status == "raw_bytes_match_but_sampling_design_unresolved"
    assert receipt.inherited_metadata_gate_status == "observation_unresolved"
    assert not receipt.response_opening_authorized
