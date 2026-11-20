"""Provider-free BCI 2026 source-version audit tests: no organism file read."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import json
import sys

import pytest

script = Path("scripts/bci2026_source_provider_metadata_v1.py")
spec = importlib.util.spec_from_file_location("bci_dryad_source_meta",script)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def config():
    return json.loads(Path("configs/bci2026_independent_source_metadata_prefreeze_v1.json").read_text())


def versions_payload():
    return {
        "_embedded":{"stash:versions":[
            {"versionNumber":1,"publicationDate":"2026-03-17",
             "_links":{"stash:files":{"href":"/api/v2/versions/271100/files"}}},
            {"versionNumber":2,"publicationDate":"2026-08-31",
             "_links":{"self":{"href":"/api/v2/versions/271101"},
                       "stash:files":{"href":"/api/v2/versions/271101/files"}}},
        ]},
        "count":2,
    }


def files_payload(*,omit_digest=False):
    return {"_embedded":{"stash:files":[
        {"path":name,"id":i+100,"size":1000+i,
         "digest":None if omit_digest else "e"*32,"digestType":"md5"}
        for i,name in enumerate(sorted(mod.EXPECTED_FILES))
    ]},"count":5}


def test_source_contract_enforces_2025_exposure_and_2026_release(config):
    mod.validate_config(config)
    invalid = deepcopy(config)
    invalid["exact_edition_publication_date"] = "2026-03-17"
    with pytest.raises(ValueError,match="source_edition_changed"):
        mod.validate_config(invalid)
    invalid = deepcopy(config)
    invalid["semantically_protected_fields"]["exposure"]="usable 2014 predeath"
    with pytest.raises(ValueError,match="post_outcome_exposure_leakage_gate"):
        mod.validate_config(invalid)
    invalid=deepcopy(config)
    invalid["product_B_blocked"]=False
    with pytest.raises(ValueError,match="original_BCI_response_admission"):
        mod.validate_config(invalid)


def test_dryad_edition_selected_by_exact_release_date_not_last_position():
    z=mod.exact_version_descriptor(versions_payload())
    assert z["publication_date"]=="2026-08-31"
    assert z["version_number"]==2
    assert z["number_of_provider_versions"]==2
    assert z["file_manifest_api_url"]=="https://datadryad.org/api/v2/versions/271101/files"
    swapped=deepcopy(versions_payload())
    swapped["_embedded"]["stash:versions"].reverse()
    assert mod.exact_version_descriptor(swapped)==z


def test_unverified_edition_and_duplicate_date_refused():
    z=versions_payload()
    z["_embedded"]["stash:versions"][1]["publicationDate"]="2026-03-18"
    with pytest.raises(ValueError,match="not_unique"):
        mod.exact_version_descriptor(z)
    z=versions_payload()
    z["_embedded"]["stash:versions"].append(deepcopy(z["_embedded"]["stash:versions"][1]))
    z["count"]=3
    with pytest.raises(ValueError,match="not_unique"):
        mod.exact_version_descriptor(z)
    z=versions_payload()
    z["count"]=9
    with pytest.raises(ValueError,match="incomplete"):
        mod.exact_version_descriptor(z)


def test_exact_five_files_digest_and_limited_metadata_only():
    x=mod.manifest_summary(files_payload())
    assert x["status"]=="provider_original_file_manifest_with_published_checksums"
    assert x["n_original_source_files"]==5
    assert [z["name"] for z in x["files"]]==sorted(mod.EXPECTED_FILES)
    assert x["all_provider_digests_and_sizes_present"]
    assert not x["raw_source_file_contents_opened"]
    assert all(z["provider_file_bytes"]>0 for z in x["files"])
    y=mod.manifest_summary(files_payload(omit_digest=True))
    assert y["status"]=="provider_original_file_manifest_missing_checksums_hold"
    assert not y["all_provider_digests_and_sizes_present"]


def test_unknown_file_duplicate_file_and_invalid_size_fail_closed():
    x=files_payload()
    x["_embedded"]["stash:files"][0]["path"]="unexpected_tree_outcome.txt"
    with pytest.raises(ValueError,match="unexpected_or_duplicate"):
        mod.manifest_summary(x)
    x=files_payload()
    x["_embedded"]["stash:files"][0]["path"]="stemfile.txt"
    with pytest.raises(ValueError,match="unexpected_or_duplicate"):
        mod.manifest_summary(x)
    x=files_payload()
    x["_embedded"]["stash:files"][0]["size"]=-1
    with pytest.raises(ValueError,match="size_invalid"):
        mod.manifest_summary(x)


def test_versioned_provider_link_must_not_redirect_to_current_or_other_host():
    for url in (
        "https://example.com/api/v2/versions/271101/files",
        "http://datadryad.org/api/v2/versions/271101/files",
        "https://datadryad.org/dataset/doi:10.5061/dryad.1g1jwsvc3",
    ):
        with pytest.raises(ValueError):
            mod.require_api_url(url)
    p=versions_payload()
    p["_embedded"]["stash:versions"][1]["_links"]["stash:files"]["href"]="/api/v2/datasets/latest/files"
    with pytest.raises(ValueError,match="not_pinned_to_specific_version"):
        mod.exact_version_descriptor(p)


def test_response_source_file_not_opened_in_preflight(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"metadata_gate_run",lambda:
        (_ for _ in ()).throw(AssertionError("must not open even provider metadata")))
    x=tmp_path/"pref.json"
    monkeypatch.setattr(sys,"argv",["script","--preflight-only","--out",str(x)])
    mod.main()
    q=json.loads(x.read_text())
    assert q["preflight"]
    assert q["result"]["status"]=="preflight_source_unopened"
    assert q["source_original_files_downloaded"]==0
    assert q["source_biological_rows_opened"] is False
    assert q["new_ecological_models_fit"]==0
    assert q["independent_forest_biological_validation_performed"] is False
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_TEXT.replace("2026-08-31","2026-03-17"))
    monkeypatch.setattr(sys,"argv",["script","--execute-lock",str(bad),
                                    "--out",str(tmp_path/"not.json")])
    with pytest.raises(ValueError,match="first_attempt_lock_changed"):
        mod.main()


def test_real_api_network_not_called_in_fixture_but_schema_decoded(monkeypatch):
    config=json.loads(Path("configs/bci2026_independent_source_metadata_prefreeze_v1.json").read_text())
    def fake(url):
        if url.endswith("/versions"):
            return versions_payload()
        if "/versions/271101/files" in url:
            return files_payload()
        return {"identifier":"doi:"+mod.DOI,
                "license":"https://spdx.org/licenses/CC0-1.0.html",
                "versionNumber":2}
    monkeypatch.setattr(mod,"_api_get_json",fake)
    z=mod.run_once(config)
    assert z["status"]=="provider_original_file_manifest_with_published_checksums"
    assert z["selected_original_version"]["version_number"]==2
    assert not z["source_original_byte_SHA256_checked"]
    assert not z["biological_tree_response_or_2025_exposure_opened"]
