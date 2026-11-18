"""Post-source, post-outcome effort sensitivity: source-model dependence only.

Recompute one frozen rectangular Quercus dataset with two *assumed* recording
intensity offsets: uniform q=1 versus raw counts of three independent plant
sentinel taxa. NEITHER is calibrated true effort. This does not identify
causal limiting variables or constitute prospective macroecology evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

REGIONS=("quercus_DE_central","quercus_SE_south")


def run(frame: pd.DataFrame, *, input_sha256: str, replicates: int = 99, seed: int = 20261019) -> dict:
    if not set(REGIONS).issubset(frame.region.unique()) or len(frame[frame.region.isin(REGIONS)].region.unique()) != 2:
        raise ValueError('Both fixed Quercus windows required')
    source=frame.loc[frame.region.isin(REGIONS)].copy()
    if source.duplicated(['region','cell_id']).any():
        raise ValueError('Duplicate cell')
    if source[['n_focal_records_diagnostic','n_independent_target_group_records_diagnostic']].isna().any().any():
        raise ValueError('Focal or sentinel source incomplete')
    if not (source.n_independent_target_group_records_diagnostic > 0).all():
        raise ValueError('Unobserved sentinel cells: no pseudocount imputation permitted')
    source['n_occ']=source.n_focal_records_diagnostic.astype(int)
    source['taxon']='Quercus robur'
    p=Path(__file__).with_name('geographic_driver_turnover_v0.py')
    spec=importlib.util.spec_from_file_location('real_window_v0',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    variants={}
    fields=['taxon','region','cell_id','spatial_block','temperature','moisture','effort','n_occ']
    for method in ('uniform_unit_offset','three_sentinel_raw_count_offset'):
        trial=source.copy()
        trial['effort']=(1.0 if method=='uniform_unit_offset' else
                         trial.n_independent_target_group_records_diagnostic.astype(float))
        variants[method]=m.analyze_taxon(trial[fields],seed=seed,replicates=replicates)
    u=variants['uniform_unit_offset'];s=variants['three_sentinel_raw_count_offset']
    sign_changes=[]
    for region in REGIONS:
        cu=u['regions'][region]['thermal_minus_moisture']
        cs=s['regions'][region]['thermal_minus_moisture']
        if cu*cs < 0:
            sign_changes.append(region)
    return {
        'type':'postsource_assumption_sensitivity_not_biological_diagnostic',
        'source_cells_sha256':input_sha256,
        'source_windows':REGIONS,
        'n_source_cells':int(len(source)),
        'full_source_presence_counts':{r:int(source.loc[source.region==r,'n_occ'].sum()) for r in REGIONS},
        'environmental_process_inference_authorized':False,
        'sensitivity_arms':variants,
        'sign_changed_under_assumed_effort_regions':sign_changes,
        'n_sign_changed_regions':len(sign_changes),
        'biological_claim_ceiling':('Model-based predictor information contrasts can depend on '
            'assumed effort offsets; neither arm estimates true detection or causal limiting factors.'),
        'cautions':['post-source exploratory','not pre-registered for scientific inference',
           'equal-area rectangles are not accessible M','native-country not native individual',
           'effort assumptions are neither calibrated nor independently validated',
           'small uneven numbers of spatial blocks','plug-in bootstrap not type-I-error calibrated'],
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cells',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seed',type=int,default=20261019)
    ap.add_argument('--replicates',type=int,default=99)
    a=ap.parse_args()
    raw=a.cells.read_bytes()
    result=run(pd.read_csv(a.cells),input_sha256=hashlib.sha256(raw).hexdigest(),
               replicates=a.replicates,seed=a.seed)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print('sign changes', result['n_sign_changed_regions'], 'of',len(REGIONS))
    for name,arm in result['sensitivity_arms'].items():
        print(name, {r:round(d['thermal_minus_moisture'],3) for r,d in arm['regions'].items()},
              'uncalibrated tail=',arm['one_sided_bootstrap_p'])

if __name__=='__main__':main()
