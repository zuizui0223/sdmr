#!/usr/bin/env python3
"""No-refit audit of frozen nonlinear/effort known-truth case receipts.

All cases, all 7-route fold-score records and complete primary denominators are
required. Recompute saved OOF probability permutation p-values independently;
oracle numerical regression is not re-fitted here.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from nonlinear_effort_core_v2 import consensus, summarize_cases, SHARP, POSITIVE


def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def verify_receipt_hash(path:Path,expected:str):
    if digest(path.read_bytes())!=expected:
        raise ValueError('pre-oracle receipt hash mismatch')
    return True


def verify_pair_consensus(finite,case,pairs,processes):
    for mode in case['consensus']:
        for effort in case['consensus'][mode]:
            for name,(a,b) in pairs.items():
                states_a={s['process']:s['state'] for s in finite[mode][effort][a]['states']}
                states_b={s['process']:s['state'] for s in finite[mode][effort][b]['states']}
                if set(states_a)!=set(processes) or set(states_b)!=set(processes):
                    raise ValueError('missing model process state')
                expected={p:consensus(states_a[p],states_b[p]) for p in processes}
                if case['consensus'][mode][effort][name]!=expected:
                    raise ValueError('case consensus differs from pre-oracle learners')
                authorized=(finite[mode][effort][a]['authorization']['authorized']
                            and finite[mode][effort][b]['authorization']['authorized'])
                if bool(case['authorizations'][mode][effort][name])!=bool(authorized):
                    raise ValueError('case authorization differs from pre-oracle learners')


def balanced_score(y,p):
    y=np.asarray(y,dtype=int)
    p=np.asarray(p,dtype=float)
    if len(y)!=len(p) or set(np.unique(y))!={0,1} or not np.isfinite(p).all() or (p<0).any() or (p>1).any():
        raise ValueError('invalid OOF score')
    p=np.clip(p,1e-9,1-1e-9)
    return float(.5*(np.mean(np.log(p[y==1]))+np.mean(np.log1p(-p[y==0]))))


def rerun_frozen_permutation(oof,n_permutations=999,seed=0):
    groups={}
    for row in oof:
        groups.setdefault(int(row['fold']),[[],[]])
        groups[int(row['fold'])][0].append(int(row['label']))
        groups[int(row['fold'])][1].append(float(row['probability']))
    folds=[(np.asarray(groups[i][0],int),np.asarray(groups[i][1],float)) for i in sorted(groups)]
    if len(folds)!=3:raise ValueError('OOF missing a declared fold')
    observed=float(np.mean([balanced_score(y,p) for y,p in folds]))
    rng=np.random.default_rng(seed)
    exceed=0
    for _ in range(n_permutations):
        null=float(np.mean([balanced_score(rng.permutation(y),p) for y,p in folds]))
        exceed+=int(null>=observed)
    return {'score':observed,'p_value':(1+exceed)/(n_permutations+1)}


def verify_case(finite,case,c,*,source_dir):
    if finite['status']!='finite_sha256_frozen_before_oracle' or finite['oracle_reference_read'] is not False or finite['ecological_generating_truth_read'] is not False:
        raise ValueError('finite output not frozen before reference')
    if case['status']!='complete_finite_before_oracle' or case['real_v5_promotion']!='failed_closed' or case['original_M5_evidence_changed'] is not False:
        raise ValueError('original M5/v5 barrier violated')
    if (case['seed'],case['world'])!=(finite['seed'],finite['world']):
        raise ValueError('case and frozen finite world/seed mismatch')
    if case['consensus']!=finite['consensus'] or case['authorizations']!=finite['authorizations']:
        raise ValueError('post-oracle finite state tampering')
    if {s['process']:s['state'] for s in case['reference_numerical_states']}!=case['oracle']:
        raise ValueError('oracle reference labels do not match numerical oracle table')
    verify_pair_consensus(finite['learners'],case,c['comparisons'],c['ecological_processes'])
    total=0;full_checks=0;incomplete=[]
    for mode in c['split_modes']:
        for effort in c['effort_regimes']:
            for learner in c['learner_routes']:
                route=finite['learners'][mode][effort][learner]
                if set(route['fit_records'])!=set(c['ecological_processes'])|{'full'}:
                    raise ValueError('missing exact whole-process route')
                for process,rows in route['fit_records'].items():
                    if len(rows)!=3 or {r['fold'] for r in rows}!={0,1,2}:
                        raise ValueError('missing fold route evidence')
                    total+=len(rows)
                if len(route['states'])!=6 or len({s['process'] for s in route['states']})!=6:
                    raise ValueError('process state denominator changed')
                auth=route['authorization']
                if auth['numerically_certified']:
                    oof=route['full_oof']
                    if len(oof)!=c['generator']['occurrences']+c['generator']['background']:
                        raise ValueError('missing OOF rows')
                    cells=[row['cell_id'] for row in oof]
                    if len(set(cells))!=len(cells):raise ValueError('duplicate OOF sampled cell')
                    stat=rerun_frozen_permutation(oof,n_permutations=c['full_system_gate']['permutations'],seed=c['full_system_gate']['permutation_seed'])
                    if abs(stat['score']-auth['score'])>1e-11 or abs(stat['p_value']-auth['p_value'])>1e-12:
                        raise ValueError('saved full-system permutation is not reproducible')
                    screen=bool(stat['score']>=c['full_system_gate']['adequacy_floor']
                        and stat['score']+np.log(2)>=c['full_system_gate']['gain_over_uniform']
                        and stat['p_value']<=c['full_system_gate']['alpha'])
                    if screen!=auth['authorized']:raise ValueError('authorization gate mismatch')
                    full_checks+=1
                else:
                    incomplete.append((mode,effort,learner))
                    if auth['authorized']:
                        raise ValueError('numerically invalid learner was authorized')
    if total!=len(c['split_modes'])*len(c['effort_regimes'])*len(c['learner_routes'])*7*3:
        raise ValueError('per-case fit records incomplete')
    return {'fit_count':total,'full_system_permutation_verified':full_checks,'uncertified_routes':len(incomplete)}


def run(root:Path,config:Path,out:Path):
    c=json.loads(config.read_text())
    if c.get('status')!='design_frozen_before_new_seed_opening':raise ValueError('open or changed preregistration')
    parts=sorted(root.glob('sdmr-nonlinear-effort-v2-case-*'))
    cases=[];sources=[];fits=perms=0;failures=0
    for part in parts:
        fp=part/'finite_before_oracle.json';cp=part/'case.json'
        if not fp.exists() or not cp.exists():raise ValueError('partial artifact detected')
        fr=fp.read_bytes();cr=cp.read_bytes()
        case=json.loads(cr);finite=json.loads(fr)
        verify_receipt_hash(fp,case['finite_receipt_sha256'])
        counts=verify_case(finite,case,c,source_dir=part)
        cases.append(case)
        sources.append({'world':case['world'],'seed':case['seed'],
                        'case_sha256':digest(cr),'finite_sha256':digest(fr)})
        fits+=counts['fit_count'];perms+=counts['full_system_permutation_verified'];failures+=counts['uncertified_routes']
    from nonlinear_effort_core_v2 import audit_case_denominators
    audit_case_denominators(cases,c)
    if fits!=c['denominators']['finite_fit_records']:
        raise ValueError('frozen finite fit denominator mismatch')
    summary=summarize_cases(cases,c)
    result={'schema':'sdmr.nonlinear_effort_known_truth.aggregate_receipt.v2',
       'status':'complete_development_science_not_promotion',
       'original_v5_promotion':'failed_closed','original_M5_evidence_changed':False,
       'n_cases':len(cases),'finite_fit_records_checked':fits,
       'full_system_permutation_pvalues_independently_verified':perms,
       'uncertified_full_routes':failures,'source_receipts':sources,
       'scientific_scope':{'primary':'effort-unavailable pair comparison across random/spatial',
           'effort_upper_bound':'additional model-information universe; not a fair same-target ODO accuracy estimate'},
       'summary':summary}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'n_cases':len(cases),'fits':fits,
        'pvalues_independently_recalculated':perms,
        'by_policy':summary['by_policy']},indent=2,ensure_ascii=False))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--contract',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();run(a.root,a.contract,a.out)
