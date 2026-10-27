"""Pre-response source census: new FIA TREE/COND + pinned successor PLOT + NOAA.

Never reads TREE.STATUSCD, DIA or tree growth. Source and opportunity ONLY.
No inference of climatic limitation, population effects or competition.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

STATES = ("RI", "VA", "WI")
FIPS = {"RI":"44", "VA":"51", "WI":"55"}
SPECIES = ("68","129","261","316","318","371","531","541","743","762","802","833","837")
BASE = "https://apps.fs.usda.gov/fia/datamart/CSV/"
# Technical maxima, not outcome-dependent sample restrictions.
LIMIT_BYTES = {"PLOT": 320_000_000, "COND": 320_000_000, "TREE": 360_000_000}
CSV_UNPACKED_LIMIT = 3_800_000_000
MIN_CLIMATE_MONTHS = 6
MIN_PLOTS_FOR_EXPLORATORY_MODEL = 8
MIN_COUNTIES_FOR_EXPLORATORY_MODEL = 3
MIN_LINKS_FOR_EXPLORATORY_MODEL = 30


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_inputs(plot_manifest: dict, climate_receipt: dict, climate_path: Path):
    if (plot_manifest.get("study") != "fia_noaa_new_plot_version_successor_v2"
            or not plot_manifest.get("original_frozen_TREE_growth_not_reanalysed")
            or plot_manifest.get("n_new_source_complete_states") != 3):
        raise ValueError("New PLOT successor receipt not source-only and 3/3 complete")
    if climate_receipt.get("study") != "fia_noaa_county_climate_pre_response_v1":
        raise ValueError("NOAA pre-response receipt not recognized")
    if climate_receipt.get("climate_csv_sha256") != sha(climate_path):
        raise ValueError("NOAA climate CSV changed")
    if climate_receipt.get("climate_csv_rows") != 43890:
        raise ValueError("NOAA 43890-row denominator changed")
    if tuple(s.get("state") for s in plot_manifest["states"]) != STATES:
        raise ValueError("PLOT states/order changed")
    hashes = {}
    for st, record in zip(STATES,plot_manifest["states"]):
        if record.get("status") != "successor_new_plot_climate_ready":
            raise ValueError(f"{st}: original PLOT successor not source eligible")
        digest = record.get("new_plot_source_sha256")
        if not isinstance(digest,str) or len(digest) != 64:
            raise ValueError(f"{st}: PLOT SHA not fixed")
        hashes[st] = digest
    return hashes


def fetch_zip(state, table, directory: Path, *, fetcher=None):
    if state not in STATES or table not in LIMIT_BYTES:
        raise ValueError("Invalid fixed state/table")
    url = BASE + state + "_" + table + ".zip"
    dest = directory / (state + "_" + table + ".zip")
    info = {"state":state,"table":table,"url":url,"status":"unavailable"}
    try:
        src = io.BytesIO(fetcher(state,table)) if fetcher else urlopen(Request(url, headers={"User-Agent":"sdmr-pre-response-climate-fia-v3"}), timeout=100)
        count = 0;h=hashlib.sha256()
        with src,dest.open('wb') as f:
            while True:
                b=src.read(1024*1024)
                if not b: break
                count+=len(b)
                if count > LIMIT_BYTES[table]:
                    raise ValueError('FIA '+table+' exceeds fixed archive cap')
                h.update(b);f.write(b)
        with ZipFile(dest) as z:
            matches=[a for a in z.infolist() if not a.is_dir() and a.filename.upper().endswith(state+"_"+table+".CSV")]
            if len(matches)!=1:raise ValueError("FIA CSV member missing/ambiguous")
            if matches[0].file_size > CSV_UNPACKED_LIMIT:raise ValueError("FIA CSV uncompressed cap")
        info.update({"status":"ready","sha256":h.hexdigest(),"bytes":count,"member":matches[0].filename,
                     "uncompressed_bytes":matches[0].file_size})
    except Exception as e:
        # Preserve *all* missing/changed sources as nonavailable. Do not impute.
        info.update({"status":"unavailable","error":f"{type(e).__name__}: {str(e)[:160]}"})
        dest.unlink(missing_ok=True)
    return info,dest


def load_climate(file):
    climate={};n=0
    with Path(file).open(encoding='utf-8',newline='') as f:
        rd=csv.DictReader(f)
        if set(rd.fieldnames or []) != {"fips_county","year","month","temperature_c","precipitation_mm"}:
            raise ValueError("NOAA climate schema drift")
        for row in rd:
            key=(row['fips_county'],int(row['year']),int(row['month']))
            if key in climate: raise ValueError("Duplicate NOAA county-month")
            climate[key]=(float(row['temperature_c']),float(row['precipitation_mm']))
            n+=1
    if n !=43890:raise ValueError("NOAA record-count drift")
    return climate


def month_index(ym):
    return ym[0]*12+ym[1]


def interval_exposure(index, county, start, stop):
    if not (start and stop and county):return None
    a,b=month_index(start),month_index(stop)
    if not 0 < b-a <= 252: return None
    vals=[]
    for year in range(start[0],stop[0]+1):
        for month in range(4,10):
            if a < year*12+month < b:
                value=index.get((county,year,month))
                if value is None:return None
                vals.append(value)
    if len(vals)<MIN_CLIMATE_MONTHS:return None
    return {"n_months":len(vals),"temperature_c":sum(x[0] for x in vals)/len(vals),
            "precipitation_mm_per_six_months":6*sum(x[1] for x in vals)/len(vals),
            "calendar_interval_years":(b-a)/12}


def read_plots(path,member,state,climate):
    out={};qc=Counter()
    with ZipFile(path) as z,z.open(member) as stream:
        rd=csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig',newline=''))
        req={'CN','PREV_PLT_CN','STATECD','COUNTYCD','MEASYEAR','MEASMON'}
        if req-set(rd.fieldnames or []):raise ValueError("FIA PLOT required columns missing")
        for row in rd:
            qc['n_plot_rows']+=1
            cn=str(row['CN'] or '').strip()
            if not cn or cn in out:raise ValueError("PLOT CN duplicate/missing")
            try:
                state_code=str(int(float(row['STATECD'])))
                county=int(float(row['COUNTYCD']))
                year=int(row['MEASYEAR']);month=int(row['MEASMON'])
                if state_code!=str(int(FIPS[state])) or not 0<county<=999 or not 1850<year<=2030 or not 1<=month<=12:
                    raise ValueError('bad county/time')
                fips=FIPS[state]+f'{county:03d}'
                date=(year,month)
            except (ValueError,TypeError):
                fips=None;date=None;qc['invalid_county_or_date']+=1
            out[cn]=(str(row['PREV_PLT_CN'] or '').strip(),fips,date)
    # Use only pairwise PLOT chains, independent of tree records.
    eligible={}
    for now,(before,county,end) in out.items():
        if not before:continue
        old=out.get(before)
        if not old:qc['prior_plot_not_found']+=1;continue
        if old[1] != county:qc['county_drift_or_missing']+=1;continue
        exposure=interval_exposure(climate,county,old[2],end)
        if exposure is None:qc['no_complete_interval_climate']+=1;continue
        eligible[now]=(before,county,exposure)
    qc['n_eligible_plot_intervals']=len(eligible)
    return eligible,dict(qc)


def read_conds(path,member):
    included=set();qc=Counter()
    with ZipFile(path) as z,z.open(member) as stream:
        rd=csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig',newline=''))
        fields={'PLT_CN','CONDID','COND_STATUS_CD','STDORGCD','STDAGE','BALIVE'}
        if fields-set(rd.fieldnames or []):raise ValueError('FIA COND missing required prespecified source fields')
        for row in rd:
            qc['n_cond_rows']+=1
            key=(str(row.get('PLT_CN') or '').strip(),str(row.get('CONDID') or '').strip())
            if not key[0] or not key[1]:qc['invalid_condition_identity']+=1;continue
            if row.get('COND_STATUS_CD')!='1' or row.get('STDORGCD')!='0':continue
            qc['n_natural_forest_condition']+=1
            try:
                age=float(row['STDAGE']);ba=float(row['BALIVE'])
                if not 0<=age<=500 or not 0<=ba<=1500:raise ValueError()
            except (ValueError,TypeError):qc['age_or_basal_area_missing']+=1;continue
            included.add(key)
    qc['n_natural_forest_context_complete']=len(included)
    return included,dict(qc)


def source_tree_links(path,member,plot_exposures,cond_eligible):
    species=set(SPECIES); counters=Counter();per=defaultdict(Counter)
    with tempfile.TemporaryDirectory(prefix='fia_no_outcomes_') as tmp:
        db=sqlite3.connect(Path(tmp)/'ids.sqlite')
        try:
            db.execute('CREATE TABLE t (cn TEXT PRIMARY KEY, prev TEXT, sp TEXT, plt TEXT, cond TEXT, invyr INTEGER)')
            db.execute('CREATE INDEX t_prev ON t(prev)')
            with ZipFile(path) as z,z.open(member) as stream:
                rd=csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig',newline=''))
                required={'CN','PREV_TRE_CN','SPCD','PLT_CN','CONDID','INVYR'}
                if required-set(rd.fieldnames or []):raise ValueError("FIA TREE source IDs missing")
                # Deliberately never reference DIA or STATUSCD.
                batch=[]
                for row in rd:
                    counters['n_tree_rows_all_species']+=1
                    try:
                        sp=str(int(float(row['SPCD'])))
                        if sp not in species:continue
                        cn=str(row['CN'] or '').strip();plt=str(row['PLT_CN'] or '').strip();cond=str(row['CONDID'] or '').strip()
                        yr=int(row['INVYR'])
                        if not cn or not plt or not cond:raise ValueError()
                    except (ValueError,TypeError):counters['selected_invalid_identity']+=1;continue
                    batch.append((cn,str(row['PREV_TRE_CN'] or '').strip(),sp,plt,cond,yr))
                    if len(batch)>=6000:
                        db.executemany('INSERT INTO t VALUES (?,?,?,?,?,?)',batch)
                        counters['n_species_identity_rows']+=len(batch);batch=[]
                if batch:
                    db.executemany('INSERT INTO t VALUES (?,?,?,?,?,?)',batch)
                    counters['n_species_identity_rows']+=len(batch)
            db.commit()
            cursor=db.execute('''SELECT c.sp,p.plt,c.plt,p.cond,c.cond FROM t c JOIN t p ON c.prev=p.cn
                                 WHERE c.prev!='' AND c.sp=p.sp AND c.invyr>p.invyr''')
            counties=defaultdict(set);plotids=defaultdict(set)
            for sp,pplt,cplt,pc,cc in cursor:
                per[sp]['n_source_forward_same_species_links']+=1
                entry=plot_exposures.get(cplt)
                if entry is None or entry[0]!=pplt:continue
                per[sp]['n_plot_climate_eligible_links']+=1
                counties[sp].add(entry[1]);plotids[sp].add(cplt)
                if (pplt,pc) in cond_eligible and (cplt,cc) in cond_eligible:
                    per[sp]['n_natural_forest_with_age_and_density']+=1
            for sp in SPECIES:
                per[sp]['n_climate_counties']=len(counties[sp]);per[sp]['n_climate_plot_revisits']=len(plotids[sp])
                per[sp]['potential_for_development_model']=(per[sp]['n_natural_forest_with_age_and_density']>=MIN_LINKS_FOR_EXPLORATORY_MODEL and
                    len(counties[sp])>=MIN_COUNTIES_FOR_EXPLORATORY_MODEL and
                    len(plotids[sp])>=MIN_PLOTS_FOR_EXPLORATORY_MODEL)
        finally:db.close()
    return dict(counters),{s:dict(per[s]) for s in SPECIES}


def run(plot_manifest_file:Path,climate_csv:Path,climate_receipt_file:Path,output:Path,*,fetcher=None):
    original=json.loads(Path(plot_manifest_file).read_bytes())
    meta=json.loads(Path(climate_receipt_file).read_bytes())
    fingerprints=verify_inputs(original,meta,Path(climate_csv))
    climate=load_climate(climate_csv)
    states=[]
    for state in STATES:
        row={'state':state,'status':'source_unavailable','tree_biological_outcomes_opened':False}
        try:
            with tempfile.TemporaryDirectory(prefix='sdmr_fia_v3_'+state+'_') as t:
                folder=Path(t)
                p,ppath=fetch_zip(state,'PLOT',folder,fetcher=fetcher)
                row['plot_source']=p
                if p['status']!='ready' or p['sha256']!=fingerprints[state]:
                    raise ValueError(f'{state} pre-pinned new-PLOT bytes drift or unavailable')
                plots,pc=read_plots(ppath,p['member'],state,climate)
                row['plot_climate_eligibility']=pc
                # Verify PLOT pre-outcome donor denominator against its own archived receipt.
                declared=next(z for z in original['states'] if z['state']==state)
                if pc['n_eligible_plot_intervals']!=declared['climate_linkage']['n_county_climate_eligible_plot_links']:
                    raise ValueError('PLOT linked climate count changed despite SHA verification')
                co,co_path=fetch_zip(state,'COND',folder,fetcher=fetcher)
                row['cond_source']=co
                if co['status']!='ready':raise ValueError(f'{state} missing COND source')
                eligible,ctx=read_conds(co_path,co['member']);row['condition_eligibility']=ctx
                tr,tr_path=fetch_zip(state,'TREE',folder,fetcher=fetcher)
                row['tree_source']=tr
                if tr['status']!='ready':raise ValueError(f'{state} missing TREE source')
                ids,per=source_tree_links(tr_path,tr['member'],plots,eligible)
                row.update({'tree_identity_denominators':ids,'species_eligibility':per,'status':'source_identity_and_climate_ready'})
        except Exception as e:
            row['status']='source_unavailable_or_changed'
            row['source_error']=f'{type(e).__name__}: {str(e)[:300]}'
        states.append(row)
    result={'study':'fia_pre_response_county_climate_tree_source_gate_v3',
            'fixed_states':list(STATES),'fixed_species_codes':list(SPECIES),
            'no_diameter_or_survival_status_read':True,
            'NOAA_receipt_sha256':sha(climate_receipt_file),
            'NOAA_CSV_sha256':sha(climate_csv),
            'previous_PLOT_successor_sha256':sha(plot_manifest_file),
            'states':states,'n_eligible_source_states':sum(z['status']=='source_identity_and_climate_ready' for z in states),
            'claim_ceiling':'source, climate and source-condition geometry only; no growth and no climatic process or survival inference',
            'old_FIA_response_unchanged':True}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('SOURCE only:',[(s['state'],s['status'],s.get('plot_climate_eligibility',{}).get('n_eligible_plot_intervals'),
                           sum(v.get('n_natural_forest_with_age_and_density',0) for v in s.get('species_eligibility',{}).values())) for s in states],
          '3/3',result['n_eligible_source_states']==3)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plot-source',type=Path,default=Path('results/fia_noaa_county_climate_v1/plot_successor_v2_result.json'))
    p.add_argument('--noaa-csv',type=Path,default=Path('results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv'))
    p.add_argument('--noaa-receipt',type=Path,default=Path('results/fia_noaa_county_climate_v1/source_receipt.json'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.plot_source,args.noaa_csv,args.noaa_receipt,args.output)


if __name__=='__main__':main()
