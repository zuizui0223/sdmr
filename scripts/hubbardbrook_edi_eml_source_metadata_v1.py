#!/usr/bin/env python3
"""Hubbard Brook EDI EML *metadata* gate, three fixed watershed inventories.

No biological response, original CSV, tree/stem row, or census occurrence
opened. EML schemas are NOT proof of complete survey effort, tree identity,
survival, sample zeros, or ecological causal process. All 3 watersheds are in
one physical experimental forest.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET

PROGRAM="sdmr_hubbardbrook_original_EML_metadata_only_v1"
CONFIG=Path("configs/hubbardbrook_edi_tree_source_metadata_v1.json")
MAX_EML_BYTES=4*1024*1024
PREFIX="https://pasta.lternet.edu/package/metadata/eml/knb-lter-hbr"
EXPECTED={
 "WS1":("knb-lter-hbr.446.1",PREFIX+"/446/1","10.6073/pasta/3d0031ea82d308f81ab26000a106b264"),
 "WS5":("knb-lter-hbr.447.1",PREFIX+"/447/1","10.6073/pasta/f50f9bab4936632b49cf93f56750394c"),
 "WS6":("knb-lter-hbr.448.1",PREFIX+"/448/1","10.6073/pasta/1aa4c3ad4c98ed151decc9ea7fa76694"),
}
LOCK="\n".join([
 f"program={PROGRAM}",
 "source_provider=Environmental_Data_Initiative_open_catalog_metadata_only",
 "package_versions=knb-lter-hbr.446.1,knb-lter-hbr.447.1,knb-lter-hbr.448.1",
 "source_sites=Watershed1,Watershed5,Watershed6_one_Hubbard_forest",
 "only_3_exact_version_EML_GETs=true",
 "no_CSV_or_original_entity_bytes_downloaded=true",
 "no_tree_status_date_stem_measurement_values_parsed=true",
 "no_independent_forest_replication_from_nested_watersheds=true",
 "no_full_source_SHA256_or_sampling_opportunity_admission=true",
 "M5_ProductA_unchanged_ProductB_blocked=true",
])+"\n"


def require_metadata_url(url:str)->None:
    p=urlsplit(url)
    if (p.scheme!="https" or p.netloc!="pasta.lternet.edu" or
        url not in [v[1] for v in EXPECTED.values()] or
        p.query or p.fragment or p.username or p.password):
        raise ValueError("not_exact_Hubbard_Brook_original_versioned_EML_metadata")


class ExactMetadataRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        require_metadata_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def validate_config(c:dict)->None:
    if c.get("schema")!="sdmr.hubbard_brook_edi_forest_tree_source_metadata_gate.v1":
        raise ValueError("unfrozen_Hubbard_Brook_source_contract")
    if (c.get("physical_forest_replicates")!=1
        or c.get("nested_source_units")!=3
        or c.get("source_original_tree_responses_opened") is not False
        or c.get("source_original_full_bytes_SHA256_verified") is not False
        or c.get("source_data_files_opened") is not False):
        raise ValueError("Hubbard_Brook_source_replicates_or_Y_status_changed")
    if [p.get("watershed") for p in c.get("packages",[]) ]!=["WS1","WS5","WS6"]:
        raise ValueError("Hubbard_Brook_three_source_versions_not_fixed")
    for d in c["packages"]:
        a=EXPECTED[d["watershed"]]
        if (d["package_id"],d["metadata_url"],d["doi"])!=a:
            raise ValueError("EDI_source_version_DOI_or_URL_substituted")
    m=c.get("method_use",{})
    if not all(m.get(k) is True for k in (
        "no_original_data_Entity_download",
        "no_metadata_header_as_verified_status_opportunity",
        "watershed_is_not_independent_forest",
        "block_new_biological_model_until_original_source_and_response_free_study_gate"
    )):
        raise ValueError("Hubbard_Brook_Estimation_Without_Original_Source_Gate")
    if c["prior_frozen_results"].get("Product_B_blocked") is not True:
        raise ValueError("Product_B_unsafe_promotion")


def _local(tag:str)->str:
    return tag.rsplit("}",1)[-1]


def _first_text(root:ET.Element,name:str)->str|None:
    for node in root.iter():
        if _local(node.tag)==name:
            t=(node.text or "").strip()
            if t:return t
    return None


def parse_EML_schema(raw:bytes,expected_id:str)->dict:
    if not isinstance(raw,bytes) or len(raw)<100 or len(raw)>MAX_EML_BYTES:
        raise ValueError("EDI_original_EML_metadata_bytes_unavailable_or_oversize")
    if not raw.lstrip().startswith((b"<?xml",b"<eml")):
        raise ValueError("provider_did_not_return_original_EML_XML")
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError("invalid_EDI_EML_XML") from e
    if _local(root.tag)!="eml":
        raise ValueError("original_EDI_EML_root_incorrect")
    package_id=root.get("packageId")
    if package_id!=expected_id:
        raise ValueError("EDI_EML_original_package_id_drift_or_absent")
    tables=[]
    for node in root.iter():
        if _local(node.tag) not in {"dataTable","otherEntity"}:
            continue
        fields=[]
        for sub in node.iter():
            if _local(sub.tag)=="attributeName" and sub.text:
                text=sub.text.strip()
                if text and text not in fields:
                    fields.append(text[:150])
        tables.append({
          "source_entity_type":_local(node.tag),
          "original_entity_name":_first_text(node,"entityName"),
          "object_name":_first_text(node,"objectName"),
          "n_original_source_attributes":len(fields),
          "original_source_attribute_names":fields[:150],
          "data_record_values_opened":False,
        })
    rights=[]
    for node in root.iter():
        if _local(node.tag)=="intellectualRights":
            rights.append(" ".join(" ".join(node.itertext()).split())[:500])
    schema_names=[x for t in tables for x in t["original_source_attribute_names"]]
    low=[x.lower() for x in schema_names]
    has_id=any(any(z in x for z in ("tree","stem","tag","individual","unique_id")) for x in low)
    has_time=any(any(z in x for z in ("year","census","date","time")) for x in low)
    has_state=any(any(z in x for z in ("dead","alive","surviv","status","mort")) for x in low)
    has_measure=any(any(z in x for z in ("dbh","diameter","basal","height","growth")) for x in low)
    return {
        "package_id_from_published_EML":package_id,
        "original_EML_sha256":hashlib.sha256(raw).hexdigest(),
        "original_EML_bytes":len(raw),
        "dataset_title":_first_text(root,"title"),
        "n_original_data_entity_descriptions":len(tables),
        "original_data_entity_schema_summaries":tables,
        "declared_intellectual_rights_metadata":rights,
        "attribute_schema_has_candidate_tree_or_stem_identifier":has_id,
        "attribute_schema_has_candidate_census_time":has_time,
        "attribute_schema_has_candidate_status_or_survival":has_state,
        "attribute_schema_has_candidate_stem_dimension":has_measure,
        "source_metadata_includes_verified_survey_zeros":False,
        "source_metadata_includes_verified_direct_death":False,
        "original_biological_rows_opened":False,
    }


def metadata_get(url:str)->bytes:
    require_metadata_url(url)
    req=Request(url,headers={
        "Accept":"application/xml,text/xml",
        "User-Agent":"sdmr-hubbardbrook-EML-metadata-only/1.0",
    })
    with build_opener(ExactMetadataRedirect()).open(req,timeout=50) as f:
        require_metadata_url(f.geturl())
        raw=f.read(MAX_EML_BYTES+1)
        if len(raw)>MAX_EML_BYTES:
            raise ValueError("EDI_original_EML_metadata_exceeds_byte_cap")
        return raw


def run_source_metadata(c:dict)->dict:
    validate_config(c)
    out=[]
    for p in c["packages"]:
        try:
            record=parse_EML_schema(metadata_get(p["metadata_url"]),p["package_id"])
            record["original_source_watershed"]=p["watershed"]
            record["publisher_source_DOI"]=p["doi"]
            out.append(record)
        except HTTPError as e:
            return {
                "status":"EDI_original_metadata_HTTP_STOP",
                "first_blocked_source":p["package_id"],
                "reason":f"http_{e.code}",
                "n_metadata_schemas_verified":len(out),
                "verified_metadata_schemas":out,
            }
        except (URLError,OSError,TimeoutError):
            return {
                "status":"EDI_original_metadata_network_STOP",
                "first_blocked_source":p["package_id"],
                "reason":"network_or_tls",
                "n_metadata_schemas_verified":len(out),
                "verified_metadata_schemas":out,
            }
        except (ValueError,KeyError,TypeError) as e:
            return {
                "status":"EDI_original_metadata_schema_integrity_STOP",
                "first_blocked_source":p["package_id"],
                "reason":type(e).__name__+":"+str(e)[:100],
                "n_metadata_schemas_verified":len(out),
                "verified_metadata_schemas":out,
            }
    return {
        "status":"three_watershed_original_EDI_EML_schema_metadata_only",
        "n_metadata_schemas_verified":len(out),
        "verified_metadata_schemas":out,
        "three_watersheds_within_one_physical_forest":True,
        "potential_independent_forest_relative_to_Harvard":True,
        "actual_tree_level_observation_eligibility_verified":False,
        "original_data_files_downloaded":0,
        "new_biological_responses_opened":0,
        "new_process_models_fit":0,
        "Product_B_unblocked":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",type=Path,default=CONFIG)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--execute-lock",type=Path)
    a=p.parse_args()
    if a.preflight_only==(a.execute_lock is not None):
        p.error("exactly one preflight/execute-lock")
    cfg=json.loads(a.config.read_text())
    validate_config(cfg)
    if a.execute_lock and a.execute_lock.read_text()!=LOCK:
        raise ValueError("Hubbard_EML_first_original_source_lock_changed")
    result={"status":"EML_source_free_preflight_only"} if a.preflight_only else run_source_metadata(cfg)
    payload={
        "schema":"sdmr.hubbard_brook_original_EML_source_first_receipt.v1",
        "program":PROGRAM,
        "preflight":a.preflight_only,
        "original_forest_replicates":1,
        "original_source_CSV_or_biological_rows_opened":False,
        "new_ecological_models_fit":0,
        "independent_empirical_process_test_performed":False,
        "Product_B_unblocked":False,
        "result":result,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print("Hubbard Brook fixed EDI EML-only source admission:",result["status"])

if __name__=="__main__":
    main()
