"""Official FIA REF_SPECIES name crosswalk for structural candidate codes only.

No plant growth, mortality, status, or DBH columns are read. Source is the
USDA FIADB_REFERENCE.zip published by FIA DataMart. No replacement taxonomy or
hand-corrected names may enter the receipt if this archive is unavailable.
"""
from __future__ import annotations
import argparse
from decimal import Decimal,InvalidOperation
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from zipfile import ZipFile,BadZipFile
import csv

REFERENCE_URL="https://apps.fs.usda.gov/fia/datamart/CSV/FIADB_REFERENCE.zip"
MAX_REFERENCE_BYTES=25_000_000
MAX_REFERENCE_CSV_BYTES=25_000_000


def canonical_code(raw:object)->str:
    txt=str(raw).strip()
    if not txt:raise ValueError("blank species code")
    try:num=Decimal(txt)
    except InvalidOperation:raise ValueError("non-numeric species code") from None
    if not num.is_finite() or num!=num.to_integral_value() or num<1:raise ValueError("invalid species code")
    return str(int(num))


def parse_reference_zip(data:bytes)->tuple[dict[str,dict],dict]:
    with ZipFile(io.BytesIO(data)) as z:
        members=[m for m in z.infolist() if m.filename.upper().endswith("REF_SPECIES.CSV")]
        if len(members)!=1:raise ValueError("REF_SPECIES table missing or ambiguous")
        if members[0].file_size>MAX_REFERENCE_CSV_BYTES:raise ValueError("reference CSV exceeds fixed size cap")
        with z.open(members[0]) as raw:
            stream=io.TextIOWrapper(raw,encoding="utf-8-sig",newline="",errors="strict")
            reader=csv.DictReader(stream)
            keys=set(reader.fieldnames or [])
            if "SPCD" not in keys:raise ValueError("official reference missing SPCD")
            if not ({"GENUS","SPECIES"}<=keys or "SCIENTIFIC_NAME" in keys):
                raise ValueError("official reference missing taxonomic names")
            names={};n=0
            for row in reader:
                n+=1
                try:spcd=canonical_code(row.get("SPCD"))
                except ValueError:continue
                sci=(row.get("SCIENTIFIC_NAME") or "").strip()
                genus=(row.get("GENUS") or "").strip()
                species=(row.get("SPECIES") or "").strip()
                if not sci:sci=" ".join(x for x in (genus,species) if x)
                if not sci:continue
                if spcd in names and names[spcd]["scientific_name"]!=sci:
                    raise ValueError("ambiguous names for same source code")
                names[spcd]={"scientific_name":sci,
                             "common_name":(row.get("COMMON_NAME") or "").strip(),
                             "source_species_code":spcd}
    return names,{"n_raw_reference_rows":n,"n_named_species_codes":len(names),
                  "member":members[0].filename,"columns":sorted(keys)}


def candidate_crosswalk(source_receipt:dict, reference:dict[str,dict])->dict:
    source=source_receipt.get("fia",{}).get("eligible_species",{})
    if not source.get("not_proof_of_survival_growth_or_native_species"):
        raise ValueError("source must explicitly limit biological inference")
    out=[]
    for s in source.get("candidate_spcd") or []:
        code=canonical_code(s["spcd"])
        row={"source_spcd_raw":s["spcd"],"source_spcd_normalized":code,
             "n_supported_states":s["n_supported_states"],"links_by_state":s["links_by_state"],
             "status":"official_reference_matched" if code in reference else "unmatched_official_reference"}
        if code in reference:row.update(reference[code])
        out.append(row)
    return {"n_candidates":len(out),"n_matched":sum(x["status"]=="official_reference_matched" for x in out),
            "taxa":out,"not_response_inference":True}


def download_reference(*,downloader=None)->tuple[bytes|None,dict]:
    try:
        if downloader is None:
            req=Request(REFERENCE_URL,headers={"User-Agent":"sdmr-fia-source-crosswalk/1"})
            with urlopen(req,timeout=55) as fh:
                data=fh.read(MAX_REFERENCE_BYTES+1)
        else:data=downloader(REFERENCE_URL)
        if len(data)>MAX_REFERENCE_BYTES:raise ValueError("reference_archive_over_cap")
        if not data[:2]==b"PK":raise ValueError("reference_not_zip")
        return data,{"status":"ready","size_bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
    except HTTPError as e:return None,{"status":"http_unavailable","http_status":int(e.code)}
    except (URLError,TimeoutError) as e:return None,{"status":"network_unavailable","error_class":type(e).__name__}
    except (ValueError,BadZipFile,OSError) as e:return None,{"status":"source_invalid","error":str(e)[:160]}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-receipt",type=Path,default=Path("evidence/geographic_tree_demography_source_gate_v1/fia_ri_va_wi_identity_linkages.json"))
    p.add_argument("--output",type=Path,default=Path("artifacts/fia_taxon_crosswalk_v1.json"))
    a=p.parse_args()
    source_bytes=a.source_receipt.read_bytes()
    src=json.loads(source_bytes)
    archive,st=download_reference()
    out={"analysis":"fia_official_taxon_crosswalk_v1", "source_receipt_sha256":hashlib.sha256(source_bytes).hexdigest(),
         "reference_source":REFERENCE_URL,"reference_download":st,
         "n_raw_tree_growth_outcomes_opened":0,"no_fitness_or_limiting_driver_claim":True}
    if archive is not None:
        try:
            ref,meta=parse_reference_zip(archive)
            out["reference_table"]=meta
            out["candidate_crosswalk"]=candidate_crosswalk(src,ref)
        except Exception as e:
            out["reference_download"]["status"]="reference_parse_unavailable"
            out["reference_download"]["error_class"]=type(e).__name__
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print("Official FIA taxon-name mapping status:",out['reference_download']['status'],
          "matched",out.get('candidate_crosswalk',{}).get('n_matched'))


if __name__=="__main__":main()
