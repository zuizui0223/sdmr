#!/usr/bin/env python3
"""Post-terminal, model-pool-only spatial vs random-location eligibility diagnosis.

Fixed first-ten taxa. No refitting based on answer-check, no claim of biological
process truth, and no retrospective v5 promotion. Random-location means
interpolation rather than spatially separated transfer.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

FROZEN_ZIP_SHA = '7488bff59e4da00db8420afcdccbb1627f1b52455609483ab9413a0b1f166aa0'
INDEX_SHA = {
    'model_pool_feature_index_v5.csv':'fa33b8ccc6ded3f12ce34b58370c83b1d66857e795cebafa678789f7f317471b',
    'background_300km_feature_index_v5.csv':'6caba416d9aefc7345994eb97568b8f24d5565c7ad6fca906de58821e88049f0',
}


def split_by_frozen_location(location_ids: np.ndarray, *, seed: int = 0, n_splits: int = 3):
    loc=np.asarray(location_ids,dtype=np.int64)
    if loc.ndim!=1 or len(loc)==0:
        raise ValueError('nonempty one-dimensional location ids required')
    cells=np.sort(np.unique(loc))
    if len(cells)<n_splits:
        raise ValueError('insufficient unique locations')
    results=[]
    splitter=KFold(n_splits=n_splits,shuffle=True,random_state=seed)
    for tr_cells,te_cells in splitter.split(cells):
        train=np.flatnonzero(np.isin(loc,cells[tr_cells]))
        test=np.flatnonzero(np.isin(loc,cells[te_cells]))
        if len(train)==0 or len(test)==0 or set(loc[train])&set(loc[test]):
            raise AssertionError('location group leakage or empty fold')
        results.append((train,test))
    if not np.array_equal(np.sort(np.concatenate([te for _,te in results])),np.arange(len(loc))):
        raise AssertionError('not a partition of original records')
    return results


def contrast_eligibility(outcomes:dict, first:str, second:str)->dict:
    left,right=outcomes[first],outcomes[second]
    if set(left)!=set(right):raise ValueError('models must be tested on same fixed cohort')
    eligible={k for k in left if left[k] and right[k]}
    union={k for k in left if left[k] or right[k]}
    return {'both_authorized':len(eligible),'union_authorized':len(union),
        'conditional_comparison_evaluable':bool(eligible),
        'conditional_agreement':None} # no closure labels fitted by this screening


def authorization_with_certificates(outcome:dict,certificates:list[bool])->dict:
    if not certificates:raise ValueError('every fold needs numerical certificate')
    result=dict(outcome)
    result['authorized_before_numerical_check']=bool(result['authorized'])
    result['numerically_certified']=bool(all(certificates))
    result['failed_numeric_folds']=int(sum(not c for c in certificates))
    result['authorized']=bool(result['authorized'] and result['numerically_certified'])
    return result

def read_frozen_location_indices(feature_zip:Path, cohort_rows:list)->dict:
    if hashlib.sha256(feature_zip.read_bytes()).hexdigest()!=FROZEN_ZIP_SHA:
        raise ValueError('historical frozen feature artifact digest mismatch')
    with zipfile.ZipFile(feature_zip) as z:
        frames={}
        for name,sha in INDEX_SHA.items():
            data=z.read(name)
            if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('model-pool index hash mismatch')
            frames[name]=pd.read_csv(io.BytesIO(data))
    model=frames['model_pool_feature_index_v5.csv']
    bg=frames['background_300km_feature_index_v5.csv']
    aligned={}
    for r in cohort_rows:
        tax=r['scientific_name']
        occ=model.loc[(model.scientific_name==tax)&model.complete_case]
        bgidx=bg.loc[(bg.scientific_name==tax)&bg.complete_case & (bg.background_rank.mod(5)!=0)]
        ids=np.r_[occ.location_id.to_numpy(np.int64),bgidx.location_id.to_numpy(np.int64)]
        y=np.asarray(r['y'])
        if len(ids)!=len(y) or not np.array_equal(y,np.r_[np.ones(len(occ),dtype=int),np.zeros(len(bgidx),dtype=int)]):
            raise AssertionError('historical row order/class membership cannot be reconstructed')
        aligned[tax]=ids
    return aligned


def run(input_zip:Path,feature_zip:Path,prior_closure_json:Path,output:Path):
    root=Path(__file__).resolve().parent
    former=root if (root/'v5_reliable_closure_probe.py').exists() else root.parent/'sdmr_closure_probe'/'experiments'
    if not former.exists():raise FileNotFoundError('exact frozen closure implementation required')
    sys.path.insert(0,str(former))
    spec=importlib.util.spec_from_file_location('prior_closure',former/'v5_reliable_closure_probe.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    cohort=mod.load_inputs(input_zip)
    if len(cohort)!=10:raise ValueError('strict first10 cohort required')
    locs=read_frozen_location_indices(feature_zip,cohort)
    prior=json.loads(prior_closure_json.read_text())
    if prior['input_zip_sha256']!=mod.INPUT_SHA or prior['reference_taxa']!=50 or prior['tested_taxa']!=10:
        raise ValueError('prior spatial cohort does not match exact ten taxa')
    prev={r['scientific_name']:r for r in prior['rows']}
    records=[]
    for item in cohort:
        tax=item['scientific_name'];x,y=item['x'],item['y']; ids=locs[tax]
        random_folds=split_by_frozen_location(ids,seed=0,n_splits=3)
        row={'scientific_name':tax,'rank':item['selection_rank'],'n_records':len(ids),'n_unique_locations':len(np.unique(ids)),'learners':{}}
        for arm in mod.ARMS:
            observed=[];folds=[];certs=[]
            for tr,te in random_folds:
                p,certificate=mod.fit_route(x[tr],y[tr],x[te],arm)
                if set(np.unique(y[te]))!={0,1}:raise ValueError('test fold lacks both labels')
                certs.append(bool(certificate['passed']))
                observed.append((y[te],p))
                folds.append({'score':mod.balanced_score(y[te],p),'n_train':len(tr),'n_test':len(te),
                    'n_locations_train':len(np.unique(ids[tr])),'n_locations_test':len(np.unique(ids[te])),
                    'numeric_certificate_passed':bool(certificate['passed']),
                    'numeric_certificate_reason':certificate.get('reason','fixed_hgb_recipe')})
            auth=authorization_with_certificates(mod.authorize(observed),certs)
            archived=prev[tax]['learners'][arm]['authorization']
            row['learners'][arm]={'random_location':auth,'spatial':archived,'random_folds':folds,
                                'gain_random_minus_spatial':auth['score']-archived['score']}
        records.append(row)
        print(f"{len(records)}/10 {tax}: " + ' '.join(f"{a} R={row['learners'][a]['random_location']['authorized']} S={row['learners'][a]['spatial']['authorized']}" for a in mod.ARMS),flush=True)
    contrasts={}
    for key in ('spatial','random_location'):
        profiles={arm:{row['scientific_name']:row['learners'][arm][key]['authorized'] for row in records} for arm in mod.ARMS}
        contrasts[key]={'authorized_taxa':{a:sum(profiles[a].values()) for a in mod.ARMS},
                        'pair_overlap':{
                            f'{a}__vs_hgb':contrast_eligibility(profiles,a,'shallow3_hgb')
                            for a in mod.ARMS[:2]}}
    out={'schema':'sdmr.v5.postterminal_matched_split_eligibility.v1','status':'exploratory_not_frozen_v5_promotion',
         'selection':'exact first10 frozen ranks','original_v5_promotion':'failed_closed','sealed_answer_check_read':False,
         'metric':'balanced_presence_background_log_score','splits':{
            'spatial':'original frozen 3-fold spatial GroupKFold',
            'random_location':'3-fold KFold over sorted unique frozen location_id, shuffle seed 0; interpolation only'},
         'raw_input_sha256':mod.INPUT_SHA,'source_feature_zip_sha256':FROZEN_ZIP_SHA,
         'fixed_taxa':10,'fixed_process_cells_per_learner':60,
         'closure_state_computed_for_random_location':False,
         'records':records,'contrast':contrasts}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(contrasts,indent=2),flush=True)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input-zip',type=Path,required=True)
    p.add_argument('--feature-zip',type=Path,required=True)
    p.add_argument('--prior-spatial-json',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    run(a.input_zip,a.feature_zip,a.prior_spatial_json,a.output)
