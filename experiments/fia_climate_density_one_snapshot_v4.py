"""One-run source-frozen FIA TREE/PLOT/COND x NOAA climate exploratory growth.

Pre-registered fixed 13 species/3 states and a *first* source-only phase.
A second phase opens responses ONLY from the same, SHA-verified, already downloaded
ZIP byte sequences. Historical PR #284 results and original PLOT v2 are untouched.
Not confirmatory, design-unweighted, and not evidence of causal niche evolution.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

import pandas as pd

HERE=Path(__file__).resolve().parent

def _load(filename, alias):
    spec=importlib.util.spec_from_file_location(alias,HERE/filename)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

gate=_load('fia_climate_tree_source_gate_v3.py','fia_v3_source_only')
analysis=_load('fia_climate_density_growth_v1.py','fia_clim_growth_model')


def source_phase(climate:dict,outdir:Path,*,fetcher=None):
    """Never touches TREE DIA/STATUSCD; named source and opportunity only."""
    outdir=Path(outdir);outdir.mkdir(exist_ok=True,parents=True)
    records=[];paths={};live_resources=[]
    for state in gate.STATES:
        row={'state':state,'status':'unavailable','tree_growth_outcome_opened':False}
        statepaths={};paths[state]=statepaths
        try:
            for table in ('PLOT','COND','TREE'):
                src,filepath=gate.fetch_zip(state,table,outdir,fetcher=fetcher)
                row[table.lower()+'_source']=src
                if src['status']!='ready':
                    raise ValueError(f'{state} {table} unavailable: {src.get("error")}')
                statepaths[table]=(filepath,src['member'])
            plots,pcounts=gate.read_plots(*statepaths['PLOT'],state,climate)
            row['plot_climate']=pcounts
            contexts,ccounts=gate.read_conds(*statepaths['COND'])
            row['condition_source']=ccounts
            ids,per=gate.source_tree_links(*statepaths['TREE'],plots,contexts)
            row['tree_source_counts']=ids;row['species_eligibility']=per
            row['status']='source_ready'
        except Exception as e:
            row['status']='source_stop';row['error']=f'{type(e).__name__}: {str(e)[:350]}'
        records.append(row)
    out={'study':'fia_climate_density_same_run_snapshot_v4','source_phase_before_biological_opening':True,
         'fixed_species_codes':list(gate.SPECIES),'fixed_states':list(gate.STATES),
         'original_SDmr_FIA_results_untouched':True,
         'n_source_ready':sum(x['status']=='source_ready' for x in records),
         'states':records,'source_only_no_status_or_diameter_opened':True}
    p=outdir/'source_phase_receipt.json'
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return out,paths


def analyze_frozen_source(source:dict,paths:dict,climate:dict,outdir:Path):
    """Open outcomes from precisely those same local ZIP bytes, never another GET."""
    if source['n_source_ready']!=3:
        return {'status':'source_stop_no_biological_outcome_opened','states':source['states'],
                'n_fitted_species':0,'fixed_species_codes':list(gate.SPECIES),
                'no_climate_or_competition_causal_claim':True}
    county_baseline=analysis.baseline_climate(climate)
    frames=[];state_reports=[]
    for s in source['states']:
        state=s['state'];copies=paths[state]
        for table in ('PLOT','COND','TREE'):
            filepath,_=copies[table]
            if gate.sha(filepath)!=s[table.lower()+'_source']['sha256']:
                raise RuntimeError('Local acquired '+table+' source drift before tree outcome opening')
        plots,pc=gate.read_plots(*copies['PLOT'],state,climate)
        if pc!=s['plot_climate']:raise ValueError('PLOT eligible counts drift before outcome')
        dates=analysis.read_plot_aux(*copies['PLOT'],plots)
        ctx=analysis.read_conditions(*copies['COND'])
        df,qc=analysis.tree_outcomes(*copies['TREE'],plots,dates,ctx,county_baseline,state)
        frames.append(df)
        state_reports.append({'state':state,'tree_outcome_qc':qc,'n_selected_growth_pairs':len(df)})
    joined=pd.concat(frames,ignore_index=True)
    population=[]
    for code in gate.SPECIES:
        selected=joined.loc[joined.sp==code].reset_index(drop=True)
        population.append({'spcd':code,**analysis.species_fit(selected)})
    return {'status':'retrospective_exploratory_same_run_snapshot_biological_outcome_opened',
            'n_selected_live_to_live_growth_pairs':len(joined),'n_fitted_species':sum(x['status']=='exploratory_county_heldout_association_only' for x in population),
            'source_phase_sha256':gate.sha(outdir/'source_phase_receipt.json'),
            'states':state_reports,'species':population,
            'fixed_species_codes':list(gate.SPECIES),
            'models':['baseline','climate','shared_interaction','state_interaction'],
            'inference_ceiling':'county-block cross-validation of same-source survivor growth association only; not causal or niche evolution',
            'site_location_scale':'NOAA public county climate, not plot-level drought',
            'excluded_before_causal_inference':['mortality and selective tree observation','plot design weights','plot-cluster sampling errors','genetic differences',
                                               'nonrandom forestry practices','unmeasured soil and annual intra-season weather'],
            'no_climate_or_competition_causal_claim':True}


def run(outdir:Path,noaa_csv:Path,noaa_receipt:Path):
    outdir=Path(outdir);outdir.mkdir(exist_ok=True,parents=True)
    climate_src=json.loads(Path(noaa_receipt).read_bytes())
    if (climate_src.get('study')!='fia_noaa_county_climate_pre_response_v1' or
        climate_src.get('climate_csv_sha256')!=gate.sha(noaa_csv) or
        climate_src.get('climate_csv_rows')!=43890):
        raise ValueError('Independent NOAA climate source changed')
    climate=gate.load_climate(noaa_csv)
    # Same directory persists across both phases. No up-to-date ZIP source
    # may replace a different historical ZIP after the opening gate.
    with tempfile.TemporaryDirectory(prefix='fia_complete_cohort_same_run_v4_') as temp:
        source,paths=source_phase(climate,Path(temp))
        receipt=outdir/'source_phase_receipt.json'
        receipt.write_text((Path(temp)/'source_phase_receipt.json').read_text(),encoding='utf-8')
        # Keep source result separate from outcome; reestablish source file hash
        # for the *copied* receipt used as linkage identity.
        value=analyze_frozen_source(source,paths,climate,Path(temp))
        value['NOAA_snapshot']=climate_src['snapshot']
        value['NOAA_county_csv_sha256']=gate.sha(noaa_csv)
        value['source_receipt_in_artifact']='source_phase_receipt.json'
        value['source_phase_sha256']=gate.sha(receipt)
        (outdir/'exploratory_climate_density_growth_v4.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print('ONE SHOT SOURCE',source['n_source_ready'],'/3',[(z['state'],z['status']) for z in source['states']])
        print('RESPONSE',value['status'],'tree_paired',value.get('n_selected_live_to_live_growth_pairs'),
              'fitted_species',value.get('n_fitted_species'))
        return value


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--noaa-csv',type=Path,default=Path('results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv'))
    p.add_argument('--noaa-receipt',type=Path,default=Path('results/fia_noaa_county_climate_v1/source_receipt.json'))
    p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();run(a.output_dir,a.noaa_csv,a.noaa_receipt)


if __name__=='__main__':main()
