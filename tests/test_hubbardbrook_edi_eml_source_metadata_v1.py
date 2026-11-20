"""Source-free three-EDI-package XML-only science gate, no tree response values."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

s=Path("scripts/hubbardbrook_edi_eml_source_metadata_v1.py")
spec=importlib.util.spec_from_file_location("hbr_edi_metadata_only",s)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def contract():
    return json.loads(Path("configs/hubbardbrook_edi_tree_source_metadata_v1.json").read_text())


def eml(pkg,attrs=None):
    attrs=attrs or ("treeTag","year","dbh_mm","species")
    fields="".join(f"<attribute><attributeName>{x}</attributeName></attribute>" for x in attrs)
    txt=f"""<?xml version="1.0" encoding="UTF-8"?>
    <eml packageId="{pkg}" xmlns="eml://ecoinformatics.org/eml-2.2.0">
      <dataset><title>Sample inventory metadata, no real tree data</title>
        <intellectualRights><para>Creative Commons Attribution 4.0</para></intellectualRights>
        <dataTable>
          <entityName>source_tree_inventory.csv</entityName>
          <physical><objectName>tree_inventory.csv</objectName></physical>
          <attributeList>{fields}</attributeList>
        </dataTable></dataset>
    </eml>"""
    return txt.encode()


def test_three_exact_edi_source_versions_one_ecosystem(contract):
    mod.validate_config(contract)
    assert [p["package_id"] for p in contract["packages"]]==[
        "knb-lter-hbr.446.1","knb-lter-hbr.447.1","knb-lter-hbr.448.1"
    ]
    assert contract["physical_forest_replicates"]==1
    assert contract["nested_source_units"]==3
    assert contract["method_use"]["source_visit_effort_and_zero_opportunity_unknown"]
    assert contract["method_use"]["source_individual_tree_ID_stability_unknown"]
    assert contract["method_use"]["watershed_is_not_independent_forest"]
    assert contract["source_data_files_opened"] is False
    assert contract["source_original_tree_responses_opened"] is False


@pytest.mark.parametrize("change",[
    lambda d:d["packages"][0].update(package_id="knb-lter-hbr.446.9"),
    lambda d:d["packages"][1].update(metadata_url="https://another.example/source"),
    lambda d:d.update(physical_forest_replicates=3),
    lambda d:d["method_use"].update(no_metadata_header_as_verified_status_opportunity=False),
    lambda d:d["prior_frozen_results"].update(Product_B_blocked=False),
])
def test_contract_changes_cannot_promote_EML_to_field_test(contract,change):
    c=deepcopy(contract)
    change(c)
    with pytest.raises(ValueError):
        mod.validate_config(c)


def test_EML_schema_only_does_not_see_biological_tree_rows():
    raw=eml("knb-lter-hbr.446.1",attrs=[
        "treeTag","year","dbh_mm","status","sourceSurveyID",
    ])
    x=mod.parse_EML_schema(raw,"knb-lter-hbr.446.1")
    assert x["original_EML_bytes"]==len(raw)
    assert len(x["original_EML_sha256"])==64
    assert x["package_id_from_published_EML"]=="knb-lter-hbr.446.1"
    assert x["n_original_data_entity_descriptions"]==1
    assert x["original_data_entity_schema_summaries"][0]["n_original_source_attributes"]==5
    assert x["attribute_schema_has_candidate_tree_or_stem_identifier"]
    assert x["attribute_schema_has_candidate_census_time"]
    assert x["attribute_schema_has_candidate_status_or_survival"]
    assert x["attribute_schema_has_candidate_stem_dimension"]
    assert not x["original_biological_rows_opened"]
    assert not x["source_metadata_includes_verified_survey_zeros"]
    assert not x["source_metadata_includes_verified_direct_death"]


def test_metadata_fields_cannot_be_assumed_to_prove_survey_coverage():
    x=mod.parse_EML_schema(eml("knb-lter-hbr.447.1",attrs=["dbh_mm"]),
                           "knb-lter-hbr.447.1")
    assert not x["attribute_schema_has_candidate_tree_or_stem_identifier"]
    assert not x["attribute_schema_has_candidate_census_time"]
    assert not x["attribute_schema_has_candidate_status_or_survival"]
    assert x["attribute_schema_has_candidate_stem_dimension"]
    assert not x["source_metadata_includes_verified_survey_zeros"]


def test_source_package_identity_xml_or_nonXML_stop():
    with pytest.raises(ValueError,match="package_id_drift"):
        mod.parse_EML_schema(eml("knb-lter-hbr.447.1"),"knb-lter-hbr.446.1")
    for broken in [b"<html>Forbidden</html>",b"",b"{\"error\":\"not found\"}"]:
        with pytest.raises(ValueError):
            mod.parse_EML_schema(broken,"knb-lter-hbr.446.1")


def test_explicit_whitelist_metadata_urls_only(contract):
    url=contract["packages"][1]["metadata_url"]
    mod.require_metadata_url(url)
    for wrong in [
        url.replace("metadata/eml","data/eml"),
        url.replace("/447/1","/447/2"),
        url.replace("https:","http:"),
        "https://portal.edirepository.org/nis/metadataviewer?packageid=knb-lter-hbr.447.1",
    ]:
        with pytest.raises(ValueError):
            mod.require_metadata_url(wrong)


def test_mock_three_source_gets_is_still_non_biological(contract,monkeypatch):
    calls=[]
    def fake(url):
        calls.append(url)
        pkg=next(p["package_id"] for p in contract["packages"]
                 if p["metadata_url"]==url)
        return eml(pkg)
    monkeypatch.setattr(mod,"metadata_get",fake)
    q=mod.run_source_metadata(contract)
    assert q["status"]=="three_watershed_original_EDI_EML_schema_metadata_only"
    assert len(calls)==3
    assert q["n_metadata_schemas_verified"]==3
    assert q["three_watersheds_within_one_physical_forest"]
    assert not q["actual_tree_level_observation_eligibility_verified"]
    assert q["new_biological_responses_opened"]==0
    assert q["new_process_models_fit"]==0
    assert not q["Product_B_unblocked"]


def test_preflight_never_touches_real_edi_metadata(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"metadata_get",lambda *_: (_ for _ in ()).throw(
        AssertionError("preflight did a network GET")))
    p=tmp_path/"pre.json"
    monkeypatch.setattr(sys,"argv",["test","--preflight-only","--out",str(p)])
    mod.main()
    o=json.loads(p.read_text())
    assert o["result"]["status"]=="EML_source_free_preflight_only"
    assert not o["original_source_CSV_or_biological_rows_opened"]
    assert o["new_ecological_models_fit"]==0
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK.replace("446.1","446.2"))
    monkeypatch.setattr(sys,"argv",["test","--execute-lock",str(bad),
                                    "--out",str(tmp_path/"out.json")])
    with pytest.raises(ValueError,match="source_lock_changed"):
        mod.main()
