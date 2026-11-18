"""Exploratory *new-source* FIA TREE × PLOT × COND demographic consistency study.

Never read or modify historical frozen FIA growth responses. For new source cohort,
match independently frozen PLOT/COND SHA then download current TREE once and record
its SHA. Report actual-year corrected observed survivor increments and composition.
Not design-based forest inference, causal climate inference or niche evolution.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import statistics
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zipfile import ZipFile
import importlib.util

HERE = Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('source',HERE/'fia_plot_condition_source_gate_v1.py')
source=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(source)
STATES=source.STATES
BANDS=(('1-<5',1.,5.),('5-<10',5.,10.),('10-<20',10.,20.),('20+',20.,150.01))
AGES=(('0-<40',0,40),('40-<80',40,80),('80+',80,501))


def _flt(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None


def _cn(x):return str(x or '').strip()


def _valid_date(year, month):
    y=source._year(year)
    try:m=int(str(month).strip())
    except (ValueError,TypeError):return None
    if y is None or not 1<=m<=12:return None
    return y+(m-0.5)/12.0


def _band(x, choices):
    if x is None:return None
    for name,lo,hi in choices:
        if lo<=x<hi:return name
    return None


def verify_contract(c, receipt, crosswalk):
    if c.get('study_id')!='fia_measurement_date_stand_context_v1' or c.get('source_lineage')!='independent_new_source_no_reuse_of_historical_tree':
        raise ValueError('not authorized independent source contract')
    if c.get('states')!=list(STATES) or [x['state'] for x in receipt['states']]!=list(STATES):
        raise ValueError('state panel mismatch')
    if receipt['n_states_complete']!=3 or any(x['status']!='source_linked_metadata_ready' for x in receipt['states']):
        raise ValueError('fixed PLOT/COND source incomplete')
    if len(c['species_codes'])!=13:
        raise ValueError('only predeclared original 13 species permitted')
    lookup={str(int(x['source_spcd_normalized'])):x['scientific_name'] for x in crosswalk['candidate_crosswalk']['taxa'] if x['status']=='official_reference_matched'}
    codes=[str(int(x)) for x in c['species_codes']]
    if len(set(codes))!=13 or any(x not in lookup for x in codes):raise ValueError('incomplete fixed names')
    if c.get('minimum_matched_pairs_per_common_stratum')!=10:raise ValueError('stratum threshold drift')
    if c.get('source_sha256')!=hashlib.sha256(json.dumps(receipt,indent=2,sort_keys=True).encode('utf-8')).hexdigest():
        # Source receipt is stored with indent=2 sort_keys=True and a terminal newline.
        raise ValueError('archived source receipt fingerprint mismatch')
    return codes,{x:lookup[x] for x in codes}


def fetch_tree(state,folder,fetcher=None):
    if state not in STATES:raise ValueError('state outside unchanged panel')
    url=source.BASE+state+'_TREE.zip'
    dst=folder/(state+'_TREE.zip')
    digest=hashlib.sha256()
    max_bytes=360_000_000
    try:
        src=(io.BytesIO(fetcher(state)) if fetcher else
             urlopen(Request(url,headers={'User-Agent':'sdmr-fia-joint-source-v1'}),timeout=90))
        with src,dst.open('wb') as out:
            n=0
            while True:
                b=src.read(1024*1024)
                if not b:break
                n+=len(b)
                if n>max_bytes:raise ValueError('tree_archive_over_fixed_technical_cap')
                out.write(b);digest.update(b)
        with ZipFile(dst) as archive:
            members=[m for m in archive.infolist() if m.filename.upper().endswith(state+'_TREE.CSV')]
            if len(members)!=1:raise ValueError('tree_table_missing_or_ambiguous')
            if members[0].file_size>3_800_000_000:raise ValueError('tree_uncompressed_over_cap')
        return {'status':'ready','sha256':digest.hexdigest(),'member':members[0].filename,'zip_bytes':n},dst
    except (OSError,HTTPError,URLError,TimeoutError,ValueError) as e:
        dst.unlink(missing_ok=True)
        return {'status':'unavailable','reason':type(e).__name__+': '+str(e)[:120]},dst


def parse_plot(path,member):
    plots={}
    with ZipFile(path) as z,z.open(member) as raw:
        rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        req={'CN','PREV_PLT_CN','MEASYEAR','MEASMON','INVYR'}
        if req-set(rd.fieldnames or []):raise ValueError('PLOT required fields missing')
        for r in rd:
            cn=_cn(r['CN'])
            if not cn or cn in plots:raise ValueError('missing/duplicate plot CN')
            plots[cn]={'previous':_cn(r['PREV_PLT_CN']),'measure':_valid_date(r['MEASYEAR'],r['MEASMON']),
                       'invyr':source._year(r['INVYR']),'plotstatus':_cn(r.get('PLOT_STATUS_CD'))}
    return plots


def parse_cond(path,member):
    conds={}
    with ZipFile(path) as z,z.open(member) as raw:
        rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        req={'PLT_CN','CONDID','STDAGE','STDORGCD','COND_STATUS_CD'}
        if req-set(rd.fieldnames or []):raise ValueError('COND required fields missing')
        for r in rd:
            key=(_cn(r['PLT_CN']),_cn(r['CONDID']))
            if not all(key) or key in conds:raise ValueError('duplicate/invalid condition')
            conds[key]={'age':source._age(r['STDAGE']),'origin':_cn(r['STDORGCD']),
                        'forest':_cn(r['COND_STATUS_CD'])=='1',
                        'disturbance':_cn(r.get('DSTRBCD1')),
                        'condition_prop':_flt(r.get('CONDPROP_UNADJ'))}
    return conds


def parse_selected_tree(path,member,db,codes):
    db.execute('CREATE TABLE tree(cn TEXT PRIMARY KEY,prev TEXT,spcd TEXT,plt TEXT,cond TEXT,invyr INTEGER,sta TEXT,dia REAL,diaht TEXT)')
    db.execute('CREATE INDEX tree_previous ON tree(prev)')
    n=0;kept=0;batch=[]
    with ZipFile(path) as z,z.open(member) as raw:
        rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        req={'CN','PREV_TRE_CN','SPCD','PLT_CN','CONDID','INVYR','STATUSCD','DIA'}
        if req-set(rd.fieldnames or []):raise ValueError('TREE required fields missing')
        for row in rd:
            n+=1
            try:spcd=str(int(float(str(row['SPCD']))))
            except (TypeError,ValueError):continue
            if spcd not in codes:continue
            cn=_cn(row['CN']);plt=_cn(row['PLT_CN']);cond=_cn(row['CONDID'])
            if not cn or not plt or not cond:continue
            yr=source._year(row['INVYR'])
            if yr is None:continue
            dia=_flt(row.get('DIA'))
            if dia is not None and not 0<dia<=150:dia=None
            batch.append((cn,_cn(row['PREV_TRE_CN']),spcd,plt,cond,yr,
                          _cn(row['STATUSCD']),dia,_cn(row.get('DIAHTCD'))))
            if len(batch)>=5000:
                db.executemany('INSERT INTO tree VALUES (?,?,?,?,?,?,?,?,?)',batch);kept+=len(batch);batch=[]
        if batch:db.executemany('INSERT INTO tree VALUES (?,?,?,?,?,?,?,?,?)',batch);kept+=len(batch)
    db.commit()
    return {'n_source_tree_records':n,'n_selected_source_tree_records':kept}


def summarize_pairs(db, plots, conds, species_codes):
    out=defaultdict(lambda: {'counters':Counter(),'rates':defaultdict(list)})
    query='''SELECT c.spcd,p.plt,c.plt,p.cond,c.cond,p.invyr,c.invyr,p.sta,c.sta,p.dia,c.dia,p.diaht,c.diaht
     FROM tree c JOIN tree p ON c.prev=p.cn
     WHERE c.prev!='' AND c.spcd=p.spcd AND c.invyr>p.invyr'''
    totals=Counter()
    for sp,pplt,cplt,pc,cc,y0,y1,sta0,sta1,d0,d1,h0,h1 in db.execute(query):
        out[sp]['counters']['forward_same_species_links']+=1
        totals['forward_links']+=1
        a=plots.get(pplt);b=plots.get(cplt)
        if a is None or b is None:
            out[sp]['counters']['no_plot_metadata']+=1;continue
        if b['previous']!=pplt:
            out[sp]['counters']['plot_chain_not_identical']+=1;continue
        out[sp]['counters']['exact_plot_chain']+=1
        if a['measure'] is None or b['measure'] is None:
            out[sp]['counters']['missing_measurement_date']+=1;continue
        interval=b['measure']-a['measure']
        if not 1<=interval<=20:
            out[sp]['counters']['measured_interval_out_of_scope']+=1;continue
        out[sp]['counters']['eligible_measurement_interval']+=1
        inventory_interval=y1-y0
        if abs(interval-inventory_interval)>0.01:
            out[sp]['counters']['inventory_vs_measurement_interval_different']+=1
        if sta0!='1':
            out[sp]['counters']['prior_not_live']+=1;continue
        out[sp]['counters']['prior_live_measurement_dates']+=1
        if sta1=='2':out[sp]['counters']['observed_dead']+=1;continue
        if sta1=='3':out[sp]['counters']['removed_not_dead']+=1;continue
        if sta1!='1':out[sp]['counters']['unknown_status_not_dead']+=1;continue
        out[sp]['counters']['live_live']+=1
        if d0 is None or d1 is None or d0<1:
            out[sp]['counters']['missing_diameter']+=1;continue
        band=_band(d0,BANDS)
        if band is None:continue
        rate=math.log(d1/d0)/interval
        oldrate=math.log(d1/d0)/inventory_interval
        if not math.isfinite(rate):continue
        priorcond=conds.get((pplt,pc));currentcond=conds.get((cplt,cc))
        out[sp]['counters']['valid_growth_measured_year']+=1
        out[sp]['rates']['all'].append((band,None,rate,oldrate))
        if h0 and h1 and h0==h1:
            out[sp]['counters']['height_comparable']+=1
        if priorcond is None or currentcond is None:
            out[sp]['counters']['missing_condition_join']+=1;continue
        if not (priorcond['forest'] and currentcond['forest']):
            out[sp]['counters']['not_forest_both_times']+=1;continue
        if priorcond['origin']!='0' or currentcond['origin']!='0':
            out[sp]['counters']['not_confirmed_natural_both']+=1;continue
        out[sp]['counters']['natural_forest_both']+=1
        ageband=_band(priorcond['age'],AGES)
        if ageband is None:
            out[sp]['counters']['missing_prior_stand_age']+=1;continue
        out[sp]['rates']['natural_age'].append((band,ageband,rate,oldrate))
        if h0 and h1 and h0==h1:out[sp]['counters']['natural_age_height_matched']+=1
    results=[]
    for code in species_codes:
        x=out[code];cc=x['counters'];arr=x['rates']['all'];age=x['rates']['natural_age']
        cells={}
        for (dname,*_) in BANDS:
            for aname,*_ in AGES:
                vals=[rec for rec in age if rec[0]==dname and rec[1]==aname]
                cells[dname+'|'+aname]={
                    'n':len(vals),
                    'mean_measyear_normalized':sum(t[2] for t in vals)/len(vals) if vals else None,
                    'mean_invyr_normalized_same_pairs':sum(t[3] for t in vals)/len(vals) if vals else None
                }
        results.append({'spcd':code,'counters':dict(cc),'n_growth_pairs':len(arr),
                        'mean_growth_measyear':sum(t[2] for t in arr)/len(arr) if arr else None,
                        'mean_growth_invyr_same_pairs':sum(t[3] for t in arr)/len(arr) if arr else None,
                        'n_natural_stand_age_pairs':len(age),'size_age_strata':cells})
    return {'species':results,'total_forward_link_rows':totals['forward_links']}


def cross_state_standardize(states,codes,min_n=10):
    lookup={s['state']:{r['spcd']:r for r in s['species']} for s in states}
    out=[]
    for sp in codes:
        cols=[]
        for d,*_ in BANDS:
            for a,*_ in AGES:
                k=d+'|'+a
                v=[lookup[st][sp]['size_age_strata'][k] for st in STATES]
                if all(x['n']>=min_n for x in v):
                    cols.append((k,sum(x['n'] for x in v),[x['mean_measyear_normalized'] for x in v],
                                 [x['mean_invyr_normalized_same_pairs'] for x in v]))
        denominator=sum(c[1] for c in cols)
        point={}
        for ix,st in enumerate(STATES):
            point[st]={
                'measyear':sum(w*vals[ix] for _,w,vals,_ in cols)/denominator if denominator else None,
                'invyr_same_pairs':sum(w*vals[ix] for _,w,_,vals in cols)/denominator if denominator else None,
            }
        out.append({'spcd':sp,'n_shared_size_age_strata':len(cols),'strata':[k for k,_,_,_ in cols],
                    'n_observed_pairs_in_common_strata':denominator,
                    'by_state':point})
    return out


def run(config_path,source_path,names_path,output_path,fetch_plotcond=None,fetch_trees=None):
    c=json.loads(Path(config_path).read_text())
    r=json.loads(Path(source_path).read_text())
    crosswalk=json.loads(Path(names_path).read_text())
    codes,names=verify_contract(c,r,crosswalk)
    states=[]
    for source_row in r['states']:
        state=source_row['state']
        with tempfile.TemporaryDirectory(prefix='fia_join_'+state+'_') as tmp:
            folder=Path(tmp)
            pa,pth=source._fetch(state,'PLOT',folder,fetcher=fetch_plotcond)
            ca,cth=source._fetch(state,'COND',folder,fetcher=fetch_plotcond)
            if pa['status']!='ready' or ca['status']!='ready':
                raise RuntimeError(state+' fresh PLOT or COND source unavailable')
            if pa['zip_sha256']!=source_row['plot']['zip_sha256'] or ca['zip_sha256']!=source_row['cond']['zip_sha256']:
                raise RuntimeError(state+' PLOT/COND source changed after new-source freeze')
            tmeta,tpath=fetch_tree(state,folder,fetcher=fetch_trees)
            if tmeta['status']!='ready':raise RuntimeError(state+' TREE source unavailable: '+str(tmeta))
            plots=parse_plot(pth,pa['csv_member'])
            conds=parse_cond(cth,ca['csv_member'])
            db=sqlite3.connect(folder/'trees.sqlite')
            try:
                counts=parse_selected_tree(tpath,tmeta['member'],db,set(codes))
                metrics=summarize_pairs(db,plots,conds,codes)
            finally:db.close()
            states.append({'state':state,'n_plots':len(plots),'n_conditions':len(conds),
                           'tree_new_source':tmeta,'source_row_counts':counts,**metrics})
    output={
        'study':'fia_new_source_measyear_stand_context_v1',
        'scope':'NEW source version, exploratory same 13 taxa and RI VA WI; original frozen FIA response unchanged',
        'names':names,
        'plot_cond_source_receipt_sha256':hashlib.sha256(Path(source_path).read_bytes()).hexdigest(),
        'tree_source_is_new_and_not_identical_to_historical_by_assumption':True,
        'states':states,
        'cross_state_size_stand_age_standardization':cross_state_standardize(states,codes,c['minimum_matched_pairs_per_common_stratum']),
        'not_equivalent_to_prior_308181_survivor_growth_pairs':True,
        'no_causal_climate_or_niche_evolution_claim':True,
        'no_design_weights_or_plot_cluster_intervals':True,
    }
    output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print('NEW cohort source-linked complete')
    for st in states:
        print(st['state'],'TREE rows',st['source_row_counts']['n_source_tree_records'],
              'growth pairs',sum(x['n_growth_pairs'] for x in st['species']),
              'natural stand age',sum(x['n_natural_stand_age_pairs'] for x in st['species']))
    print('COMMON SIZE AGE strata among 13 taxa',[(names[x['spcd']],x['n_shared_size_age_strata']) for x in output['cross_state_size_stand_age_standardization']])
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,default=Path('configs/fia_tree_plot_condition_join_v1.json'))
    p.add_argument('--source',type=Path,default=Path('evidence/fia_plot_condition_source_v1.json'))
    p.add_argument('--names',type=Path,default=Path('evidence/geographic_tree_demography_source_gate_v1/fia_official_species_crosswalk.json'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.config,a.source,a.names,a.output)

if __name__=='__main__':main()
