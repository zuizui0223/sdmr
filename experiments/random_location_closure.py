#!/usr/bin/env python3
"""Random-location process closure challenge on frozen first10 model-pool data.

Exploratory counterfactual to the *same* three-fold spatial split design.
Nothing from held-out answer-check is read; v5 remains failed/closed.
"""
from __future__ import annotations
import argparse, importlib.util, sys, json, hashlib
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from split_contrast import split_by_frozen_location, read_frozen_location_indices, authorization_with_certificates

HERE=Path(__file__).resolve().parent
BASE=HERE if (HERE/'v5_reliable_closure_probe.py').exists() else HERE.parent/'sdmr_closure_probe'/'experiments'
sys.path.insert(0,str(BASE))
spec=importlib.util.spec_from_file_location('matchedspatial',BASE/'v5_reliable_closure_probe.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def run(input_zip:Path,feature_zip:Path,registry_path:Path,reference_spatial:Path,output:Path):
    frozen=mod.load_inputs(input_zip)
    locs=read_frozen_location_indices(feature_zip,frozen)
    if mod.git_hash(registry_path.read_bytes())!=mod.REG_SHA:raise ValueError('frozen registry modified')
    reg=pd.read_csv(registry_path)
    prior=json.loads(reference_spatial.read_text())
    assert prior['original_v5_promotion']=='failed_closed' and prior['sealed_answer_check_read'] is False
    assert prior['input_zip_sha256']==mod.INPUT_SHA
    assert [r['scientific_name'] for r in prior['rows']]==[r['scientific_name'] for r in frozen]
    report={'schema':'sdmr.v5.postterminal_random_location_closure.v1',
            'status':'development_only_no_ecological_truth_claim',
            'original_v5_promotion':'failed_closed','sealed_answer_check_read':False,
            'reference_taxa':50,'tested_taxa':10,'cells_per_arm':60,
            'splits':'3 KFold on sorted unique frozen location_id, seed=0; interpolation not transfer',
            'source_spatial_sha256':hashlib.sha256(reference_spatial.read_bytes()).hexdigest(),
            'input_zip_sha256':mod.INPUT_SHA,'feature_zip_sha256':hashlib.sha256(feature_zip.read_bytes()).hexdigest(),
            'registry_blob_sha':mod.REG_SHA,'state_classifier_blob_sha':mod.RULE_SHA,
            'outcome_rules':{'margin':.01,'adequacy_floor':-.75,'sem_multiplier':1.,'perm_n':999,'perm_alpha':.001,'perm_seed':0},
            'rows':[]}
    output.parent.mkdir(parents=True,exist_ok=True)
    for rec in frozen:
        tax=rec['scientific_name'];x,y,pred=rec['x'],rec['y'],rec['predictors'];ids=locs[tax]
        splits=split_by_frozen_location(ids,seed=0,n_splits=3)
        row={'selection_rank':rec['selection_rank'],'scientific_name':tax,'x_sha256':mod.hash_array(x),
             'n_unique_locations':len(np.unique(ids)),'learners':{},'consensus':{}}
        challenges={'full':([],pred)}
        for process in mod.PROCESSES:challenges[process]=mod.closure_columns(pred,reg,process)
        for arm in mod.ARMS:
            fits=[];scores={p:[] for p in challenges};certs={p:[] for p in challenges};oof=[]
            for fold,(tr,te) in enumerate(splits):
                assert set(ids[tr]).isdisjoint(set(ids[te]))
                for process,(exc,keep) in challenges.items():
                    selected=[pred.index(p) for p in keep]
                    probs,certificate=mod.fit_route(x[tr][:,selected],y[tr],x[te][:,selected],arm)
                    score=mod.balanced_score(y[te],probs)
                    scores[process].append(score)
                    certs[process].append(bool(certificate['passed']))
                    fits.append({'fold':fold,'challenge':process,
                                 'excluded_predictors':exc,'retained_predictors':keep,
                                 'score':score,'certificate':certificate})
                    if process=='full':oof.append((y[te],probs))
            auth=authorization_with_certificates(mod.authorize(oof),certs['full'])
            states=[]
            for process in mod.PROCESSES:
                s=mod.state_from_scores(scores['full'],scores[process],all(certs['full']+certs[process]),auth)
                s.update(process=process,closure_predictors=','.join(challenges[process][0]),
                         fold_deltas=(np.array(scores['full'])-np.array(scores[process])).tolist())
                states.append(s)
            states=mod.RULES.apply_identical_closure_abstention(pd.DataFrame(states)).to_dict(orient='records')
            row['learners'][arm]={'authorization':auth,'states':states,'fits':fits}
        for arm in mod.ARMS[:2]:
            a={s['process']:s['state'] for s in row['learners'][arm]['states']}
            b={s['process']:s['state'] for s in row['learners']['shallow3_hgb']['states']}
            row['consensus'][arm+'__vs_hgb']=[{'process':p,'linear_state':a[p],
                       'hgb_state':b[p],'state':mod.consensus(a[p],b[p])} for p in mod.PROCESSES]
        report['rows'].append(row)
        report['summary']=mod.summarize(report)
        output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(f"{rec['selection_rank']}/10 {tax} "+' '.join(
             f"{a}:authorized={row['learners'][a]['authorization']['authorized']},"
             f"sharp={sum(st['state'] in mod.SHARP for st in row['learners'][a]['states'])}"
             for a in mod.ARMS),flush=True)
    print(json.dumps(report['summary'],indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input-zip',type=Path,required=True)
    p.add_argument('--feature-zip',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True)
    p.add_argument('--prior-spatial-json',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.input_zip,a.feature_zip,a.registry,a.prior_spatial_json,a.output)
