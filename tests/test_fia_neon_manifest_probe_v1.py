"""NEON 2026 pilot: no signed URLs/tokens, no plant data, fail-closed gates."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_neon_manifest_probe_v1 as m


def sample_manifest(site: str):
    prefix=f"NEON.D01.{site}.{m.PRODUCT}"
    def entry(t):
        return {"name":f"{prefix}.{t}.2014-08.basic.20261001T000000Z.csv",
                "size":1234, "url":"https://unsafe-other-host.example/?apiToken=PRIVATE_SENTINEL"}
    return {"data":{"files":[entry(t) for t in m.REQUIRED_TABLES]+
                  [{"name":f"{prefix}.readme.txt", "size":80,
                    "url":"https://unsafe.example/SECRET_SENTINEL"}]}}


def test_frozen_pilot_months_are_predeclared_and_source_only():
    assert m.PILOT==( ("HARV","2014-08"),("HARV","2024-08"),
                     ("SCBI","2014-08"),("SCBI","2024-09") )
    assert m.RELEASE=="RELEASE-2026"
    assert m.PRODUCT=="DP1.10098.001"
    assert len(m.ORIGINAL_PUBLIC_CATALOG_SHA)==len(m.ORIGINAL_PUBLIC_RECEIPT_SHA)==64


def test_valid_manifest_reports_three_tables_and_no_URLs_or_individuals():
    x=m.summarize_manifest(sample_manifest("HARV"),"HARV","2014-08")
    assert x["required_tables_each_present_once"]
    assert x["n_files"]==4
    assert x["required_table_counts"]=={t:1 for t in m.REQUIRED_TABLES}
    assert x["any_signed_file_urls_archived"] is False
    text=json.dumps(x)
    assert "PRIVATE_SENTINEL" not in text
    assert "SECRET_SENTINEL" not in text
    assert "http" not in text
    assert x["individualID_or_growth_data_read"] is False


def test_missing_table_or_duplicate_table_never_passes():
    manifest=sample_manifest("SCBI")
    manifest["data"]["files"]=[f for f in manifest["data"]["files"] if "vst_mappingandtagging" not in f["name"]]
    one=m.summarize_manifest(manifest,"SCBI","2024-09")
    assert not one["required_tables_each_present_once"]
    assert one["required_table_counts"]["vst_mappingandtagging"]==0
    manifest["data"]["files"].append({"name":"NEON.D01.SCBI.DP1.10098.001.vst_apparentindividual.2024-09.basic.X.csv",
                                       "size":1})
    two=m.summarize_manifest(manifest,"SCBI","2024-09")
    assert not two["required_tables_each_present_once"]
    assert two["required_table_counts"]["vst_apparentindividual"]==2


@pytest.mark.parametrize("name",[
    "NEON.D01.XXXX.DP1.10098.001.vst_apparentindividual.2014-08.basic.csv",
    "NEON.D01.HARV.DP1.99999.001.vst_apparentindividual.2014-08.basic.csv",
    "not_a_NEON_name.csv",
])
def test_invalid_site_product_or_vendor_file_is_rejected(name):
    payload=sample_manifest("HARV")
    payload["data"]["files"][0]["name"]=name
    with pytest.raises(ValueError,match="inconsistency"):
        m.summarize_manifest(payload,"HARV","2014-08")


def test_absent_token_does_not_call_authenticated_endpoint(tmp_path,monkeypatch):
    monkeypatch.setattr(m,"audit_frozen_catalog",lambda *args:None)
    calls=[]
    def fetcher(url,token):
        calls.append((url,token));return sample_manifest("HARV")
    x=m.run(tmp_path/"cat",tmp_path/"receipt",tmp_path,token=None,fetcher=fetcher)
    assert x["status"]=="no_NEON_API_TOKEN_secret_configured_no_network_data_request"
    assert x["n_manifest_requests"]==0
    assert x["n_manifest_table_sets_confirmed"] is None
    assert calls==[]
    assert x["individual_repeat_status_verified"] is None
    assert not x["biological_promotion_authorized"]


def test_configured_token_probes_only_four_fixed_manifest_urls(tmp_path,monkeypatch):
    monkeypatch.setattr(m,"audit_frozen_catalog",lambda *args:None)
    calls=[]
    def fetch(url,token):
        calls.append(url)
        assert token=="SYNTHETIC_PRIVATE_TOKEN"
        assert "/api/v0/data/DP1.10098.001/" in url and "release=RELEASE-2026" in url
        assert "SYNTHETIC_PRIVATE_TOKEN" not in url
        site=url.split("/")[7]
        return sample_manifest(site)
    x=m.run(tmp_path/"cat",tmp_path/"receipt",tmp_path,
            token="SYNTHETIC_PRIVATE_TOKEN",fetcher=fetch)
    assert x["status"]=="all_pilot_file_manifests_available_no_raw_data"
    assert x["n_manifest_requests"]==4
    assert x["n_manifest_table_sets_confirmed"]==4
    saved=(tmp_path/"neon_2026_file_manifest_source_gate.json").read_text()
    assert "SYNTHETIC_PRIVATE_TOKEN" not in saved
    assert "PRIVATE_SENTINEL" not in saved
    assert "SECRET_SENTINEL" not in saved
    assert all(row["individualID_or_growth_data_read"] is False for row in x["site_month_manifests"])
    assert not x["raw_vegetation_tables_downloaded"]


def test_authentication_error_does_not_fake_source_confirmations(tmp_path,monkeypatch):
    monkeypatch.setattr(m,"audit_frozen_catalog",lambda *args:None)
    def forbidden(url,token):
        raise HTTPError(url,401,"Authorization required",None,None)
    x=m.run(tmp_path/"cat",tmp_path/"receipt",tmp_path,token="SECRET",fetcher=forbidden)
    assert x["status"]=="pilot_file_manifest_incomplete_stop_before_any_raw_data"
    assert x["n_manifest_table_sets_confirmed"]==0
    assert all(e["http_status"]==401 for e in x["site_month_manifests"])
    assert "SECRET" not in json.dumps(x)
    assert x["n_planned_site_months"]==4


def test_altered_catalog_refused_before_requests(tmp_path):
    c=tmp_path/"catalog.json";s=tmp_path/"receipt.json"
    c.write_text("{}");s.write_text("{}")
    x=m.run(c,s,tmp_path,token="SECRET",fetcher=lambda *_: (_ for _ in ()).throw(
        AssertionError("must never contact new source")))
    assert x["status"]=="frozen_public_source_catalog_unavailable_stop"
    assert x["n_manifest_requests"]==0


def test_unregistered_site_month_or_missing_token_refuses_call():
    with pytest.raises(ValueError,match="unregistered"):
        m.manifest_request("OTHER","2024-09","SYNTHETIC_TOKEN",fetcher=lambda *_:None)
    with pytest.raises(ValueError,match="token"):
        m.manifest_request("HARV","2024-08","",fetcher=lambda *_:None)
