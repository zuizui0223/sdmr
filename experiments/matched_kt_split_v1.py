#!/usr/bin/env python3
"""One-case worker for frozen matched split-mode / known-truth benchmark.

Finite evidence is serialized and hashed BEFORE the independent occurrence-
distribution oracle is evaluated. No world truth surface, sampling effort,
generating-process declaration, or ODO state is supplied to learner fitting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from sdmr.process_id.hgb_profiles import get_hgb_profile
from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS, simulate_process_world
from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
from sdmr.process_id.known_truth.permutation_gate import evaluate_permutation_statistic
from sdmr.process_id.states import classify_process_state, apply_identical_closure_abstention
from sdmr.process_information_closure import process_information_closure

from matched_kt_core import make_case_splits, consensus_state, SHARP

PROCESSES=('thermal','water','seasonality','radiation_energy','soil_substrate','productivity')
LEARNERS=('standardized_isotropic_l2','shallow3_hgb')
SPLITS=('random_cell','spatial')


def file_digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialize(payload)->str:
    return json.dumps(payload,indent=2,sort_keys=True,allow_nan=False,ensure_ascii=False)+'\n'


def sample_model_input(world):
    """No truth/suitability columns are ever returned to the learning code."""
    positive=world.occurrences.copy()
    negative=world.background.copy()
    positive['label']=1
    negative['label']=0
    sample=pd.concat([positive,negative],ignore_index=True,sort=False)
    ids=sample['cell_id'].astype(int).to_numpy()
    if len(np.unique(ids))!=len(ids):
        raise ValueError('sampled known-truth world duplicated cell IDs')
    id2group=dict(zip(world.environment['cell_id'].astype(int),np.asarray(world.spatial_groups),strict=True))
    groups=np.asarray([id2group[int(i)] for i in ids],dtype=int)
    predictors=tuple(world.predictor_universe)
    x=sample.loc[:,list(predictors)].to_numpy(float)
    y=sample['label'].to_numpy(int)
    if not np.isfinite(x).all() or set(np.unique(y))!={0,1}:
        raise ValueError('non-finite features or missing labels')
    return x,y,ids,groups,predictors


def balanced_score(labels,probabilities)->float:
    y=np.asarray(labels,dtype=int)
    p=np.asarray(probabilities,dtype=float)
    if set(np.unique(y))!={0,1} or not np.isfinite(p).all() or (p<0).any() or (p>1).any():
        raise ValueError('invalid two-class probability score input')
    p=np.clip(p,1e-9,1-1e-9)
    return float(.5*(np.mean(np.log(p[y==1]))+np.mean(np.log1p(-p[y==0]))))


def learner_predict(x_train,y_train,x_test,learner):
    """Fit exactly one declared recipe, report failed numerics as unavailable."""
    y=np.asarray(y_train,dtype=int)
    if set(np.unique(y))!={0,1}:
        return None,{'passed':False,'reason':'training_single_class'}
    try:
        if learner=='standardized_isotropic_l2':
            model=make_pipeline(StandardScaler(),LogisticRegression(
                C=1.0,penalty='l2',solver='newton-cholesky',max_iter=100,
                tol=1e-10,class_weight='balanced',random_state=0))
            with warnings.catch_warnings(record=True) as logged:
                warnings.simplefilter('always',ConvergenceWarning)
                model.fit(x_train,y)
            n_iter=int(model.named_steps['logisticregression'].n_iter_[0])
            warned=any(issubclass(e.category,ConvergenceWarning) for e in logged)
            if warned or n_iter>=100:
                return None,{'passed':False,'reason':'nonconverged_newton_cholesky','iterations':n_iter,'convergence_warning':warned}
        elif learner=='shallow3_hgb':
            n=len(y);n_pos=int(y.sum());n_neg=n-n_pos
            weights=np.where(y==1,n/(2*n_pos),n/(2*n_neg))
            model=HistGradientBoostingClassifier(
                loss='log_loss',random_state=0,**get_hgb_profile('shallow3'))
            model.fit(x_train,y,sample_weight=weights)
            n_iter=int(model.n_iter_)
        else:
            raise ValueError('undeclared learner')
        p=np.asarray(model.predict_proba(x_test)[:,1],dtype=float)
        if not np.isfinite(p).all() or np.any((p<0)|(p>1)):
            return None,{'passed':False,'reason':'nonfinite_probabilities'}
        return p,{'passed':True,'iterations':n_iter,'reason':'finite_converged_fit'}
    except (ValueError,RuntimeError,np.linalg.LinAlgError,FloatingPointError) as e:
        return None,{'passed':False,'reason':f'numeric_fit_error_{type(e).__name__}'}


def finite_for_split(world,split_mode:str,learner:str,config:dict)->dict:
    x,y,ids,spatial_groups,predictors=sample_model_input(world)
    folds=make_case_splits(ids,spatial_groups,y,split_mode=split_mode,n_splits=3)
    registry=world.process_registry
    closures={process:process_information_closure(registry,process) for process in PROCESSES}
    # All registered representations of a process are removed together.
    challenges={'full':tuple(predictors)}
    for process,closure in closures.items():
        subset=tuple(p for p in predictors if p not in set(closure))
        if not subset:
            raise ValueError('process closure removes entire declared predictor system')
        challenges[process]=subset
    results={route:[] for route in challenges}
    full_oof=[]
    for fold,(tr,te) in enumerate(folds):
        for route,keep in challenges.items():
            indices=[predictors.index(p) for p in keep]
            pred,cert=learner_predict(x[tr][:,indices],y[tr],x[te][:,indices],learner)
            score=balanced_score(y[te],pred) if pred is not None else None
            results[route].append({'fold':fold,'score':score,'certificate':cert,
                                   'n_train':len(tr),'n_test':len(te),'n_features':len(keep)})
            if route=='full' and pred is not None:
                full_oof.append(pd.DataFrame({'fold':int(fold),'label':y[te],
                                              'probability':pred,'cell_id':ids[te]}))
    all_full=all(v['certificate']['passed'] for v in results['full'])
    authorized=False;score=None;gain=None;pvalue=None;reason='numerical_full_unavailable'
    if all_full:
        observed=pd.concat(full_oof,ignore_index=True)
        stat=evaluate_permutation_statistic(observed,n_permutations=999,permutation_seed=0)
        score=float(stat['observed_mean_score']);gain=float(stat['mean_gain_over_null']);pvalue=float(stat['p_value'])
        authorized=bool(score>=-.75 and gain>=.01 and pvalue<=.001)
        reason='authorized' if authorized else 'full_system_adequacy_failed'
    states=[]
    for process in PROCESSES:
        full=results['full'];ko=results[process]
        complete=bool(all_full and all(row['certificate']['passed'] for row in ko))
        if complete:
            vals=np.asarray([float(a['score'])-float(b['score']) for a,b in zip(full,ko,strict=True)])
            mean=float(vals.mean());sem=float(vals.std(ddof=1)/math.sqrt(3))
            reduced_mean=float(np.mean([float(v['score']) for v in ko]))
            evidence=pd.DataFrame([{'route':learner,'complete':True,
                'full_adequate':bool(score>=-.75),
                'knockout_adequate':bool(reduced_mean>=-.75),
                'delta_mean':mean,'delta_sem':sem}])
            classification=classify_process_state(evidence,margin=.01,adequacy_floor=-.75,sem_multiplier=1.)
        else:
            mean=sem=None;classification='unresolved'
        if not authorized:
            classification='unavailable'
        states.append({'process':process,'state':classification,
                       'reason':('full_system_not_authorized' if not authorized else
                                 'incomplete_knockout_fit' if not complete else 'interval_process_challenge'),
                       'closure_predictors':','.join(closures[process]),
                       'delta_mean':mean,'delta_sem':sem,'complete':complete})
    states=apply_identical_closure_abstention(pd.DataFrame(states)).to_dict(orient='records')
    return {'authorization':{'authorized':authorized,'score':score,'gain':gain,
                             'p_value':pvalue,'reason':reason,'numerically_certified':all_full},
            'states':states,'fits':results,
            'all_fold_records':sum(len(v) for v in results.values()),
            'unique_sampled_cells':len(np.unique(ids))}


def evaluate_case(config:dict,*,world_name:str,seed:int,output_dir:Path,prospective:bool):
    if config.get('schema')!='sdmr.matched_known_truth_split.v1' or config.get('status')!='preregistered_before_any_new_seed_outcome':
        raise ValueError('wrong / opened scientific contract')
    if world_name not in config['worlds'] or world_name not in KNOWN_TRUTH_WORLDS:
        raise ValueError('world not predeclared')
    if prospective and seed not in config['seeds']:
        raise ValueError('undeclared prospective seed')
    if not prospective and seed in config['seeds']:
        raise ValueError('development fixture must not use prospective seed')
    s=config['sampling']
    world=simulate_process_world(world_name,seed=seed,n_cells=s['n_cells'],
       n_occurrences=s['n_occurrences'],n_background=s['n_background'])
    finite={}
    for mode in config['finite']['split_modes']:
        finite[mode]={}
        for learner in config['finite']['learners']:
            finite[mode][learner]=finite_for_split(world,mode,learner,config)
    def combine(mode):
        a={r['process']:r['state'] for r in finite[mode]['standardized_isotropic_l2']['states']}
        b={r['process']:r['state'] for r in finite[mode]['shallow3_hgb']['states']}
        return {p:consensus_state(a[p],b[p]) for p in PROCESSES}
    preoracle={
       'schema':'sdmr.matched_known_truth_split.finite_receipt.v1',
       'status':'finite_frozen_before_reference_opening',
       'world':world_name,'seed':seed,'prospective':bool(prospective),
       'finite':finite,'consensus':{mode:combine(mode) for mode in config['finite']['split_modes']},
       'reference_truth_read_by_learner':False,
    }
    output_dir.mkdir(parents=True,exist_ok=True)
    frozen_path=output_dir/'finite_frozen_before_oracle.json'
    frozen_path.write_text(serialize(preoracle),encoding='utf-8')
    finite_digest=file_digest(frozen_path)

    # Only AFTER finite decisions have a persisted hash is truth-side evidence opened.
    o=config['oracle']
    oracle=evaluate_occurrence_oracle_states(world,
       n_splits=o['n_splits'],margin=o['margin'],sem_multiplier=o['sem_multiplier'],
       adequacy_floor=o['adequacy_floor'],approximation_tolerance=o['approximation_tolerance'],
       max_iter=o['fit_max_iter'],max_leaf_nodes=o['max_leaf_nodes'],
       min_samples_leaf=o['min_samples_leaf'],learning_rate=o['learning_rate'],
       l2_regularization=o['l2_regularization'],split_mode=o['split_mode'])
    oracle_states={str(r['process']):str(r['state']) for _,r in oracle.states.iterrows()}
    if set(oracle_states)!=set(PROCESSES):
        raise ValueError('missing ODO oracle processes')
    case={'schema':'sdmr.matched_known_truth_split.case.v1',
        'status':'completed_all_declared_states',
        'seed':seed,'world':world_name,'prospective':bool(prospective),
        'finite_receipt_sha256':finite_digest,
        'oracle':oracle_states,'generating_processes_metadata_only':list(world.generating_processes),
        'consensus':preoracle['consensus'],
        'authorization':{mode:bool(all(finite[mode][learner]['authorization']['authorized'] for learner in LEARNERS)) for mode in SPLITS},
        'per_learner_authorization':{mode:{learn:bool(finite[mode][learn]['authorization']['authorized']) for learn in LEARNERS} for mode in SPLITS},
        'per_learner_states':{mode:{learn:{r['process']:r['state'] for r in finite[mode][learn]['states']} for learn in LEARNERS} for mode in SPLITS},
        'oracle_split_independent_of_finite':'random on all 1600 population cells; ODO is distribution-conditional approximation',
        'original_v5_promotion':'failed_closed',
        'M5_original_evidence_changed':False,
    }
    case_path=output_dir/'case.json'
    case_path.write_text(serialize(case),encoding='utf-8')
    return case


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',type=Path,required=True)
    ap.add_argument('--world',required=True)
    ap.add_argument('--seed',required=True,type=int)
    ap.add_argument('--output-dir',required=True,type=Path)
    ap.add_argument('--prospective',action='store_true')
    a=ap.parse_args()
    c=json.loads(a.config.read_text())
    result=evaluate_case(c,world_name=a.world,seed=a.seed,output_dir=a.output_dir,
                        prospective=a.prospective)
    print(json.dumps({'world':result['world'],'seed':result['seed'],
        'joint_authorized':result['authorization'],
        'sharp':{m:sum(s in SHARP for s in result['consensus'][m].values()) for m in SPLITS},
        'oracle_states':result['oracle']},ensure_ascii=False,sort_keys=True),flush=True)

if __name__=='__main__':main()
