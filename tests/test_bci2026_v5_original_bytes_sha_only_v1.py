"""Pure-synthetic Dryad v5 full-file hash-only gate tests, source untouched."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from io import BytesIO

import pytest

p=Path("scripts/bci2026_v5_original_bytes_sha_only_v1.py")
sys.path.insert(0,str(p.parent.resolve()))
spec=importlib.util.spec_from_file_location("bci2026_original_bytes_only_v1",p)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def checkpoint():
    return json.loads(Path("evidence/bci2026_first_dryad_published_metadata_v1.json").read_text())


def mock_manifest(checkpoint):
    return {"count":5,"_embedded":{"stash:files":[{
        "path":fname,
        "size":v["bytes"],
        "digest":v["sha256"],
        "digestType":"sha-256",
        "_links":{
            "self":{"href":f"/api/v2/files/{500000+i}"},
            "stash:download":{"href":f"/api/v2/files/{500000+i}/download"},
            "stash:version":{"href":"/api/v2/versions/460507"}
        }
    } for i,(fname,v) in enumerate(sorted(checkpoint["files"].items()))]}}


def test_exact_publisher_sha256_and_source_v5_metadata_precommitted(checkpoint):
    q=mod.precommitted_metadata(checkpoint)
    assert len(q)==5
    assert q["mainfile.txt"]["bytes"]==4444083
    assert q["README.md"]["bytes"]==16958
    assert checkpoint["Dryad_version_number"]==5
    assert checkpoint["all_publisher_sha256_and_size_available"]
    assert not checkpoint["first_source_file_sha256_verified"]


def test_extract_file_id_only_from_versioned_publisher_links(checkpoint):
    output=mod.parse_exact_publisher_manifest(mock_manifest(checkpoint),
                                             checkpoint["files"])
    assert len(output)==5
    assert output["README.md"]["source_file_id"] in range(500000,500005)
    assert output["mainfile.txt"]["download_url"].startswith(
        "https://datadryad.org/api/v2/files/"
    )
    assert all(x["publisher_bytes"]>0 for x in output.values())
    assert all(len(x["publisher_sha256"])==64 for x in output.values())


def test_drift_missing_source_revision_and_file_links_stop(checkpoint):
    original=mock_manifest(checkpoint)
    mutations=[
        lambda x:x["_embedded"]["stash:files"][0].update(size=1),
        lambda x:x["_embedded"]["stash:files"][0].update(digest="0"*64),
        lambda x:x["_embedded"]["stash:files"][0]["_links"].update(
            **{"stash:version":{"href":"/api/v2/versions/OLD"}}),
        lambda x:x["_embedded"]["stash:files"][0]["_links"].update(
            **{"stash:download":{"href":"/api/v2/files/500000/other"}}),
    ]
    for mutate in mutations:
        z=deepcopy(original)
        mutate(z)
        with pytest.raises(ValueError):
            mod.parse_exact_publisher_manifest(z,checkpoint["files"])


def test_strict_source_link_security():
    url,ident=mod.require_file_download_link("/api/v2/files/38291/download")
    assert ident==38291
    assert url=="https://datadryad.org/api/v2/files/38291/download"
    for bad in (
        "https://example.com/api/v2/files/38291/download",
        "/api/v2/files/38291/download?version=latest",
        "/api/v2/datasets/download",
        "http://datadryad.org/api/v2/files/38291/download",
    ):
        with pytest.raises(ValueError):
            mod.require_file_download_link(bad)
    assert mod.strict_download_host("https://datadryad.org/api/v2/files/1/download")
    assert mod.strict_download_host("https://publisher-bucket.s3.us-west-2.amazonaws.com/data")
    with pytest.raises(ValueError):
        mod.strict_download_host("https://example.org/other-data")


def test_raw_byte_stream_digest_matching_without_any_biological_decoding():
    raw=b"synthetic example, NOT original field data\n"
    sha=hashlib.sha256(raw).hexdigest()

    class Stream:
        def __init__(self, body):
            self.body=BytesIO(body)
            self.headers={"Content-Length":str(len(body))}
        def read(self,n):
            return self.body.read(n)
        def geturl(self):
            return "https://datadryad.org/api/v2/files/1/download"
        def __enter__(self):return self
        def __exit__(self,*args):return False

    class Opener:
        def __init__(self,body):self.body=body
        def open(self,req,timeout):return Stream(self.body)

    url="https://datadryad.org/api/v2/files/1/download"
    p=mod.stream_original_file_sha256(url,len(raw),sha,opener=Opener(raw))
    assert p["status"]=="original_full_byte_sha256_matched"
    assert p["n_original_bytes"]==len(raw)
    assert not p["biological_rows_or_original_text_decoded"]
    assert not p["original_file_saved_to_artifact"]
    q=mod.stream_original_file_sha256(url,len(raw),sha,opener=Opener(b"x"*len(raw)))
    assert q["status"]=="original_provider_sha_or_size_drift_STOP"
    with pytest.raises(ValueError,match="larger_than"):
        mod.stream_original_file_sha256(url,len(raw)-1,sha,
                                         opener=Opener(raw))


def test_execute_once_checks_exact_five_files_no_raw_bytes(monkeypatch,checkpoint):
    manifest=mock_manifest(checkpoint)
    monkeypatch.setattr(mod,"_api_get_json",lambda _:manifest)
    calls=[]
    def fake(url,size,sha):
        calls.append((url,size,sha))
        return {
            "status":"original_full_byte_sha256_matched","n_original_bytes":size,
            "source_SHA256_checked":sha,"published_SHA256_expected":sha,
            "provider_size_expected":size,"provider_final_host":"datadryad.org",
            "biological_rows_or_original_text_decoded":False,
            "original_file_saved_to_artifact":False,
        }
    monkeypatch.setattr(mod,"stream_original_file_sha256",fake)
    x=mod.execute_once(checkpoint)
    assert x["status"]=="all_original_five_file_sha256_matched_no_biological_rows_opened"
    assert x["n_original_files_checked"]==5
    assert x["n_original_files_passed_SHA256"]==5
    assert len(calls)==5
    assert x["downloaded_original_files_archived"]==0
    assert x["decoded_biological_rows"]==0
    assert not x["new_independent_field_process_validation"]


def test_no_source_get_preflight_and_strict_second_lock(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"execute_once",lambda _: (_ for _ in ()).throw(
        AssertionError("preflight never fetches original file")))
    pre=tmp_path/"pre.json"
    monkeypatch.setattr(sys,"argv",["hash","--preflight-only","--out",str(pre)])
    mod.main()
    q=json.loads(pre.read_text())
    assert q["result"]["status"]=="preflight_metadata_sha_pinned_original_tree_rows_unopened"
    assert q["source_original_mainfile_stemfile_or_README_parsed"] is False
    assert q["biological_outcome_or_2025_exposure_opened"] is False
    assert q["original_CSV_or_text_bytes_archived"] is False
    wrong=tmp_path/"wrong.lock"
    wrong.write_text(mod.LOCK.replace("460507","version_latest"))
    monkeypatch.setattr(sys,"argv",["hash","--execute-lock",str(wrong),
                                    "--out",str(tmp_path/"no.json")])
    with pytest.raises(ValueError,match="second_stage_lock_changed"):
        mod.main()
