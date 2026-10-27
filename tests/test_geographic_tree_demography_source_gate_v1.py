"""Offline structural checks; no biological outcome columns inspected."""
import importlib.util
import io
import pathlib
import sqlite3
import zipfile

import pytest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("tree_source",ROOT/"experiments/geographic_tree_demography_source_gate_v1.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def sample_zip(state="RI",invalid=False):
    source="CN,PREV_TRE_CN,SPCD,INVYR,PLT_CN,DIA,STATUSCD\n"
    source+=("a,,316,2010,plot1,10,1\n"
             "b,a,316,2015,plot2,25,2\n"
             "c,,131,2010,plot1,11,1\n"
             "d,c,131,2015,plot2,14,1\n"
             "e,b,316,2020,plot3,99,2\n"
             "f,e,999,2025,plot4,2,1\n")
    if invalid:source=source.replace("b,a,316,2015","a,a,316,2015")
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{state}_TREE.csv",source)
    return stream.getvalue()


def test_neon_release_count_does_not_claim_repeated_individuals():
    payload={"data":{"productCode":mod.NEON_PRODUCT,"siteCodes":[
        {"siteCode":"HARV","availableReleases":[
             {"release":"RELEASE-2025","availableMonths":["2024-08"]},
             {"release":"RELEASE-2026","availableMonths":["2019-09","2021-09","2022-10"]}]},
        {"siteCode":"WREF","availableReleases":[{"release":"RELEASE-2026","availableMonths":["2023-10"]}]}
    ]}}
    out=mod.neon_catalog(payload)
    assert out["n_sites"]==2
    assert out["n_sites_with_2_plus_available_years"]==1
    assert out["do_not_interpret_as_remeasured_trees"]
    assert out["sites"][0]["n_release_months"]==3
    probe=mod.neon_anonymous_data_probe(out,fetch_status=lambda _:401)
    assert probe["status"]=="api_token_required" and probe["direct_table_access"] is False


def test_neon_mismatch_must_fail_not_reinterpret():
    with pytest.raises(ValueError,match="mismatch"):
        mod.neon_catalog({"data":{"productCode":"DP1.OTHER","siteCodes":[]}})


def test_zip_and_only_identity_fields_are_inspected(tmp_path):
    r=mod.process_state_zip("RI",tmp_path,reader=lambda s:sample_zip(s))
    assert r["status"]=="ready"
    assert r["n_raw_rows"]==6
    assert r["n_admitted_identity_rows"]==6
    assert r["n_strict_forward_same_species_links"]==3
    assert r["n_with_internal_same_species_prior"]==3
    assert {x["spcd"]:x["n_linked_trees"] for x in r["per_species"]}=={"316":2,"131":1}
    assert not r["growth_or_mortality_evaluated"]


def test_duplicate_cn_rejected(tmp_path):
    r=mod.process_state_zip("RI",tmp_path,reader=lambda _:sample_zip(invalid=True))
    assert r["status"]=="invalid_source_schema_or_duplicates"
    assert "duplicate_cn" in r["error"]


def test_archive_restricted_to_predeclared_states():
    with pytest.raises(ValueError,match="outside frozen"):
        mod.fia_archive_url("CA")
    assert mod.fia_archive_url("VA")=="https://apps.fs.usda.gov/fia/datamart/CSV/VA_TREE.zip"


def test_candidate_nominations_require_two_states():
    states=[
        {"state":"RI","status":"ready","per_species":[{"spcd":"316","n_linked_trees":50},{"spcd":"131","n_linked_trees":22}]},
        {"state":"VA","status":"ready","per_species":[{"spcd":"316","n_linked_trees":40},{"spcd":"131","n_linked_trees":80}]},
        {"state":"WI","status":"http_unavailable"}
    ]
    out=mod.nominate_cross_state_species(states)
    assert out["n_candidate_spcd"]==1
    assert out["candidate_spcd"][0]["spcd"]=="316"
    assert out["not_proof_of_survival_growth_or_native_species"]


def test_fake_no_data_is_not_zero(tmp_path):
    r=mod.fetch_zip("RI",tmp_path,reader=lambda s:b"not a zip")
    assert r["status"]=="source_invalid"
    assert "n_raw_rows" not in r
