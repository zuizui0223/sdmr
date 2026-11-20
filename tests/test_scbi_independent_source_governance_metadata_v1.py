"""SCBI source-governance metadata v1 synthetic-only gates. Never open CSV."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

script=Path("scripts/scbi_independent_source_governance_metadata_v1.py")
spec=importlib.util.spec_from_file_location("scbi_source_governance_v1",script)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def config():
    return json.loads(Path("configs/scbi_independent_forest_governance_prefreeze_v1.json").read_text())


def fake_git_tree(commit:str,files:list[dict])->dict:
    return {"sha":commit,"truncated":False,"tree":[
        {"path":x["path"],"sha":x["git_blob_sha1"],
         "size":x["bytes"],"mode":"100644","type":"blob"}
        for x in files]}


def test_all_source_rights_and_no_approved_master_are_explicit(config):
    mod.validate_config(config)
    assert not config["original_approved_ForestGEO_master_data_available"]
    assert config["approval_or_scbi_version_from_PIs"] is None
    assert not config["analysis_using_original_SCBI_tree_data_authorized"]
    assert config["source_use_rules"]["require_data_request_and_approved_master_version_before_analysis"]
    assert config["source_use_rules"]["require_PI_collaborator_and_authorship_terms_per_official_site"]
    assert config["source_use_rules"]["separate_custom_mortality_use_agreement_for_years_2022_and_later"]
    assert config["scientific_admission"]["future_biological_analyses_blocked"]
    assert config["scientific_admission"]["2018_crown_sample_is_selected_dendroband_core_subset"]
    assert config["Git_blob_SHA1_is_NOT_raw_file_SHA256"]


@pytest.mark.parametrize("edit,reason",[
    (lambda c:c.update(analysis_using_original_SCBI_tree_data_authorized=True),
     "false_authorization_or_digest"),
    (lambda c:c.update(approval_or_scbi_version_from_PIs="fabricated"),
     "false_authorization_or_digest"),
    (lambda c:c["source_use_rules"].update(require_data_request_and_approved_master_version_before_analysis=False),
     "original_SCBI_PI_use_terms_weakened"),
    (lambda c:c["provider_sources"]["public_2023_release"].update(published_release_tag="main"),
     "exact_public_snapshot_lineage"),
    (lambda c:c["scientific_admission"].update(future_biological_analyses_blocked=False),
     "SCBI_response_access"),
    (lambda c:c.update(Git_blob_SHA1_is_NOT_raw_file_SHA256=False),
     "false_authorization_or_digest"),
])
def test_mutation_never_promotes_source_metadata_to_field_use(config,edit,reason):
    c=deepcopy(config);edit(c)
    with pytest.raises(ValueError,match=reason):
        mod.validate_config(c)


def test_exact_git_tree_sha1_bytes_and_no_file_contents(config):
    old=config["provider_sources"]["earlier_public_copies"]
    d=mod.exact_public_git_tree(
        fake_git_tree(mod.OLD_SHA,old["files"]),mod.OLD_SHA,old["files"])
    assert len(d["selected_files"])==3
    assert not d["selected_original_CSV_bytes_opened"]
    assert all(not x["is_raw_complete_file_SHA256"] for x in d["selected_files"])
    assert all(not x["is_approved_original_ForestGEO_master"] for x in d["selected_files"])
    assert sorted(x["public_Git_object_size_bytes"] for x in d["selected_files"])==[
        5927551,6219513,6598542]


def test_sha_size_truncation_or_drift_never_silently_admitted(config):
    old=config["provider_sources"]["earlier_public_copies"]
    record=fake_git_tree(mod.OLD_SHA,old["files"])
    for modfn in [
        lambda z:z.update(sha="0"*40),
        lambda z:z.update(truncated=True),
        lambda z:z["tree"][0].update(sha="0"*40),
        lambda z:z["tree"][0].update(size=1),
        lambda z:z["tree"].pop(),
    ]:
        x=deepcopy(record);modfn(x)
        with pytest.raises(ValueError):
            mod.exact_public_git_tree(x,mod.OLD_SHA,old["files"])


def test_tagged_2024_05_version_not_mutable_2026_main(config):
    p=config["provider_sources"]["public_2023_release"]
    original=[{"path":p["source_path"],"bytes":p["bytes"],"git_blob_sha1":p["git_blob_sha1"]}]
    r=mod.exact_public_git_tree(fake_git_tree(mod.TAG_COMMIT,original),mod.TAG_COMMIT,original)
    assert r["frozen_commit"]=="6ac8718dcab0c5c653c56d55a1e093a6c20150e2"
    assert r["selected_files"][0]["public_Git_object_size_bytes"]==35463140
    assert r["selected_files"][0]["public_Git_blob_SHA1"]=="cbaa4d92fb4588788895cc95f3542c9de1f80f32"


def test_only_static_git_trees_and_no_branch_latest_url():
    good="https://api.github.com/repos/SCBI-ForestGEO/2023census/git/trees/"+mod.TAG_COMMIT+"?recursive=1"
    mod.require_api_path(good)
    for bad in [
        "https://raw.githubusercontent.com/SCBI-ForestGEO/2023census/main/processed_data/scbi.stem4.csv",
        "https://api.github.com/repos/SCBI-ForestGEO/2023census/contents/processed_data/scbi.stem4.csv",
        "http://api.github.com/repos/SCBI-ForestGEO/2023census/git/trees/abc",
        "https://api.github.com/repos/private/other/git/trees/main?recursive=1",
    ]:
        with pytest.raises(ValueError):
            mod.require_api_path(bad)


def test_full_source_api_fixture_still_returns_rights_hold(config,monkeypatch):
    prev=config["provider_sources"]["earlier_public_copies"]
    nxt=config["provider_sources"]["public_2023_release"]
    new=[{"path":nxt["source_path"],"bytes":nxt["bytes"],"git_blob_sha1":nxt["git_blob_sha1"]}]
    def fake(url):
        if mod.OLD_SHA in url:
            return fake_git_tree(mod.OLD_SHA,prev["files"])
        if mod.TAG_COMMIT in url:
            return fake_git_tree(mod.TAG_COMMIT,new)
        raise AssertionError("unexpected source")
    monkeypatch.setattr(mod,"metadata_get",fake)
    r=mod.source_receipt(config,preflight=False)
    assert r["result"]["status"]=="public_snapshots_Git_tree_metadata_verified_but_master_approval_pending"
    assert not r["original_tree_data_approved_for_scientific_use"]
    assert not r["raw_original_CSV_downloaded"]
    assert not r["full_original_biological_response_opened"]
    assert r["result"]["source_full_byte_sha256_verified"] is False
    assert r["result"]["same_physical_forest_for_all_four_censuses"] is True
    assert r["new_ecological_models_fit"]==0
    assert r["independent_field_process_test_performed"] is False


def test_preflight_never_contacts_source_and_inexact_lock_fails(config,tmp_path,monkeypatch):
    monkeypatch.setattr(mod,"metadata_get",lambda url:
        (_ for _ in ()).throw(AssertionError("no API GET allowed in preflight")))
    pre=tmp_path/"preflight.json"
    monkeypatch.setattr(sys,"argv",["check","--preflight-only","--out",str(pre)])
    mod.main()
    x=json.loads(pre.read_text())
    assert x["result"]["status"]=="source_free_preflight_governance_contract_only"
    assert x["metadata_only"]
    assert not x["raw_original_CSV_downloaded"]
    assert not x["original_authorized_master_version_verified"]
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK.replace("approved_master_version_not_available=true",
                                     "approved_master_version_not_available=false"))
    monkeypatch.setattr(sys,"argv",["check","--execute-lock",str(bad),
                                    "--out",str(tmp_path/"bad.json")])
    with pytest.raises(ValueError,match="authorization_lock_mismatch"):
        mod.main()
