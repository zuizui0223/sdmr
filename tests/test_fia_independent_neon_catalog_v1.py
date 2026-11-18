"""No tree-response data: public NEON product metadata source contract."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_independent_neon_catalog_v1 as gate


def payload():
    return {"data":{"productCode":"DP1.10098.001","siteCodes":[
        {"siteCode":"ZZZZ","availableReleases":[
            {"release":"RELEASE-2025","availableMonths":["2024-07"]},
            {"release":"RELEASE-2026","availableMonths":["2018-08","2019-08","2022-08","2024-09"]}]},
        {"siteCode":"WREF","availableReleases":[
            {"release":"RELEASE-2026","availableMonths":["2024-06","2025-07"]}]},
        {"siteCode":"ABBY","availableReleases":[
            {"release":"RELEASE-2026","availableMonths":["2025-08"]}]},
        {"siteCode":"HARV","availableReleases":[]}
    ]}}


def test_full_catalog_preserves_zero_and_missing_longitudinal_unknown():
    x=gate.audit_public_catalog(payload())
    assert x["status"]=="metadata_only_no_tree_response_observed"
    assert x["n_sites_catalog_total"]==4
    assert x["n_sites_with_released_months"]==3
    assert x["n_sites_with_2_plus_distinct_release_years"]==2
    assert x["n_sites_with_available_release_year_span_ge_four"]==1
    assert x["n_sites_with_verified_repeated_individuals"] is None
    assert x["neon_taxonomy_and_FIA_species_crosswalk_verified"] is False
    assert x["later_growth_and_survival_data_accessed"] is False
    assert x["sites"][0]["site"]=="ABBY"
    assert x["sites"][1]["site"]=="HARV"
    assert x["sites"][1]["release_year_span"] is None
    assert x["sites"][-1]["release_months"]==["2018-08","2019-08","2022-08","2024-09"]
    assert gate.DOI=="10.48443/pypa-qf12"
    assert x["no_biological_promotion_authorized"]


def test_release_other_years_never_satisfy_2026_gate():
    data=payload()
    z=data["data"]["siteCodes"][0]
    z["availableReleases"]=[{"release":"RELEASE-2025",
                             "availableMonths":["2010-01","2024-06"]}]
    x=gate.audit_public_catalog(data)
    assert x["n_sites_with_available_release_year_span_ge_four"]==0
    assert x["n_sites_with_released_months"]==2


@pytest.mark.parametrize("mutation,expected",[
    (lambda p:p["data"].update(productCode="DP1.OTHER"),"wrong NEON"),
    (lambda p:p["data"]["siteCodes"].append(p["data"]["siteCodes"][0].copy()),"duplicate NEON site"),
    (lambda p:p["data"]["siteCodes"][0].update(siteCode="invalid"),"four-letter"),
    (lambda p:p["data"]["siteCodes"][0]["availableReleases"][1].update(availableMonths=["2024-99"]),"invalid month"),
    (lambda p:p["data"]["siteCodes"][0]["availableReleases"][1].update(availableMonths=["2024-07","2024-07"]),"duplicate NEON site-month"),
    (lambda p:p["data"]["siteCodes"].clear(),"unavailable"),
    (lambda p:p["data"]["siteCodes"][0]["availableReleases"].append(
        {"release":"RELEASE-2026","availableMonths":["2024-06"]}),"duplicate same-release"),
])
def test_missing_or_drifted_catalog_never_claims_site_count(mutation,expected):
    x=payload()
    mutation(x)
    with pytest.raises(ValueError,match=expected):
        gate.audit_public_catalog(x)


def test_one_metadata_get_only_and_content_hash_receipt(tmp_path):
    calls=[]
    def fetch(url):
        calls.append(url)
        return payload()
    out=gate.run(tmp_path,fetcher=fetch)
    assert calls==["https://data.neonscience.org/api/v0/products/DP1.10098.001"]
    raw_file=tmp_path/"neon_release_2026_public_product_metadata.json"
    assert raw_file.exists()
    data=raw_file.read_bytes().rstrip(b"\n")
    assert hashlib.sha256(data).hexdigest()==out["source_metadata_canonical_json_sha256"]
    assert json.loads((tmp_path/"neon_release_2026_source_gate.json").read_text())["n_sites_catalog_total"]==4
    assert out["n_sites_with_verified_repeated_individuals"] is None
    assert out["NEON_raw_file_endpoint_requires_account_token"]
    assert "DIA" not in out and "STATUSCD" not in out


def test_401_public_metadata_failure_not_zero_eligible(tmp_path):
    def denied(url):
        raise HTTPError(url,401,"Unauthorized",hdrs=None,fp=None)
    out=gate.run(tmp_path,fetcher=denied)
    assert out["status"]=="public_metadata_unavailable_not_zero_sites"
    assert "n_sites_catalog_total" not in out
    assert out["n_sites_with_verified_repeated_individuals"] is None
    assert out["no_raw_data_accessed"]
    assert not (tmp_path/"neon_release_2026_public_product_metadata.json").exists()


def test_public_release_missing_is_fail_closed(tmp_path):
    data=payload()
    for site in data["data"]["siteCodes"]:
        site["availableReleases"]=[]
    out=gate.run(tmp_path,fetcher=lambda _:data)
    assert out["status"]=="public_metadata_unavailable_not_zero_sites"
    assert "target NEON release unavailable" in out["error_message_excerpt"]
    assert out["no_biological_promotion_authorized"]
