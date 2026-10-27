"""Exploratory source-locked FIA growth vs county climate and stand basal area.

Prerequisites: new independent source gate v3 receipt, all 9 source ZIP SHA-256s
verified AGAIN, and full exact NOAA 20261006 43,890 county-month archive.
Not a test of physiological niche evolution or causal species processes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sqlite3
import tempfile
from zipfile import ZipFile

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('fia_climate_tree_source_gate_v3',HERE/'fia_climate_tree_source_gate_v3.py')
gate=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(gate)
STATES=gate.STATES;SPECIES=gate.SPECIES
MIN_SPECIES_OBSERVATIONS=500
MIN_SPECIES_COUNTIES=8
MIN_SPECIES_PLOTS=25
COUNTY_CV_FOLDS=5
PRIMARY_MODEL='common_temperature_precipitation_x_basal_area'


def contract(gate_manifest,noaa_receipt,climate_csv,plot_source):
    receipt=json.loads(Path(gate_manifest).read_bytes())
    if receipt.get('study')!='fia_pre_response_county_climate_tree_source_gate_v3':raise ValueError('Not source-only gate v3')
    if not receipt.get('no_diameter_or_survival_status_read') or receipt.get('n_eligible_source_states')!=3:
        raise ValueError('No full pre-response source identity gate')
    if receipt.get('fixed_states')!=list(STATES) or receipt.get('fixed_species_codes')!=list(SPECIES):
        raise ValueError('Source panel deviates from outcome-blind contract')
    for s in receipt['states']:
        if s.get('status')!='source_identity_and_climate_ready':raise ValueError('Source state is not complete')
        for tab in ('plot','cond','tree'):
            source=s.get(tab+'_source',{})
            if source.get('status')!='ready' or len(source.get('sha256',''))!=64:
                raise ValueError('Missing verified source for '+tab)
    if gate.sha(noaa_receipt)!=receipt['NOAA_receipt_sha256'] or gate.sha(climate_csv)!=receipt['NOAA_CSV_sha256']:
        raise ValueError('NOAA source changed')
    if gate.sha(plot_source)!=receipt['previous_PLOT_successor_sha256']:
        raise ValueError('PLOT successor changed')
    return receipt


def baseline_climate(climate:dict):
    baseline=defaultdict(list)
    for (fips,year,month), (t,p) in climate.items():
        if 1991<=year<=2020:
            baseline[fips].append((t,p))
    if len(baseline)!=209:raise ValueError('NOAA fixed 209-county baseline changed')
    result={}
    for county,values in baseline.items():
        if len(values)!=180:raise ValueError('NOAA county missing baseline month')
        result[county]=(sum(v[0] for v in values)/180,6*sum(v[1] for v in values)/180)
    return result


def valid_float(raw, *, low=-math.inf, high=math.inf):
    try:
        x=float(raw)
        return x if math.isfinite(x) and low<=x<=high else None
    except (ValueError,TypeError):return None


def read_plot_aux(zip_path,member,plot_eligibility):
    """Optional PLOT context is retained only for previously declared intervals."""
    needed={}
    with ZipFile(zip_path) as z,z.open(member) as raw:
        rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        for row in rd:
            cn=str(row['CN'] or '').strip()
            if cn in plot_eligibility:
                needed[cn]=((int(row['MEASYEAR']),int(row['MEASMON'])))
    if set(needed)!=set(plot_eligibility):raise ValueError('PLOT eligibility key changes on re-read')
    return needed


def read_conditions(zip_path,member):
    out={}
    with ZipFile(zip_path) as z,z.open(member) as raw:
        rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        required={'PLT_CN','CONDID','COND_STATUS_CD','STDORGCD','STDAGE','BALIVE'}
        if required-set(rd.fieldnames or []):raise ValueError('COND fields missing')
        for r in rd:
            key=(str(r.get('PLT_CN') or '').strip(),str(r.get('CONDID') or '').strip())
            if not all(key) or key in out:raise ValueError('COND identity invalid/duplicate')
            age=valid_float(r.get('STDAGE'),low=0,high=500)
            density=valid_float(r.get('BALIVE'),low=0,high=1500)
            origin=str(r.get('STDORGCD') or '').strip()
            forest=str(r.get('COND_STATUS_CD') or '').strip()=='1'
            out[key]={'natural_forest':forest and origin=='0','stand_age':age,'basal_area':density}
    return out


def tree_outcomes(zip_path,member,plots,plot_dates,condition_context,county_baseline,state):
    """After SHA-gate ONLY. Individual tree rows stay local; only aggregate leaves."""
    species=set(SPECIES);qc=Counter();records=[]
    with tempfile.TemporaryDirectory(prefix='fia_growth_records_') as d:
        con=sqlite3.connect(Path(d)/'selected.sqlite')
        try:
            con.execute('CREATE TABLE t(cn TEXT PRIMARY KEY, prev TEXT, species TEXT, plt TEXT, cond TEXT, invyr INTEGER, status TEXT, dia REAL, ht TEXT)')
            con.execute('CREATE INDEX ix_prev ON t(prev)')
            batch=[]
            with ZipFile(zip_path) as z,z.open(member) as raw:
                rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
                required={'CN','PREV_TRE_CN','SPCD','PLT_CN','CONDID','INVYR','STATUSCD','DIA'}
                if required-set(rd.fieldnames or []):raise ValueError('TREE changed status/diameter schema')
                for row in rd:
                    qc['n_source_tree_rows']+=1
                    try:
                        sp=str(int(float(row['SPCD'])))
                        if sp not in species:continue
                        identity=str(row['CN'] or '').strip()
                        plt=str(row['PLT_CN'] or '').strip()
                        cond=str(row['CONDID'] or '').strip()
                        year=int(row['INVYR'])
                        if not all((identity,plt,cond)):raise ValueError('blank identity')
                    except (ValueError,TypeError):qc['selected_invalid_tree_source_identity']+=1;continue
                    dia=valid_float(row.get('DIA'),low=0.00001,high=150)
                    batch.append((identity,str(row.get('PREV_TRE_CN') or '').strip(),sp,plt,cond,year,
                                  str(row.get('STATUSCD') or '').strip(),dia,str(row.get('DIAHTCD') or '').strip()))
                    if len(batch)>=5000:
                        con.executemany('INSERT INTO t VALUES (?,?,?,?,?,?,?,?,?)',batch)
                        qc['n_selected_tree_rows']+=len(batch);batch=[]
                if batch:
                    con.executemany('INSERT INTO t VALUES (?,?,?,?,?,?,?,?,?)',batch)
                    qc['n_selected_tree_rows']+=len(batch)
            con.commit()
            query='''SELECT c.species,p.plt,c.plt,p.cond,c.cond,p.invyr,c.invyr,p.status,c.status,p.dia,c.dia,p.ht,c.ht
                     FROM t c JOIN t p ON c.prev=p.cn WHERE c.prev!='' AND c.species=p.species AND c.invyr>p.invyr'''
            for sp,prev_plot,current_plot,prior_cond,current_cond,y0,y1,prev_status,current_status,d0,d1,h0,h1 in con.execute(query):
                qc['same_species_forward_links']+=1
                interval=plots.get(current_plot)
                if interval is None or interval[0]!=prev_plot:continue
                qc['linked_climate_plot']+=1
                before=condition_context.get((prev_plot,prior_cond));now=condition_context.get((current_plot,current_cond))
                if before is None or now is None or not before['natural_forest'] or not now['natural_forest']:
                    qc['not_both_natural_forest']+=1;continue
                age=before['stand_age'];density=before['basal_area']
                if age is None or density is None:
                    qc['missing_age_or_density']+=1;continue
                qc['natural_context_available']+=1
                if prev_status!='1':qc['prior_status_not_live']+=1;continue
                if current_status=='2':qc['linked_live_to_dead_observed']+=1;continue
                if current_status=='3':qc['removed_not_in_growth']+=1;continue
                if current_status!='1':qc['current_nonlive_unclassified']+=1;continue
                if d0 is None or d1 is None or d0<1:qc['missing_eligible_diameter']+=1;continue
                if not (h0 and h1 and h0==h1):qc['diameter_height_code_not_matched']+=1;continue
                exposure=interval[2];duration=exposure['calendar_interval_years']
                if not 1<=duration<=20:qc['duration_out_of_scope']+=1;continue
                baseline=county_baseline.get(interval[1])
                if baseline is None:qc['baseline_not_available']+=1;continue
                y=math.log(d1/d0)/duration
                if not math.isfinite(y):qc['nonfinite_response']+=1;continue
                month=plot_dates.get(current_plot)
                if not month:qc['missing_current_measure_date']+=1;continue
                qc['growth_pairs_admitted']+=1
                records.append((sp,state,current_plot,interval[1],(month[0]-2005)/20,
                                duration,math.log(d0/10),age/60,density/100,
                                (exposure['temperature_c']-baseline[0])/3,
                                (exposure['precipitation_mm_per_six_months']-baseline[1])/200,
                                y))
        finally:con.close()
    cols=['sp','state','plot','county','year_centered','interval','ln_dia10','age60','ba100','tanom3','panom200','growth']
    return pd.DataFrame.from_records(records,columns=cols),dict(qc)


def model_design(df,kind):
    """Predefined nested models. Site-environment interactions are *associations*."""
    if kind not in ('baseline','climate','shared_interaction','state_interaction'):
        raise ValueError('Unknown model')
    n=len(df)
    f=[np.ones(n)];names=['intercept']
    for state in ('VA','WI'):
        f.append((df.state.to_numpy()==state).astype(float));names.append('state_'+state)
    for var in ('year_centered','interval','ln_dia10','age60','ba100'):
        f.append(df[var].to_numpy(float));names.append(var)
    if kind in ('climate','shared_interaction','state_interaction'):
        for var in ('tanom3','panom200'):
            f.append(df[var].to_numpy(float));names.append(var)
    if kind in ('shared_interaction','state_interaction'):
        ba=df.ba100.to_numpy(float)
        for var in ('tanom3','panom200'):
            f.append(ba*df[var].to_numpy(float));names.append('ba_x_'+var)
    if kind=='state_interaction':
        ba=df.ba100.to_numpy(float)
        for state in ('VA','WI'):
            mask=(df.state.to_numpy()==state).astype(float)
            for var in ('tanom3','panom200'):
                f.append(mask*ba*df[var].to_numpy(float));names.append(state+'_ba_x_'+var)
    return np.column_stack(f),names


def assign_county_folds(df):
    """Outcome-blind stable county-block folds, no tree/plot leakage."""
    counties=df.county.astype(str).to_numpy()
    return np.array([int.from_bytes(hashlib.sha256(c.encode()).digest()[:4],'big')%COUNTY_CV_FOLDS for c in counties])


def species_fit(df):
    if (len(df)<MIN_SPECIES_OBSERVATIONS or df.county.nunique()<MIN_SPECIES_COUNTIES
            or df['plot'].nunique()<MIN_SPECIES_PLOTS or df.state.nunique()!=3):
        return {'status':'insufficient_source_support','n_growth_pairs':len(df),
                'n_counties':df.county.nunique(),'n_plots':df['plot'].nunique(),'n_states':df.state.nunique()}
    y=df.growth.to_numpy(float);folds=assign_county_folds(df)
    models=('baseline','climate','shared_interaction','state_interaction')
    predictions={name:np.full(len(df),np.nan) for name in models}
    scores={};coefs={}
    for name in models:
        x,cols=model_design(df,name)
        if np.linalg.matrix_rank(x)<x.shape[1]:
            scores[name]={'status':'rank_deficient','n_cols':x.shape[1]};continue
        good=True
        for fold in range(COUNTY_CV_FOLDS):
            train,test=folds!=fold,folds==fold
            if train.sum()<x.shape[1]+10 or test.sum()<1 or np.linalg.matrix_rank(x[train])<x.shape[1]:
                good=False;break
            fit=np.linalg.lstsq(x[train],y[train],rcond=None)[0]
            predictions[name][test]=x[test]@fit
        if not good:
            scores[name]={'status':'county_cv_fold_rank_or_support_failure'};continue
        e=y-predictions[name]
        scores[name]={'status':'cross_validated','rmse_log_dia_per_year':float(np.sqrt(np.mean(e**2))),
                      'mae_log_dia_per_year':float(np.mean(np.abs(e))),'n_folds':COUNTY_CV_FOLDS}
        beta=np.linalg.lstsq(x,y,rcond=None)[0]
        coefs[name]={k:float(v) for k,v in zip(cols,beta)}
    outcome={'status':'exploratory_county_heldout_association_only','n_growth_pairs':len(df),
             'n_plots':int(df['plot'].nunique()),'n_counties':int(df.county.nunique()),
             'n_states':int(df.state.nunique()),'species':str(df.sp.iloc[0]),'scores':scores,
             'coefficient_descriptions':coefs,'year_mean':float(df.year_centered.mean()),
             'relative_climate_support':{
               s:{'min_tanom3':float(g.tanom3.min()),'max_tanom3':float(g.tanom3.max()),
                  'min_panom200':float(g.panom200.min()),'max_panom200':float(g.panom200.max()),
                  'n_counties':int(g.county.nunique()),'n_links':len(g)}
               for s,g in df.groupby('state',sort=True)}}
    keys=['baseline','climate','shared_interaction','state_interaction']
    if all(scores.get(k,{}).get('status')=='cross_validated' for k in keys):
        b=scores['baseline']['rmse_log_dia_per_year']
        outcome['rmse_gains_over_baseline']={k:float(b-scores[k]['rmse_log_dia_per_year']) for k in keys[1:]}
        outcome['incremental_shared_interaction_gain']=float(scores['climate']['rmse_log_dia_per_year']-scores['shared_interaction']['rmse_log_dia_per_year'])
        outcome['incremental_region_interaction_gain']=float(scores['shared_interaction']['rmse_log_dia_per_year']-scores['state_interaction']['rmse_log_dia_per_year'])
    return outcome


def run(source_receipt,climate_csv,noaa_receipt,plot_source,output,*,fetcher=None):
    source=contract(source_receipt,noaa_receipt,climate_csv,plot_source)
    index=gate.load_climate(climate_csv);base=baseline_climate(index)
    results=[];species_frames=[]
    for state_row in source['states']:
        state=state_row['state'];notes={'state':state,'status':'unavailable','source_hashes_checked_again':{}}
        with tempfile.TemporaryDirectory(prefix='fia_climate_growth_'+state+'_') as tmp:
            folder=Path(tmp);files={}
            for table in ('PLOT','COND','TREE'):
                meta,zippath=gate.fetch_zip(state,table,folder,fetcher=fetcher)
                notes['source_hashes_checked_again'][table]={'status':meta['status'],'sha256':meta.get('sha256')}
                if meta['status']!='ready' or meta['sha256']!=state_row[table.lower()+'_source']['sha256']:
                    notes['status']='source_changed_or_unavailable';notes['reason']=table+' differs from source-only v3 freeze';break
                files[table]=(zippath,meta['member'])
            if notes['status']=='source_changed_or_unavailable':results.append(notes);continue
            plots,_=gate.read_plots(*files['PLOT'],state,index)
            dates=read_plot_aux(*files['PLOT'],plots)
            conditions=read_conditions(*files['COND'])
            df,qc=tree_outcomes(*files['TREE'],plots,dates,conditions,base,state)
            notes['qc']=qc;notes['status']='source_identical_growth_opened';notes['n_growth_pairs']=len(df)
            species_frames.append(df);results.append(notes)
    if any(x['status']!='source_identical_growth_opened' for x in results):
        panel=[];status='source_stop_no_partial_model'
    else:
        joint=pd.concat(species_frames,ignore_index=True)
        panel=[{'spcd':code,**species_fit(joint.loc[joint.sp==code].reset_index(drop=True))} for code in SPECIES]
        status='retrospective_exploratory_climate_density_candidate'
    out={'study':'fia_county_climate_density_growth_v1','data_status':status,'states':results,
         'source_receipt_sha256':gate.sha(source_receipt),'source_noaa_sha256':gate.sha(noaa_receipt),
         'species':panel,'fixed_species':list(SPECIES),'n_model_eligible_taxa':sum(x['status']=='exploratory_county_heldout_association_only' for x in panel),
         'no_causal_climate_competition_or_niche_evolution_claim':True,
         'limits':['County-level climate not plot climate; within-county spatial exposure unobserved',
          'Unweighted survivor-only, linked live-to-live diameter selection',
          'County-heldout RMSE across same geographic panel is not independent temporal validation',
          'No plot or county-cluster uncertainty; coefficients descriptive, not causal effect tests',
          'State effects and plant physiology not separately identified',
          'Source PLOT/TREE/COND data can drift; 3/3 SHA must match before outcome opening']}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
    print('Climate-by-density source status:',status,'eligible species',out['n_model_eligible_taxa'])
    for sp in panel:
        print(sp['spcd'],sp['status'],sp.get('rmse_gains_over_baseline'))
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--noaa-csv',type=Path,default=Path('results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv'))
    p.add_argument('--noaa-receipt',type=Path,default=Path('results/fia_noaa_county_climate_v1/source_receipt.json'))
    p.add_argument('--plot-successor',type=Path,default=Path('results/fia_noaa_county_climate_v1/plot_successor_v2_result.json'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    run(args.source,args.noaa_csv,args.noaa_receipt,args.plot_successor,args.output)


if __name__=='__main__':main()
