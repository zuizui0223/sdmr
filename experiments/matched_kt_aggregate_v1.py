#!/usr/bin/env python3
"""Independent declared-denominator aggregation of once-opened known-truth cases.

Does not fit models, tune rules, read predictor matrices, or reseed generators.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from matched_kt_core import aggregate_cases, STATES, SHARP


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summarize(input_root:Path,contract:dict,output:Path):
    paths=sorted(input_root.rglob('case.json'))
    cases=[]
    sources=[]
    for case_path in paths:
        result=_read(case_path)
        receipt_path=case_path.parent/'finite_frozen_before_oracle.json'
        raw=receipt_path.read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        if actual!=result.get('finite_receipt_sha256'):
            raise ValueError(f'pre-oracle finite-state receipt digest mismatch: {case_path}')
        finite=json.loads(raw)
        if finite.get('status')!='finite_frozen_before_reference_opening' or finite.get('reference_truth_read_by_learner') is not False:
            raise ValueError('truth information barrier violated')
        if finite.get('prospective') is not True:
            raise ValueError('finite receipt prospective flag mismatch: burned or unsealed fit cannot be promoted')
        if (finite.get('seed'),finite.get('world'))!=(result['seed'],result['world']):
            raise ValueError('finite and oracle case identity mismatch')
        if result.get('prospective') is not True or result.get('original_v5_promotion')!='failed_closed':
            raise ValueError('case not prospective or v5 boundary changed')
        if result.get('M5_original_evidence_changed') is not False:
            raise ValueError('M5 evidence mutation prohibited')
        if set(finite['finite'])!=set(contract['finite']['split_modes']):
            raise ValueError('wrong number of split modes')
        for mode in contract['finite']['split_modes']:
            if set(finite['finite'][mode])!=set(contract['finite']['learners']):
                raise ValueError('wrong number of learners')
            for learner in contract['finite']['learners']:
                case=finite['finite'][mode][learner]
                if len(case['states'])!=6 or case['all_fold_records']!=21:
                    raise ValueError('missing process or fold evidence')
        sources.append({'seed':result['seed'],'world':result['world'],
                        'finite_receipt_sha256':actual,
                        'case_sha256':hashlib.sha256(case_path.read_bytes()).hexdigest()})
        cases.append(result)
    summary=aggregate_cases(cases,contract)
    fit_count=len(cases)*2*2*7*3
    if fit_count!=contract['denominators']['finite_fits']:
        raise ValueError('fixed whole-process fit denominator wrong')
    per_learner={mode:{learner:sum(bool(case['per_learner_authorization'][mode][learner]) for case in cases)
                      for learner in contract['finite']['learners']}
                 for mode in contract['finite']['split_modes']}
    by_world={}
    for world in contract['worlds']:
        matched=[case for case in cases if case['world']==world]
        by_world[world]={mode:{
              'joint_authorized':sum(case['authorization'][mode] for case in matched),
              'sharp':sum(state in SHARP for case in matched for state in case['consensus'][mode].values()),
              'n_cases':len(matched),
              'n_process_cells':len(matched)*6,
            } for mode in contract['finite']['split_modes']}
    report={
        'schema':'sdmr.matched_known_truth_split.aggregate.v1',
        'status':'complete_scientific_outcome_not_promotion',
        'scientific_claim_boundary':'finite 24-case conditional reference benchmark; not real-v5 rescue, not causal process identification',
        'original_v5_promotion':'failed_closed',
        'truth_estimand':'occurrence-distribution oracle approximation, not generating-driver membership',
        'source_receipts':sources,
        'declared_fit_count':fit_count,
        'summary':summary,'per_learner_authorized':per_learner,'by_world':by_world,
        'no_favorable_seed_selection':True,'no_threshold_changes':True,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'summary':summary,'per_learner_authorized':per_learner},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input-root',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    summarize(a.input_root,_read(a.config),a.output)
