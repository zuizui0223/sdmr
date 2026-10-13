#!/usr/bin/env python3
"""Prospective simulation-only effort/nonlinear capacity diagnostic, isolated from M5/v5.

Finite process decisions are WRITTEN AND HASHED before evaluating the
occurrence-distribution reference. Sampled ecological data and (optional)
survey effort are the only columns accessed by fitting functions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sdmr.process_id.known_truth.worlds import simulate_process_world
from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
from sdmr.process_id.known_truth.permutation_gate import evaluate_permutation_statistic
from sdmr.process_id.states import apply_identical_closure_abstention, classify_process_state
from sdmr.process_information_closure import process_information_closure
from matched_kt_split_v1 import sample_model_input, learner_predict, balanced_score
from matched_kt_core import make_case_splits
from nonlinear_effort_core_v2 import (known_effort_features, ecological_closure_index,
    predict_forest, consensus, safe_jsonable, SHARP)

LEARNERS=('standardized_isotropic_l2','shallow3_hgb','random_forest_leaf7')
SPLITS=('random_cell','spatial')
EFFORT_REGIMES=('unavailable','known_effort_upper_bound')
PAIRS={'baseline_pair':('shallow3_hgb','standardized_isotropic_l2'),
       'nonlinear_pair':('shallow3_hgb','random_forest_leaf7')}
PROCESSES=('thermal','water','seasonality','radiation_energy','soil_substrate','productivity')


def serialize(x):
    return json.dumps(safe_jsonable(x),indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n'


def validate_contract(c):
    if c.get('schema')!='sdmr.nonlinear_effort_known_truth.v2' or c.get('status')!='design_frozen_before_new_seed_opening':
        raise ValueError('unfrozen or altered scientific contract')
    if tuple(c['split_modes'])!=SPLITS or tuple(c['ecological_processes'])!=PROCESSES:
        raise ValueError('split/process registry changed')
    if tuple(c['learner_routes'])!=LEARNERS or tuple(c['effort_regimes'])!=EFFORT_REGIMES:
        raise ValueError('learner/effort registry changed')
    if (set(c['comparisons'])-set(PAIRS) not in (set(),{'consensus'}) or
        {k:tuple(c['comparisons'][k]) for k in PAIRS}!=PAIRS):
        raise ValueError('model pair policy changed')
    d=c['denominators'];s=c['seeds'];w=c['worlds']
    if len(set(s))!=len(s) or len(set(w))!=len(w) or len(s)*len(w)!=d['cases'] or len(PROCESSES)*d['cases']!=d['oracle_target_cells']:
        raise ValueError('frozen seed/world denominator mismatch')
    n_fits=d['cases']*len(SPLITS)*len(EFFORT_REGIMES)*len(LEARNERS)*7*3
    if d['finite_fit_records']!=n_fits:
        raise ValueError('frozen model fit denominator mismatch')
    return True


def predict(x_train,y_train,x_test,route):
    if route=='random_forest_leaf7':
        return predict_forest(x_train,y_train,x_test)
    if route in ('shallow3_hgb','standardized_isotropic_l2'):
        # Exact frozen baseline from PR #279, unchanged.
        return learner_predict(x_train,y_train,x_test,route)
    raise ValueError('unknown frozen learner')


def finite_results(world,c):
    x,y,cells,groups,predictors=sample_model_input(world)
    # The fit engine never receives true_suitability or generating-process labels.
    result={}
    for mode in SPLITS:
        folds=make_case_splits(cells,groups,y,split_mode=mode,n_splits=3)
        result[mode]={}
        for effort_mode in EFFORT_REGIMES:
            allow_effort=(effort_mode=='known_effort_upper_bound')
            augmented=known_effort_features(x,cells,world.environment,available=allow_effort)
            result[mode][effort_mode]={}
            challenges={'full':list(range(len(predictors)+(1 if allow_effort else 0)))}
            closures={}
            for process in PROCESSES:
                closed=process_information_closure(world.process_registry,process)
                closures[process]=closed
                challenges[process]=ecological_closure_index(predictors,closed,with_effort=allow_effort)
            for learner in LEARNERS:
                records={route:[] for route in challenges}
                full_oof=[]
                for fold,(train,test) in enumerate(folds):
                    for route,indices in challenges.items():
                        xp=augmented[train][:,indices]
                        xv=augmented[test][:,indices]
                        proba,certificate=predict(xp,y[train],xv,learner)
                        score=balanced_score(y[test],proba) if proba is not None else None
                        records[route].append({'fold':fold,'score':score,'certificate':certificate,
                            'n_features':len(indices),'n_train':len(train),'n_test':len(test)})
                        if route=='full' and proba is not None:
                            full_oof.extend({'fold':fold,'cell_id':int(cells[k]),'label':int(y[k]),
                                'probability':float(v)} for k,v in zip(test,proba,strict=True))
                all_full=all(row['certificate']['passed'] for row in records['full'])
                auth={'authorized':False,'reason':'numerically_unavailable',
                    'score':None,'gain':None,'p_value':None,'n_full_oof':len(full_oof),
                    'numerically_certified':all_full}
                if all_full:
                    if len(full_oof)!=len(y):raise ValueError('incomplete OOF predictions')
                    reference=pd.DataFrame(full_oof)
                    stat=evaluate_permutation_statistic(reference,n_permutations=999,permutation_seed=0)
                    score=float(stat['observed_mean_score']);gain=float(stat['mean_gain_over_null']);pv=float(stat['p_value'])
                    gate=c['full_system_gate']
                    auth.update(score=score,gain=gain,p_value=pv,
                       authorized=bool(score>=gate['adequacy_floor'] and gain>=gate['gain_over_uniform'] and pv<=gate['alpha']),
                       reason='passed_full_system_gate' if score>=gate['adequacy_floor'] and gain>=gate['gain_over_uniform'] and pv<=gate['alpha'] else 'insufficient_full_system_information')
                states=[]
                for process in PROCESSES:
                    full=records['full'];ko=records[process]
                    complete=all_full and all(row['certificate']['passed'] for row in ko)
                    if complete:
                        diffs=np.asarray([float(a['score'])-float(b['score']) for a,b in zip(full,ko,strict=True)])
                        mean=float(diffs.mean());sem=float(diffs.std(ddof=1)/math.sqrt(3))
                        knock_mean=float(np.mean([float(k['score']) for k in ko]))
                        one=pd.DataFrame([{'route':learner,'complete':True,
                            'full_adequate':bool(auth['score']>=c['full_system_gate']['adequacy_floor']),
                            'knockout_adequate':bool(knock_mean>=c['full_system_gate']['adequacy_floor']),
                            'delta_mean':mean,'delta_sem':sem}])
                        state=classify_process_state(one,margin=c['state_rule']['margin'],
                            adequacy_floor=c['full_system_gate']['adequacy_floor'],
                            sem_multiplier=c['state_rule']['sem_multiplier'])
                    else:
                        mean=sem=None;state='unresolved'
                    if not auth['authorized']:state='unavailable'
                    reason=('full_system_not_authorized' if not auth['authorized'] else
                            'numerical_knockout_incomplete' if not complete else 'interval_process_challenge')
                    states.append({'process':process,'state':state,'reason':reason,'complete':bool(complete),
                        'closure_predictors':','.join(closures[process]),
                        'delta_mean':mean,'delta_sem':sem})
                states=apply_identical_closure_abstention(pd.DataFrame(states)).to_dict(orient='records')
                result[mode][effort_mode][learner]={'authorization':auth,'states':states,
                    'fit_records':records,'full_oof':full_oof,
                    'effort_feature_supplied':allow_effort,'n_eco_predictors':len(predictors)}
    return result


def run_case(c, *, world_name:str, seed:int,output_dir:Path,prospective:bool):
    validate_contract(c)
    if world_name not in c['worlds']:raise ValueError('undeclared world')
    if prospective and seed not in c['seeds']:raise ValueError('undeclared prospective seed')
    if not prospective and seed in c['seeds']:raise ValueError('development case cannot use prospective seed')
    sampling=c['generator']
    world=simulate_process_world(world_name,seed=seed,n_cells=sampling['cells'],
        n_occurrences=sampling['occurrences'],n_background=sampling['background'])
    finite=finite_results(world,c)
    pair_states={};pair_auth={}
    for mode in SPLITS:
        pair_states[mode]={};pair_auth[mode]={}
        for effort in EFFORT_REGIMES:
            pair_states[mode][effort]={};pair_auth[mode][effort]={}
            for pair,(a,b) in PAIRS.items():
                ta={s['process']:s['state'] for s in finite[mode][effort][a]['states']}
                tb={s['process']:s['state'] for s in finite[mode][effort][b]['states']}
                pair_states[mode][effort][pair]={p:consensus(ta[p],tb[p]) for p in PROCESSES}
                pair_auth[mode][effort][pair]=bool(finite[mode][effort][a]['authorization']['authorized'] and finite[mode][effort][b]['authorization']['authorized'])
    output_dir.mkdir(parents=True,exist_ok=True)
    finite_receipt={'schema':'sdmr.nonlinear_effort_known_truth.pre_oracle_finite.v2',
        'status':'finite_sha256_frozen_before_oracle','seed':seed,'world':world_name,'prospective':bool(prospective),
        'oracle_reference_read':False,'ecological_generating_truth_read':False,
        'effort_status':'known effort is simulator privileged, not field-observed',
        'learners':finite,'consensus':pair_states,'authorizations':pair_auth}
    receipt_path=output_dir/'finite_before_oracle.json'
    receipt_path.write_text(serialize(finite_receipt),encoding='utf-8')
    receipt_sha=hashlib.sha256(receipt_path.read_bytes()).hexdigest()

    # Oracle is opened only AFTER the finite receipt is serialized and hashed.
    o=c['oracle']
    odo=evaluate_occurrence_oracle_states(world,n_splits=o['n_splits'],
        split_mode=o['split_mode'],margin=o['margin'],sem_multiplier=o['sem_multiplier'],
        adequacy_floor=o['adequacy_floor'],approximation_tolerance=o['approximation_tolerance'],
        max_iter=o['max_iter'],max_leaf_nodes=o['max_leaf_nodes'],
        min_samples_leaf=o['min_samples_leaf'],learning_rate=o['learning_rate'],
        l2_regularization=o['l2_regularization'])
    oracle={str(r['process']):str(r['state']) for _,r in odo.states.iterrows()}
    if set(oracle)!=set(PROCESSES):raise ValueError('reference process states incomplete')
    result={'schema':'sdmr.nonlinear_effort_known_truth.case.v2','status':'complete_finite_before_oracle',
        'world':world_name,'seed':seed,'prospective':bool(prospective),
        'finite_receipt_sha256':receipt_sha,'oracle':oracle,
        'reference_numerical_states':odo.states.to_dict(orient='records'),
        'reference_numerical_evidence':odo.evidence.to_dict(orient='records'),
        'generating_processes_METADATA_ONLY':list(world.generating_processes),
        'observation_refusal_METADATA_ONLY':list(world.observation_unresolved_processes),
        'consensus':pair_states,'authorizations':pair_auth,
        'real_v5_promotion':'failed_closed','original_M5_evidence_changed':False,
        'effort_sensitivity_is_not_same_representation_oracle_accuracy':True}
    (output_dir/'case.json').write_text(serialize(result),encoding='utf-8')
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--contract',type=Path,required=True)
    ap.add_argument('--world',required=True)
    ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--prospective',action='store_true')
    a=ap.parse_args();c=json.loads(a.contract.read_text())
    result=run_case(c,world_name=a.world,seed=a.seed,output_dir=a.output_dir,prospective=a.prospective)
    print(json.dumps({'world':a.world,'seed':a.seed,'prospective':a.prospective,
        'joint_authorizations':result['authorizations'],
        'reference_oracle_opened_after_finite_receipt':True,
        'finite_receipt_sha256':result['finite_receipt_sha256']},sort_keys=True))

if __name__=='__main__':main()
