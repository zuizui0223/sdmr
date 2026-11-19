"""Synthetic-only tag/year identity audit; zero biological source download."""
import importlib.util
from io import StringIO
from pathlib import Path
import json
import sys

import pytest

SCRIPTS = Path("scripts").resolve()
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "hf453_tag_year_only_v2", SCRIPTS / "hf453_tag_year_identity_source_only_v2.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _sample(y1="A", y2="DS"):
    return "\n".join([
        "StemTag,year,status,CP,secret_health",
        "treeA,2021," + y1 + ",2,unused_1",
        "treeA,2022," + y2 + ",5,unused_2",
        "treeA,2023,AU,1,unused_3",
        "treeA,2024,DN,4,unused_4",
        "treeB,2021,DN,1,unused_5",
        "treeB,2023,A,3,unused_6",
        "treeC,2022,DC,2,unused_7",
        "treeC,2024,A,5,unused_8",
    ]) + "\n"


def test_identity_counts_and_missing_year_is_not_determined_death():
    d=mod.scan_identity_only(StringIO(_sample()))
    assert d["status"] == "tag_year_source_identity_indexed_only"
    assert d["n_original_rows"] == 8
    assert d["n_distinct_StemTag"] == 3
    assert d["n_distinct_tag_year"] == 8
    assert d["n_duplicate_tag_year"] == 0
    assert d["n_record_rows_by_year"] == {
        "2021":2,"2022":2,"2023":2,"2024":2,
    }
    assert d["n_tag_year_matched_by_adjacent_census"] == {
        "2021_to_2022":1,"2022_to_2023":1,"2023_to_2024":1,
    }
    assert d["n_tags_recorded_two_plus_years"] == 3
    assert d["n_tags_recorded_all_four_years"] == 1
    assert d["not_present_next_census_is_not_observed_death"] is True
    assert d["physical_tag_stability_author_verified"] is False
    assert d["alive_at_risk_denominator_estimated"] is False
    assert d["status_or_CP_columns_indexed"] is False
    assert d["biological_outcome_rows_interpreted"] is False


def test_status_and_canopy_mutations_cannot_change_source_identity_output():
    a=mod.scan_identity_only(StringIO(_sample("A","DS")))
    b=mod.scan_identity_only(StringIO(_sample("wounded","unknown")))
    assert a == b


def test_duplicate_tree_year_and_invalid_tag_are_hard_source_stops():
    duplicate=_sample()+"treeA,2021,A,3,unused\n"
    d=mod.scan_identity_only(StringIO(duplicate))
    assert d["status"] == "duplicate_original_tag_year_stop"
    assert d["n_duplicate_tag_year"] == 1
    invalid=_sample()+"treeD,2029,A,5,unused\n"
    e=mod.scan_identity_only(StringIO(invalid))
    assert e["status"] == "identity_source_fields_invalid_stop"
    assert e["n_invalid_StemTag_year"] == 1


def test_wrong_header_or_incomplete_four_year_frame_stops():
    with pytest.raises(ValueError, match="original_StemTag_year_fields_missing"):
        mod.scan_identity_only(StringIO("treeID,year,status\nA,2021,A\n"))
    c=mod.scan_identity_only(StringIO(
        "StemTag,year,status\nA,2021,A\nA,2022,A\nA,2023,A\n"
    ))
    assert c["status"] == "identity_year_frame_incomplete_stop"


def test_new_source_sha_barrier_prevents_any_csv_parse(monkeypatch):
    monkeypatch.setattr(mod, "_download_and_hash_original", lambda path: {
        "sha256":"f"*64,"md5":mod.PUBLISHER_MD5,
        "n_bytes":mod.EXPECTED_ORIGINAL_NBYTES
    })
    monkeypatch.setattr(
        mod,"scan_identity_only",
        lambda stream: (_ for _ in ()).throw(AssertionError("must not parse source")),
    )
    o=mod.audit_first_tag_year_source()
    assert o["status"] == "original_frozen_source_byte_mismatch_stop"
    assert o["source_identity_opened"] is False


