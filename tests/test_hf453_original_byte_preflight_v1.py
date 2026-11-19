"""Synthetic-only HF453 byte preflight tests. No provider request made."""
from hashlib import md5, sha256
import importlib.util
import json
from pathlib import Path
import sys

import pytest


SOURCE = Path("scripts/hf453_original_byte_preflight_v1.py")
spec = importlib.util.spec_from_file_location("sdmr_hf453_hash_script", SOURCE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_byte_digest_is_exact_bounded_and_no_payload_retained():
    d = mod.byte_digests([b"abc", b"def"])
    assert d == {
        "sha256": sha256(b"abcdef").hexdigest(),
        "md5": md5(b"abcdef").hexdigest(), "bytes": 6,
    }
    with pytest.raises(ValueError, match="byte_cap"):
        mod.byte_digests([b"123", b"456"], max_bytes=5)
    with pytest.raises(ValueError, match="empty"):
        mod.byte_digests([])
    with pytest.raises(TypeError, match="binary"):
        mod.byte_digests(["a,b,Y\n"])


def test_exact_provider_redirect_scope_and_no_unpinned_query():
    assert mod.require_provider_https(mod.SOURCE_URL) == "harvardforest.fas.harvard.edu"
    assert mod.require_provider_https(
        mod.SOURCE_URL.replace("harvardforest.fas.harvard.edu",
                               "harvardforest1.fas.harvard.edu")
    ) == "harvardforest1.fas.harvard.edu"
    for url in (
        mod.SOURCE_URL.replace("https:", "http:"),
        mod.SOURCE_URL + "?download=latest",
        mod.SOURCE_URL.replace("harvardforest.fas.harvard.edu", "example.org"),
        mod.SOURCE_URL.replace(mod.FILENAME, "other-tree-data.csv"),
        mod.SOURCE_URL + "#unstable",
    ):
        with pytest.raises(mod.UnsafeSourceUrl):
            mod.require_provider_https(url)


def test_no_network_preflight_and_strict_source_lock(tmp_path, monkeypatch):
    def no_get():
        raise AssertionError("preflight must not access external source")
    monkeypatch.setattr(mod, "check_publisher_bytes", no_get)
    report = tmp_path / "preflight.json"
    monkeypatch.setattr(
        sys, "argv",
        ["preflight", "--preflight-only", "--out", str(report)],
    )
    mod.main()
    d = json.loads(report.read_text())
    assert d["preflight_only"]
    assert d["original_network_get_attempted"] is False
    assert d["biological_responses_inspected"] is False
    assert d["new_biological_endpoint_test_authorized"] is False
    assert d["result"]["status"] == "preflight_unopened"
    bad_lock = tmp_path / "bad.lock"
    bad_lock.write_text(mod.LOCK_CONTENT.replace("source=", "source=changed"))
    monkeypatch.setattr(
        sys, "argv", ["preflight", "--execute-lock", str(bad_lock),
                        "--out", str(tmp_path / "bad.json")],
    )
    with pytest.raises(ValueError, match="lock mismatch"):
        mod.main()


def test_synthetic_get_exact_published_md5_gate_with_no_parsing(monkeypatch):
    body = b"fixture text only, never real organism observations\n"
    expected = md5(body).hexdigest()
    monkeypatch.setattr(mod, "PUBLISHER_MD5", expected)

    class FakeResponse:
        headers = {"Content-Length": str(len(body))}
        def __init__(self):
            self.done = False
        def geturl(self):
            return mod.SOURCE_URL
        def read(self, n):
            if self.done:
                return b""
            self.done = True
            return body
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    class FakeOpener:
        calls = 0
        def open(self, req, timeout):
            self.calls += 1
            assert req.full_url == mod.SOURCE_URL
            return FakeResponse()

    opener = FakeOpener()
    monkeypatch.setattr(mod, "build_opener", lambda *args: opener)
    out = mod.check_publisher_bytes()
    assert opener.calls == 1
    assert out["status"] == "original_byte_md5_matched_source_only"
    assert out["publisher_md5_matched"] is True
    assert out["sha256"] == sha256(body).hexdigest()
    assert "body" not in out
    assert "rows" not in out


def test_provider_checksum_drift_and_http_failure_are_source_stops(monkeypatch):
    class FakeResponse:
        headers = {"Content-Length": "3"}
        def geturl(self):
            return mod.SOURCE_URL
        def read(self, n):
            if not hasattr(self, "done"):
                self.done = True
                return b"foo"
            return b""
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    class FakeOpener:
        def open(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(mod, "build_opener", lambda *args: FakeOpener())
    out = mod.check_publisher_bytes()
    assert out["status"] == "publisher_md5_drift_stop"
    assert out["publisher_md5_matched"] is False
    from urllib.error import HTTPError

    class FailOpener:
        def open(self, *args, **kwargs):
            raise HTTPError(mod.SOURCE_URL, 403, "Forbidden", None, None)

    monkeypatch.setattr(mod, "build_opener", lambda *args: FailOpener())
    stop = mod.check_publisher_bytes()
    assert stop["status"] == "original_source_unavailable_stop"
    assert stop["stop_reason"] == "http_status_403"
    assert stop["bytes_complete"] is False


def test_source_receipt_never_admits_ecology():
    x = mod.source_receipt(
        preflight_only=False, source={
            "status": "original_byte_md5_matched_source_only",
            "md5": mod.PUBLISHER_MD5,
            "publisher_md5_matched": True,
            "bytes_complete": True,
        },
    )
    assert not x["raw_bytes_retained"]
    assert not x["source_rows_decoded"]
    assert not x["biological_responses_inspected"]
    assert x["n_new_biological_models"] == 0
    assert not x["new_biological_endpoint_test_authorized"]
    assert x["Product_B_unblocked"] is False
