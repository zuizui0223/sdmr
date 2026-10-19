"""First explicitly exploratory demographic response in a fixed FIA source panel.

Accept only 13 species nominated from pre-response RI/VA/WI TREE identity links.
Reads two censuses of the *same linked tree* for diameter and observed status,
not occurrence intensities. Calculates raw repeat-observed survival/death counts
and live-to-live size/growth summaries. Does NOT infer climate processes, causal
fitness, demographic population estimates, habitat selection or niche evolution.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
from decimal import Decimal,InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
import importlib.util

def _import_child(path,alias):
 spec=importlib.util.spec_from_file_location(alias,HERE/path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

gate=_import_child('geographic_tree_demography_source_gate_v1.py','fia_initial_source')
ref=_import_child('geographic_tree_demography_fia_crosswalk_v1.py','fia_official_crosswalk')

DIA_BANDS=(0,5,10,20,float('inf'))
DIA_LABELS=('1-<5','5-<10','10-<20','20+')
MAX_INTERVAL=20


def validate_contract(contract:dict,successor:dict,crosswalk:dict)->dict:
    if contract.get('stage')!='exploratory_measured_response_not_confirmatory':
        raise ValueError('non-exploratory status not allowed')
    states=contract.get('states')
    if states!=list(gate.FIA_STATES):raise ValueError('source states not frozen RI/VA/WI')
    sources=successor.get('states') or []
    if [r['state'] for r in sources]!=states or any(s['status']!='ready' for s in sources):
        raise ValueError('three complete verified source archives required')
    expected={s['state']:s.get('sha256') for s in sources}
    if expected != contract['source_zip_sha256_by_state']:
        raise ValueError('frozen ZIP SHA/source mismatch')
    if contract.get('min_interval_years')!=1 or contract.get('max_interval_years')!=MAX_INTERVAL:
        raise ValueError('unfrozen measurement interval bounds')
    candidate=successor['eligible_species']['candidate_spcd']
    elig=sorted(ref.canonical_code(s['spcd']) for s in candidate if s['n_supported_states']==3)
    req=sorted(ref.canonical_code(x) for x in contract['nominated_species_codes'])
    if elig!=req or len(req)!=13:raise ValueError('frozen response species cohort is not source-derived')
    names={ref.canonical_code(s['source_spcd_normalized']):s['scientific_name']
           for s in crosswalk['candidate_crosswalk']['taxa']
           if s['status']=='official_reference_matched' and
           ref.canonical_code(s['source_spcd_normalized']) in req}
    if any(s not in names for s in req):raise ValueError('missing official taxon name crosswalk')
    return {"species_codes":req,"official_names":names,"sha_by_state":expected}


def numeric_code(raw,*,allow_empty=False):
    if raw in (None,''):
        if allow_empty:return ''
        raise ValueError('missing numeric code')
    try:d=Decimal(str(raw).strip())
    except InvalidOperation:raise ValueError('invalid numeric code') from None
    if not d.is_finite() or d!=d.to_integral_value():raise ValueError('nonintegral numeric code')
    return str(int(d))


def diameter(raw)->float|None:
    if raw in (None,''):return None
    try:value=float(raw)
    except (TypeError,ValueError):return None
    import math
    if not math.isfinite(value) or value<=0 or value>150:return None
    return value


def read_selected_tree_rows(zippath:Path,member:str,con:sqlite3.Connection,codes:set[str])->dict:
    con.execute('''CREATE TABLE t(cn TEXT PRIMARY KEY,prev TEXT,spcd TEXT,invyr INTEGER,
                   pltcn TEXT,sta TEXT,dia REAL,diaheight TEXT)''')
    con.execute('CREATE INDEX t_prev ON t(prev)')
    rawrows=0;invalid=Counter();selected=0;batch=[]
    with ZipFile(zippath) as z, z.open(member) as f:
        stream=io.TextIOWrapper(f,encoding='utf-8-sig',newline='',errors='strict')
        reader=csv.DictReader(stream)
        required={'CN','PREV_TRE_CN','SPCD','INVYR','PLT_CN','STATUSCD','DIA'}
        if not reader.fieldnames or required-set(reader.fieldnames):
            raise ValueError('missing required DIA/status link fields: '+str(sorted(required-set(reader.fieldnames or []))))
        has_diaht='DIAHTCD' in reader.fieldnames
        for row in reader:
            rawrows+=1
            try:code=numeric_code(row.get('SPCD'))
            except ValueError:invalid['unparseable_spcd']+=1;continue
            if code not in codes:continue
            try:
                cn=str(row.get('CN') or '').strip()
                prev=str(row.get('PREV_TRE_CN') or '').strip()
                invyr=int(numeric_code(row.get('INVYR')))
                plt=str(row.get('PLT_CN') or '').strip()
                if not cn or not plt:raise ValueError('missing CN/PLT')
                status=numeric_code(row.get('STATUSCD'),allow_empty=True)
            except ValueError:
                invalid['selected_bad_identity_or_status']+=1;continue
            batch.append((cn,prev,code,invyr,plt,status,diameter(row.get('DIA')),
                          str(row.get('DIAHTCD') or '').strip() if has_diaht else ''))
            if len(batch)>=5000:
                try:con.executemany('INSERT INTO t VALUES (?,?,?,?,?,?,?,?)',batch)
                except sqlite3.IntegrityError:raise ValueError('duplicate CN in selected species') from None
                selected+=len(batch);batch=[]
        if batch:
            try:con.executemany('INSERT INTO t VALUES (?,?,?,?,?,?,?,?)',batch)
            except sqlite3.IntegrityError:raise ValueError('duplicate CN in selected species') from None
            selected+=len(batch)
    con.commit()
    return {'n_source_rows':rawrows,'n_selected_identity_rows':selected,
            'qc_exclusions':dict(invalid),'diameter_height_field_present':has_diaht}


def diameter_band(d:float)->str|None:
    if d is None or d<1:return None
    for i in range(4):
        if DIA_BANDS[i]<=d<DIA_BANDS[i+1]:return DIA_LABELS[i]
    return None


def summarize_linked_states(con:sqlite3.Connection,names:dict[str,str],state:str)->dict:
    """One row per exact earlier-current TREE link, never infer missing=dead."""
    cur=con.execute('''SELECT c.spcd, p.sta, c.sta, p.dia, c.dia,
                  p.invyr, c.invyr, p.diaheight,c.diaheight
          FROM t c JOIN t p ON c.prev=p.cn
          WHERE c.spcd=p.spcd AND c.invyr>p.invyr
          ORDER BY c.spcd,c.cn''')
    counters=defaultdict(Counter)
    data=defaultdict(list)
    excluded=Counter()
    for sp,prior,now,d0,d1,y0,y1,ht0,ht1 in cur:
        key=sp;counters[key]['valid_forward_same_species_links']+=1
        dt=y1-y0
        if not 1<=dt<=MAX_INTERVAL:
            counters[key]['interval_out_of_scope']+=1;continue
        if prior!='1':
            counters[key]['prior_not_confirmed_live']+=1;continue
        counters[key]['prior_live_linked']+=1
        if now=='1':
            counters[key]['observed_live_to_live']+=1
            if d0 is None or d1 is None or d0<1:
                counters[key]['live_pair_missing_or_ineligible_diameter']+=1;continue
            import math
            annual_log_growth=(math.log(d1)-math.log(d0))/dt
            annual_abs_growth=(d1-d0)/dt
            if not math.isfinite(annual_log_growth):
                counters[key]['nonfinite_growth']+=1;continue
            matched_heights=bool(ht0 and ht1 and ht0==ht1)
            band=diameter_band(d0)
            if band is None:
                counters[key]['diameter_below_1inch']+=1;continue
            data[key].append({'band':band,'lograte':annual_log_growth,
                     'absrate':annual_abs_growth,'height_match':matched_heights,
                     'd0':d0,'interval':dt})
            counters[key]['growth_diameter_pairs']+=1
            if matched_heights:counters[key]['height_code_matched_growth_pairs']+=1
        elif now=='2':counters[key]['observed_live_to_dead']+=1
        elif now=='3':counters[key]['observed_removed_not_mortality']+=1
        elif now=='0':counters[key]['not_currently_tallied_not_mortality']+=1
        else:counters[key]['status_missing_or_other_not_mortality']+=1
    import statistics
    output=[]
    for sp in sorted(names,key=int):
        xs=data.get(sp,[]);cc=counters[sp]
        rates=[x['lograte'] for x in xs]
        per_bin={}
        for band in DIA_LABELS:
            b=[x['lograte'] for x in xs if x['band']==band]
            per_bin[band]={'n':len(b),'mean_annual_log_diameter_change':sum(b)/len(b) if b else None}
        output.append({'spcd':sp,'official_scientific_name':names[sp],
          'state':state,'n_valid_forward_links':int(cc['valid_forward_same_species_links']),
          'n_prior_live_linked':int(cc['prior_live_linked']),
          'n_observed_live_to_live':int(cc['observed_live_to_live']),
          'n_observed_live_to_dead':int(cc['observed_live_to_dead']),
          'n_removed_excluded':int(cc['observed_removed_not_mortality']),
          'n_not_tallied_excluded':int(cc['not_currently_tallied_not_mortality']),
          'n_other_unknown_status_excluded':int(cc['status_missing_or_other_not_mortality']),
          'n_growth_pairs_with_diameter':len(xs),
          'n_growth_pairs_matching_diameter_height_code':int(cc['height_code_matched_growth_pairs']),
          'median_annual_log_diameter_change':statistics.median(rates) if rates else None,
          'mean_annual_log_diameter_change':sum(rates)/len(rates) if rates else None,
          'median_initial_diameter_inch':statistics.median(x['d0'] for x in xs) if xs else None,
          'size_band_growth_log_means':per_bin,
          'mortality_fraction_among_live_to_live_or_dead_links':(
             cc['observed_live_to_dead']/(cc['observed_live_to_live']+cc['observed_live_to_dead'])
             if cc['observed_live_to_live']+cc['observed_live_to_dead'] else None),
          'all_status_counts':dict(cc)})
    return {'state':state,'taxa':output,'outcome_opened_for_exploratory_development_only':True}


def standardize_size_across_states(states:list[dict], codes:list[str],min_bin_n:int=30)->dict:
    """Exploratory within-species direct standardization over COMMON size bands.

    Shared band weights are proportional to pooled measured pairs. This is not
    probability-sampling-weighted forest demography or causal climate inference.
    """
    by_state={s['state']:{row['spcd']:row for row in s['taxa']} for s in states}
    out=[]
    for sp in codes:
        usable=[]
        for band in DIA_LABELS:
            bins=[by_state[s][sp]['size_band_growth_log_means'][band] for s in gate.FIA_STATES]
            if all(b['n']>=min_bin_n for b in bins):
                usable.append((band,sum(b['n'] for b in bins),[b['mean_annual_log_diameter_change'] for b in bins]))
        denom=sum(w for _,w,_ in usable)
        est={}
        for i,state in enumerate(gate.FIA_STATES):
            est[state]=sum(w*vals[i] for _,w,vals in usable)/denom if denom else None
        out.append({'spcd':sp,'n_shared_size_bands':len(usable),
                    'eligible_size_bands':[b for b,_,_ in usable],
                    'shared_size_weight_basis':'pooled observed matched-pair counts',
                    'observed_size_standardized_mean_log_diameter_change_by_state':est,
                    'size_standardization_diagnostic_only':True})
    return {'min_growth_pairs_per_band_per_state':min_bin_n,'taxa':out}


def run(conf:Path,source:Path,crosswalk:Path,output:Path)->dict:
    config=json.loads(conf.read_bytes());suc=json.loads(source.read_bytes());cw=json.loads(crosswalk.read_bytes())
    q=validate_contract(config,suc,cw)
    # WI 2026 DataMart ZIP was independently verified at 159.61 MB under the
    # source-only capacity successor; use a technical cap that admits all three
    # previously frozen archives, without changing any scientific cohort.
    gate.MAX_ARCHIVE_BYTES=310_000_000
    gate.MAX_UNCOMPRESSED_BYTES=3_500_000_000
    results=[]
    for state in gate.FIA_STATES:
        with tempfile.TemporaryDirectory(prefix=f'fia_{state}_growth_') as tmp:
            folder=Path(tmp)
            receipt=gate.fetch_zip(state,folder)
            if receipt['status']!='ready':
                raise RuntimeError(f'{state} SOURCE UNAVAILABLE: {receipt["status"]}')
            if receipt['sha256']!=q['sha_by_state'][state]:
                raise RuntimeError(f'{state} source ZIP bytes changed, outcomes not authorized')
            con=sqlite3.connect(folder/'selected.sqlite')
            try:
                with ZipFile(folder/f'{state}_TREE.zip') as z:
                    member=receipt['member']
                raw=read_selected_tree_rows(folder/f'{state}_TREE.zip',member,con,set(q['species_codes']))
                if raw['n_source_rows']!=next(s for s in suc['states'] if s['state']==state)['n_raw_rows']:
                    raise RuntimeError('source denominator drift')
                result=summarize_linked_states(con,q['official_names'],state)
                result['source_rows_qc']=raw
                results.append(result)
            finally:con.close()
    aggregate={'analysis':'fia_three_state_named_taxa_first_observed_demography_v1',
       'analysis_type':'post_source_exploratory_observed_demographic_association',
       'raw_study_response_frozen_before_download':True,
       'sources':{'response_contract_sha256':hashlib.sha256(conf.read_bytes()).hexdigest(),
                  'wi_successor_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                  'name_crosswalk_sha256':hashlib.sha256(crosswalk.read_bytes()).hexdigest(),
                  'original_source_zip_sha_by_state':q['sha_by_state']},
       'data_limits':['FIA publicly perturbed coordinates, no calibrated exact environmental exposure',
          'Only repeat-observed trees are included, plot design weights not applied',
          'Records sharing plots and trees are dependent; no interval-censored hazard model fitted',
          'Missing links are not deaths; code 3 removals and status 0 excluded',
          'Stem diameter measurement height comparability only partially checked',
          'No species-specific physiological/causal process inferred; no prospective external confirmation'],
       'state_summaries':results,
       'size_standardized':standardize_size_across_states(results,q['species_codes']),
       'n_predeclared_taxa':len(q['species_codes']),
       'no_claim_about_niche_evolution_or_constraint_switch':True}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(aggregate,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
    print('SOURCE VERIFIED - 3 states,',len(q['species_codes']),'species; measurement pairs',
          [(s['state'],sum(x['n_growth_pairs_with_diameter'] for x in s['taxa'])) for s in results])
    return aggregate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=Path('configs/geographic_tree_demography_first_response_v1.json'))
    p.add_argument('--source',type=Path,default=Path('evidence/geographic_tree_demography_source_gate_v1/fia_wi_size_cap_successor_v2.json'))
    p.add_argument('--crosswalk',type=Path,default=Path('evidence/geographic_tree_demography_source_gate_v1/fia_official_species_crosswalk.json'))
    p.add_argument('--output',type=Path,default=Path('artifacts/fia_3state_growth_first_response_v1.json'))
    a=p.parse_args();run(a.config,a.source,a.crosswalk,a.output)

if __name__=='__main__':main()