def test_exact_verified_source_can_only_admit_identity_fields(monkeypatch):
    def fake_stream_hash(path):
        path.write_text(_sample())
        return {
            "sha256":mod.EXPECTED_ORIGINAL_SHA256,
            "md5":mod.PUBLISHER_MD5,
            "n_bytes":mod.EXPECTED_ORIGINAL_NBYTES,
        }
    monkeypatch.setattr(mod, "_download_and_hash_original", fake_stream_hash)
    o=mod.audit_first_tag_year_source()
    assert o["status"] == "tag_year_source_identity_indexed_only"
    assert o["source_identity_opened"] is True
    assert o["identity_only"]["status_or_CP_columns_indexed"] is False
    assert o["identity_only"]["alive_at_risk_denominator_estimated"] is False


def test_preflight_no_get_and_rejected_lock(tmp_path, monkeypatch):
    def forbidden():
        raise AssertionError("preflight must be network free")
    monkeypatch.setattr(mod,"audit_first_tag_year_source",forbidden)
    dest=tmp_path/"pre.json"
    monkeypatch.setattr(
        sys,"argv",["source_only","--preflight-only","--out",str(dest)]
    )
    mod.main()
    d=json.loads(dest.read_text())
    assert d["network_get_attempted"] is False
    assert d["status_CP_health_taxon_columns_not_used"] is True
    assert d["new_tree_response_opened"] is False
    assert d["new_biological_models_fit"] == 0
    assert d["new_biological_inference_authorized"] is False
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_CONTENT.replace("source=", "source=wrong"))
    monkeypatch.setattr(
        sys,"argv",["source_only","--execute-lock",str(bad),
                    "--out",str(tmp_path/"bad.json")]
    )
    with pytest.raises(ValueError,match="lock mismatch"):
        mod.main()


def test_latin1_non_utf8_source_note_is_not_an_identity_stop(tmp_path):
    # Invalid UTF-8 is deliberately confined to the ignored Notes column.
    # Only ASCII StemTag/year are indexed; no tree outcome is interpreted.
    source = tmp_path/"synthetic_source.csv"
    source.write_bytes(
        b"StemTag,year,status,CP,Notes\n"
        b"A,2021,A,1,\xff\n"
        b"A,2022,DS,3,\xfe\n"
        b"A,2023,A,4,ok\n"
        b"A,2024,A,5,ok\n"
    )
    with pytest.raises(UnicodeDecodeError):
        with source.open(encoding="utf-8-sig",newline="") as fh:
            mod.scan_identity_only(fh)
    with source.open(encoding="latin-1",newline="") as fh:
        r=mod.scan_identity_only(fh)
    assert r["status"]=="tag_year_source_identity_indexed_only"
    assert r["n_distinct_tag_year"]==4
    assert r["n_tags_recorded_all_four_years"]==1
    assert r["status_or_CP_columns_indexed"] is False


def test_reject_non_ascii_identity_even_if_latin1_would_decode():
    source = StringIO("StemTag,year\nT\u00e9st,2021\nT,2022\nT,2023\nT,2024\n")
    out=mod.scan_identity_only(source)
    assert out["status"] == "identity_source_fields_invalid_stop"
    assert out["n_invalid_StemTag_year"] == 1


def test_utf8_bom_read_through_latin1_is_removable_for_ascii_header():
    raw = (
        b"\xef\xbb\xbfStemTag,year\n"
        b"T,2021\nT,2022\nT,2023\nT,2024\n"
    )
    from io import TextIOWrapper, BytesIO
    with TextIOWrapper(BytesIO(raw), encoding="latin-1", newline="") as fh:
        out=mod.scan_identity_only(fh)
    assert out["status"]=="tag_year_source_identity_indexed_only"
    assert out["n_distinct_tag_year"]==4


def test_v2_first_v1_failure_is_explicitly_frozen_not_retroactively_changed():
    assert mod.PROGRAM.endswith("_v2")
    assert "first_identity_attempt_stop=UnicodeDecodeError_run_44476932274" in mod.LOCK_CONTENT
    assert "byte_decode=latin1_only_ASCII_identifiers" in mod.LOCK_CONTENT
