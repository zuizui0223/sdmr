"""Pre-response source eligibility gate for repeated tree measurements.

Two INDEPENDENT public census routes, no opportunistic after-the-fact site search:
  NEON RELEASE-2026: public product metadata and HTTP token-access status only;
  USDA FIA DataMart: raw TREE.zip from three frozen U.S. states, linkage counts.

No survival, death, stem growth, plant stress, fitness, or driver-shift outcomes are
read or calculated. A PREV_TRE_CN link is not a verified surviving tree. The gate
reports eligibility to build a subsequent strictly prospective response study.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import zipfile

NEON_PRODUCT="DP1.10098.001"
NEON_RELEASE="RELEASE-2026"
NEON_URL=f"https://data.neonscience.org/api/v0/products/{NEON_PRODUCT}"
FIA_BASE="https://apps.fs.usda.gov/fia/datamart/CSV/"
FIA_STATES=("RI", "VA", "WI")  # geographically predeclared; not selected by demographic outcome
FIA_TABLE="TREE"
MIN_LINKS_PER_STATE=30
MIN_STATES_PER_TAXON=2
MIN_DIFFERENT_YEARS=2
MAX_ARCHIVE_BYTES=135_000_000  # one archive cap
MAX_UNCOMPRESSED_BYTES=1_800_000_000


def fetch_small_json(url: str, *, fetcher=None) -> dict:
    if fetcher is not None:
        return fetcher(url)
    req=Request(url,headers={"User-Agent":"sdmr-tree-demography-source-gate/0.1", "Accept":"application/json"})
    with urlopen(req,timeout=35) as response:
        raw=response.read(5_000_001)
        if len(raw)>5_000_000:
            raise ValueError("metadata exceeds allowed response cap")
        obj=json.loads(raw)
        if not isinstance(obj,dict): raise ValueError("NEON product metadata must be an object")
        return obj


def neon_catalog(payload: dict) -> dict:
    data=payload.get("data") or {}
    if data.get("productCode")!=NEON_PRODUCT: raise ValueError("NEON metadata product ID mismatch")
    sites=data.get("siteCodes")
    if not isinstance(sites,list): raise ValueError("NEON siteCodes missing")
    rows=[]
    for item in sites:
        code=str(item.get("siteCode") or "")
        if not code.isalpha() or len(code)!=4: continue
        months=set()
        for release in item.get("availableReleases") or []:
            if release.get("release")==NEON_RELEASE:
                months.update(str(m) for m in release.get("availableMonths") or [] if str(m)[:4].isdigit())
        rows.append({"site":code,"release_months":sorted(months),
                     "n_release_months":len(months),
                     "n_release_years":len({m[:4] for m in months}),
                     "months_status":"metadata_only_not_repeat_individuals"})
    rows.sort(key=lambda v:v["site"])
    repeated=[v for v in rows if v["n_release_years"]>=MIN_DIFFERENT_YEARS]
    return {"product":NEON_PRODUCT,"release":NEON_RELEASE,"n_sites":len(rows),
            "n_sites_with_2_plus_available_years":len(repeated),"sites":rows,
            "do_not_interpret_as_remeasured_trees":True}


def neon_anonymous_data_probe(catalog:dict, *, fetch_status=None)->dict:
    sites=[s for s in catalog["sites"] if s["n_release_months"]>0]
    if not sites:
        return {"status":"no_release_months","attempted":False,"direct_table_access":False}
    # Deterministic first alphabetical site/month, no species/demography conditioning.
    site=sites[0];month=site["release_months"][0]
    url=f"https://data.neonscience.org/api/v0/data/{NEON_PRODUCT}/{site['site']}/{month}?release={NEON_RELEASE}"
    if fetch_status is not None: status=fetch_status(url)
    else:
        req=Request(url,headers={"User-Agent":"sdmr-tree-demography-source-gate/0.1"})
        try:
            with urlopen(req,timeout=25) as response:
                response.read(500)   # NEVER download data file here
                status=int(response.status)
        except HTTPError as e: status=int(e.code)
        except (URLError,TimeoutError) as e:
            return {"status":"network_unavailable","reason":type(e).__name__,
                    "attempted":True,"direct_table_access":False,"site":site['site'],"month":month}
    if status in (401,403): label="api_token_required"
    elif status==200:label="metadata_endpoint_open_not_data_file_confirmed"
    elif status==404:label="data_endpoint_missing_or_filtered"
    else:label=f"http_{status}"
    return {"status":label,"http_status":status,"attempted":True,
            "direct_table_access":False, "site":site['site'],"month":month,
            "no_individual_data_downloaded":True}


def fia_archive_url(state: str)->str:
    if state not in FIA_STATES: raise ValueError("FIA state outside frozen source panel")
    return FIA_BASE+f"{state}_{FIA_TABLE}.zip"


def fetch_zip(state:str,directory:Path, *, reader=None) -> dict:
    """Write archived source bytes to disk and independently preserve SHA-256.

    `reader` is an optional fixture returning raw ZIP bytes for offline tests.
    On network errors, return an unavailable state, not fake zero records.
    """
    url=fia_archive_url(state)
    result={"state":state,"url":url,"status":"unavailable","n_bytes":0}
    directory.mkdir(parents=True,exist_ok=True)
    dest=directory/f"{state}_TREE.zip"
    sha=hashlib.sha256()
    try:
        if reader is not None:
            source=io.BytesIO(reader(state))
        else:
            request=Request(url,headers={"User-Agent":"sdmr-tree-demography-source-gate/0.1"})
            source=urlopen(request,timeout=55)
        with source, dest.open("wb") as out:
            n=0
            while True:
                buf=source.read(1024*1024)
                if not buf:break
                n+=len(buf)
                if n>MAX_ARCHIVE_BYTES:
                    raise ValueError("archive_above_predeclared_size_limit")
                out.write(buf);sha.update(buf)
        if not zipfile.is_zipfile(dest):raise ValueError("not_zip_file")
        with zipfile.ZipFile(dest) as z:
            infos=[x for x in z.infolist() if not x.is_dir()]
            matches=[x for x in infos if x.filename.upper().endswith(f"{state}_{FIA_TABLE}.CSV") or x.filename.upper()==f"{FIA_TABLE}.CSV"]
            if len(matches)!=1:raise ValueError("ambiguous_or_missing_tree_table")
            if matches[0].file_size>MAX_UNCOMPRESSED_BYTES:raise ValueError("uncompressed_tree_table_over_cap")
            result.update({"status":"ready","n_bytes":n,"sha256":sha.hexdigest(),
                           "member":matches[0].filename,"member_uncompressed_bytes":matches[0].file_size})
    except HTTPError as e: result.update({"status":"http_unavailable","http_status":int(e.code)})
    except (TimeoutError,URLError) as e:result.update({"status":"network_unavailable","error_class":type(e).__name__})
    except (ValueError,OSError,zipfile.BadZipFile) as e:
        result.update({"status":"source_invalid","error":str(e)[:120]})
    if result["status"]!="ready":dest.unlink(missing_ok=True)
    return result


def _create_tree_db(con:sqlite3.Connection):
    con.execute("CREATE TABLE tree(cn TEXT PRIMARY KEY,prev TEXT,spcd TEXT, invyr INTEGER, plt_cn TEXT)")
    con.execute("CREATE INDEX tree_prev_idx ON tree(prev)")
    con.execute("CREATE INDEX tree_spcd_idx ON tree(spcd)")


def ingest_tree_csv(source, con:sqlite3.Connection)->dict:
    """Read ONLY linkage/taxonomy/date keys. Never read diameter or status.

    Validate unique identifiers, year, and return complete denominators.
    """
    text=io.TextIOWrapper(source,encoding="utf-8-sig",errors="strict",newline="")
    try:
        rdr=csv.DictReader(text)
        needed={"CN","PREV_TRE_CN","SPCD","INVYR","PLT_CN"}
        if not rdr.fieldnames or needed-set(rdr.fieldnames):
            raise ValueError("missing linkage/identity fields: "+str(sorted(needed-set(rdr.fieldnames or []))))
        count=0;bad_rows=Counter();batch=[]
        for row in rdr:
            count+=1
            cn=(row.get("CN") or "").strip()
            if not cn:
                bad_rows["missing_cn"]+=1;continue
            spcd=(row.get("SPCD") or "").strip()
            prev=(row.get("PREV_TRE_CN") or "").strip()
            plt=(row.get("PLT_CN") or "").strip()
            year=(row.get("INVYR") or "").strip()
            if not spcd or not year.isdecimal() or not plt:
                bad_rows["missing_species_year_or_plot"]+=1;continue
            batch.append((cn,prev,spcd,int(year),plt))
            if len(batch)>=3000:
                try:con.executemany("INSERT INTO tree VALUES (?,?,?,?,?)",batch)
                except sqlite3.IntegrityError:raise ValueError("duplicate_cn")
                batch=[]
        if batch:
            try:con.executemany("INSERT INTO tree VALUES (?,?,?,?,?)",batch)
            except sqlite3.IntegrityError:raise ValueError("duplicate_cn")
        con.commit()
        return {"n_raw_rows":count,"n_rejected_identity_rows":sum(bad_rows.values()),
                "identity_rejection_reasons":dict(sorted(bad_rows.items())),
                "n_admitted_identity_rows":int(con.execute("SELECT COUNT(*) FROM tree").fetchone()[0])}
    finally:text.detach()


def summarize_fia_links(con:sqlite3.Connection)->dict:
    """Identity-link sufficient counts, not live/dead status or growth rates."""
    # Only same species and forward-year links, internal to the single state archive.
    rows=con.execute("""SELECT c.spcd, COUNT(*) n_links,
             COUNT(DISTINCT c.plt_cn) n_distinct_current_plots,
             COUNT(DISTINCT c.invyr) n_current_years,
             MIN(p.invyr) min_prior_year, MAX(c.invyr) max_current_year
        FROM tree c JOIN tree p ON c.prev=p.cn
        WHERE c.prev!='' AND c.spcd=p.spcd AND c.invyr>p.invyr
        GROUP BY c.spcd ORDER BY n_links DESC,c.spcd""").fetchall()
    mapped=[{"spcd":str(s),"n_linked_trees":int(n),"n_current_plot_visits":int(k),
             "n_current_years":int(y),"earliest_previous_year":int(lo),"latest_current_year":int(hi)}
            for s,n,k,y,lo,hi in rows]
    other=dict(con.execute("""SELECT 'n_with_prev_key',count(*) FROM tree WHERE prev!=''
       UNION ALL SELECT 'n_with_any_same_species_link',count(*) FROM tree c
       JOIN tree p ON c.prev=p.cn WHERE c.prev!='' AND c.spcd=p.spcd"""))
    return {"n_with_prior_key":int(other["n_with_prev_key"]),
            "n_with_internal_same_species_prior":int(other["n_with_any_same_species_link"]),
            "n_strict_forward_same_species_links":sum(x["n_linked_trees"] for x in mapped),
            "per_species":mapped,"growth_or_mortality_evaluated":False}


def process_state_zip(state:str,workdir:Path,*,reader=None)->dict:
    archive=fetch_zip(state,workdir,reader=reader)
    if archive["status"]!="ready":return archive
    db=workdir/f"{state}_key_pairs.sqlite"
    con=sqlite3.connect(db)
    try:
        _create_tree_db(con)
        with zipfile.ZipFile(workdir/f"{state}_TREE.zip") as z:
            with z.open(archive["member"]) as src:
                identity=ingest_tree_csv(src,con)
        archive.update(identity);archive.update(summarize_fia_links(con))
    except (ValueError,UnicodeError,sqlite3.Error) as e:
        archive.update({"status":"invalid_source_schema_or_duplicates","error":str(e)[:180]})
    finally:
        con.close();db.unlink(missing_ok=True)
        # Source ZIP retention in Actions artifact only if explicitly requested;
        # don't silently upload specimen-level records to repo.
    return archive


def nominate_cross_state_species(states:list[dict])->dict:
    counts=defaultdict(dict)
    for item in states:
        if item.get("status")!="ready":continue
        for sp in item.get("per_species") or []:
            if sp["n_linked_trees"]>=MIN_LINKS_PER_STATE:
                counts[sp["spcd"]][item["state"]]=sp["n_linked_trees"]
    candidates=[{"spcd":sp,"n_supported_states":len(values),"links_by_state":values,
                 "n_total_links_across_qualifying_states":sum(values.values())}
                for sp,values in counts.items() if len(values)>=MIN_STATES_PER_TAXON]
    candidates.sort(key=lambda r:(-r["n_supported_states"],-r["n_total_links_across_qualifying_states"],r["spcd"]))
    return {"nomination_rule":{"minimum_prior_links_per_state":MIN_LINKS_PER_STATE,
              "minimum_states":MIN_STATES_PER_TAXON},
            "n_candidate_spcd":len(candidates),"candidate_spcd":candidates,
            "not_proof_of_survival_growth_or_native_species":True}


def run_gate(*,out:Path,cache:Path,neon_only:bool=False,fia_only:bool=False,
             fia_states=FIA_STATES)->dict:
    receipt={"analysis":"tree_demography_pre_response_source_gate_v1",
             "as_of_utc":"2026-10-19","closed_product_a_unchanged":True,
             "raw_growth_death_status_not_opened":True,
             "claims_allowed":"availability and identity-link counts only"}
    if not fia_only:
        try:
            metadata=fetch_small_json(NEON_URL)
            source_sha=hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest()
            cat=neon_catalog(metadata)
            cat["api_metadata_json_sha256"]=source_sha
            cat["anonymous_probe"]=neon_anonymous_data_probe(cat)
            receipt["neon"]=cat
        except Exception as e:
            receipt["neon"]={"status":"metadata_unavailable","error_class":type(e).__name__,
                             "no_vegetation_data_downloaded":True}
    if not neon_only:
        with tempfile.TemporaryDirectory(prefix="fia_pre_response_",dir=cache) as temp:
            results=[process_state_zip(s,Path(temp)) for s in fia_states]
        receipt["fia"]={"states":results,"eligible_species":nominate_cross_state_species(results),
                        "downloaded_survey_data_not_submitted_to_git":True,
                        "plot_coordinates_and_survey_weights_not_checked":True}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    return receipt


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path("artifacts/tree_demography_source_gate_v1.json"))
    p.add_argument("--cache",type=Path,default=Path("artifacts"))
    p.add_argument("--neon-only",action="store_true")
    p.add_argument("--fia-only",action="store_true")
    a=p.parse_args()
    if a.neon_only and a.fia_only:p.error("choose at most one of --neon-only or --fia-only")
    a.cache.mkdir(parents=True,exist_ok=True)
    r=run_gate(out=a.output,cache=a.cache,neon_only=a.neon_only,fia_only=a.fia_only)
    if "neon" in r:
        print("NEON site metadata:",r['neon'].get('n_sites'),"2+ years",r['neon'].get('n_sites_with_2_plus_available_years'),
              "probe",r['neon'].get('anonymous_probe',{}).get('status'))
    if "fia" in r:
        print("FIA state archives",[(s['state'],s['status'],s.get('n_strict_forward_same_species_links')) for s in r['fia']['states']])
        print("cross-state identity-linked taxon codes",r['fia']['eligible_species']['n_candidate_spcd'])


if __name__=="__main__":main()
