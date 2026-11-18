"""Audit coverage of original FIA PLOT intervals by independently pinned NOAA county climate.

This is a metadata-only source join. Does not open any individual TREE row, survival
outcome, FIA forest-condition outcome or growth. Can only use original SHA-256
PLOT archives and the separately frozen NOAA source; it fails closed on drift.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
from collections import Counter
from pathlib import Path
import tempfile
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
mod_spec=importlib.util.spec_from_file_location('county',HERE/'fia_noaa_county_climate_source_v1.py')
county=importlib.util.module_from_spec(mod_spec)
mod_spec.loader.exec_module(county)
plot_spec=importlib.util.spec_from_file_location('plot_gate',HERE/'fia_plot_condition_source_gate_v1.py')
plot_gate=importlib.util.module_from_spec(plot_spec)
plot_spec.loader.exec_module(plot_gate)

STATES=('RI','VA','WI')
FIPS={'RI':'44','VA':'51','WI':'55'}


def parse_plots(zippath:Path,member:str,state:str):
    prefix=FIPS[state]
    out={}; reject=Counter(); n_rows=0
    with ZipFile(zippath) as z,z.open(member) as raw:
        reader=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        keys={'CN','PREV_PLT_CN','STATECD','COUNTYCD','MEASYEAR','MEASMON'}
        if keys-set(reader.fieldnames or []):
            raise ValueError('missing required FIA county/year plot fields')
        for row in reader:
            n_rows+=1
            cn=str(row.get('CN') or '').strip()
            if not cn or cn in out:raise ValueError('duplicate/missing FIA plot identity')
            try:
                st=str(int(float(str(row['STATECD']))))
                co=int(float(str(row['COUNTYCD'])))
                year=int(str(row['MEASYEAR']))
                month=int(str(row['MEASMON']))
                if st!=str(int(prefix)) or not 1<=co<=999 or not 1850<=year<=2030 or not 1<=month<=12:
                    raise ValueError('invalid state county or measure date')
                fips=prefix+f'{co:03d}'
                when=(year,month)
            except (ValueError,TypeError):
                reject['invalid_state_county_or_date']+=1
                fips,when=None,None
            out[cn]=(str(row.get('PREV_PLT_CN') or '').strip(),fips,when)
    return out,{'n_plot_rows':n_rows,'n_invalid_county_or_date':reject['invalid_state_county_or_date']}


def load_climate(csv_path:Path,receipt_path:Path):
    receipt=json.loads(receipt_path.read_bytes())
    data=csv_path.read_bytes()
    if receipt.get('study')!='fia_noaa_county_climate_pre_response_v1' or not receipt.get('no_tree_or_growth_data_opened'):
        raise ValueError('wrong NOAA source contract')
    if receipt.get('climate_csv_sha256')!=hashlib.sha256(data).hexdigest():
        raise ValueError('NOAA climate archive checksum changed')
    records={}
    reader=csv.DictReader(io.StringIO(data.decode('utf-8')))
    if set(reader.fieldnames or [])!=set(county.COLUMNS):raise ValueError('NOAA climate data schema changed')
    for r in reader:
        key=(r['fips_county'],int(r['year']),int(r['month']))
        if key in records:raise ValueError('duplicate NOAA county month')
        records[key]=(float(r['temperature_c']),float(r['precipitation_mm']))
    if len(records)!=receipt['climate_csv_rows']:raise ValueError('NOAA climate denominator changed')
    return records,receipt


def interval_climate(index:dict,fips:str,start:tuple[int,int],end:tuple[int,int]):
    if not fips or not start or not end:return None
    a,b=12*start[0]+start[1],12*end[0]+end[1]
    if b<=a or b-a > 12*21:return None
    values=[]
    for y in range(start[0],end[0]+1):
        for m in (4,5,6,7,8,9):
            z=12*y+m
            if a<z<b:
                val=index.get((fips,y,m))
                if val is None:return None
                values.append(val)
    if len(values)<6:return None
    return len(values),sum(x[0] for x in values)/len(values),sum(x[1] for x in values)*6/len(values)


def summarize_plot_chain(plots:dict,index:dict,state:str):
    c=Counter();tmp=[]
    for cn,(prev,fips,date) in plots.items():
        if not prev:continue
        c['n_with_previous_plot_key']+=1
        old=plots.get(prev)
        if old is None:
            c['prior_plot_not_in_source']+=1
            continue
        if fips is None or date is None or old[1] is None or old[2] is None:
            c['plot_county_or_date_invalid']+=1
            continue
        if old[1]!=fips:
            c['county_changed_between_censuses']+=1
            continue
        r=interval_climate(index,fips,old[2],date)
        if r is None:
            c['climate_not_complete_in_two_census_interval']+=1
            continue
        c['n_exact_county_interval_climate_complete']+=1
        tmp.append(r[0])
    return {'state':state,'n_plot_entries':len(plots),
            'n_previous_plot_records':c['n_with_previous_plot_key'],
            'n_county_climate_eligible_plot_links':c['n_exact_county_interval_climate_complete'],
            'n_distinct_plot_exposure_rows_not_trees':len(tmp),
            'minimum_apr_sep_months':min(tmp) if tmp else None,
            'median_apr_sep_months':sorted(tmp)[len(tmp)//2] if tmp else None,
            'exclusions':dict(c),
            'no_tree_growth_or_forest_dynamics_evaluated':True}


def run(plot_receipt_file,climate_csv,climate_receipt,outpath,*,getter=None):
    src=json.loads(Path(plot_receipt_file).read_bytes())
    if src.get('n_states_complete')!=3 or [x['state'] for x in src['states']]!=list(STATES):
        raise ValueError('frozen FIA PLOT state cohort incomplete')
    idx,nmeta=load_climate(Path(climate_csv),Path(climate_receipt))
    all_states=[]
    for item in src['states']:
        st=item['state'];expected=item['plot']['zip_sha256']
        with tempfile.TemporaryDirectory(prefix='fia_noaa_plot_source_') as tmp:
            folder=Path(tmp)
            meta,path=plot_gate._fetch(st,'PLOT',folder,fetcher=getter)
            if meta['status']!='ready' or meta['zip_sha256']!=expected:
                all_states.append({'state':st,'status':'source_unavailable_or_changed',
                                   'no_outcomes_accessed':True,
                                   'actual_sha256':meta.get('zip_sha256'),'source_expected_sha256':expected})
                continue
            plots,info=parse_plots(path,meta['csv_member'],st)
            audit=summarize_plot_chain(plots,idx,st)
            all_states.append({'state':st,'status':'plot_climate_pre_response_join_ready',
                               'source_expected_sha256':expected,
                               'plot_source':info,'join':audit})
    result={'study':'fia_noaa_county_plot_chain_coverage_v1',
            'original_noaa_climate_source_sha256':hashlib.sha256(Path(climate_receipt).read_bytes()).hexdigest(),
            'original_fia_plot_source_sha256':hashlib.sha256(Path(plot_receipt_file).read_bytes()).hexdigest(),
            'states':all_states,'n_states_join_complete':sum(x['status']=='plot_climate_pre_response_join_ready' for x in all_states),
            'n_tree_growth_observations_opened':0,
            'no_climate_density_effect_or_causal_inference':True}
    p=Path(outpath);p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('PLOT NOAA SOURCE ONLY',[(r['state'],r['status'],r.get('join',{}).get('n_county_climate_eligible_plot_links')) for r in all_states])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fia-plot',type=Path,default=Path('evidence/fia_plot_condition_source_v1.json'))
    p.add_argument('--climate-csv',type=Path,required=True)
    p.add_argument('--climate-receipt',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    run(args.fia_plot,args.climate_csv,args.climate_receipt,args.output)

if __name__=='__main__':main()
