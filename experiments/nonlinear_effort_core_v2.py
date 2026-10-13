"""Frozen, truth-blind helper functions for a new nonlinear/effort sensitivity study.

The optional known sampling effort is PRIVILEGED simulator information, not a
field-ready GBIF covariate and not a surrogate for the generating-process truth.
"""
from __future__ import annotations
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

SHARP=frozenset(('replaceable','contributory','required'))
POSITIVE=frozenset(('contributory','required'))
STATES=SHARP|frozenset(('unresolved','unavailable'))


def known_effort_features(x, sampled_cell_ids, environment, *, available:bool):
    x=np.asarray(x,dtype=float)
    cells=np.asarray(sampled_cell_ids)
    if x.ndim!=2 or cells.ndim!=1 or x.shape[0]!=len(cells) or not np.isfinite(x).all():
        raise ValueError('ecological predictor matrix and aligned cell IDs required')
    if not available:
        return x
    # Use only the two declared columns, never suitability / generating truth.
    allowed=environment.loc[:,['cell_id','sampling_effort']].copy()
    if allowed.cell_id.duplicated().any():
        raise ValueError('duplicate cell_id in effort covariate')
    effort=pd.to_numeric(allowed.sampling_effort,errors='raise').to_numpy(float)
    if not np.isfinite(effort).all() or not (effort>0).all():
        raise ValueError('effort values must be finite and positive')
    lookup=dict(zip(allowed.cell_id.astype(int),effort,strict=True))
    try:
        log_effort=np.log([lookup[int(c)] for c in cells])
    except KeyError as exc:
        raise ValueError('missing effort for sampled cell ID') from exc
    return np.column_stack((x,log_effort))


def ecological_closure_index(predictor_names, removed_carriers, *, with_effort:bool):
    names=tuple(predictor_names)
    carriers=set(removed_carriers)
    if not carriers or not carriers.issubset(set(names)):
        raise ValueError('undeclared or empty process-information closure')
    indexes=[i for i,p in enumerate(names) if p not in carriers]
    if not indexes:
        raise ValueError('removing closure leaves no ecological representation')
    if with_effort:
        indexes.append(len(names))
    return indexes


def predict_forest(x_train,y_train,x_test):
    x=np.asarray(x_train,dtype=float)
    y=np.asarray(y_train,dtype=int)
    v=np.asarray(x_test,dtype=float)
    if x.ndim!=2 or v.ndim!=2 or x.shape[1]!=v.shape[1] or len(x)!=len(y):
        raise ValueError('training/test dimensions must match')
    if not np.isfinite(x).all() or not np.isfinite(v).all() or set(np.unique(y))!={0,1}:
        return None,{'passed':False,'reason':'nonfinite_or_missing_class'}
    model=RandomForestClassifier(n_estimators=256,max_leaf_nodes=7,
        min_samples_leaf=20,max_features=1.0,bootstrap=True,
        class_weight='balanced_subsample',random_state=0,n_jobs=1)
    model.fit(x,y)
    p=np.asarray(model.predict_proba(v)[:,1],float)
    passed=bool(np.isfinite(p).all() and (p>=0).all() and (p<=1).all() and len(model.estimators_)==256)
    return (p if passed else None), {'passed':passed,'reason':'fixed_forest_completed' if passed else 'nonfinite_forest_output',
        'n_trees':len(model.estimators_),'max_leaf_nodes':7,'min_leaf':20}


def consensus(a,b):
    if a not in STATES or b not in STATES:
        raise ValueError('unknown process state')
    if 'unavailable' in (a,b):return 'unavailable'
    return a if a==b and a in SHARP else 'unresolved'


def audit_case_denominators(cases:list[dict],config:dict):
    expected={(int(seed),str(world)) for seed in config['seeds'] for world in config['worlds']}
    got=[(int(c['seed']),str(c['world'])) for c in cases]
    if len(set(got))!=len(got):
        raise ValueError('duplicate seed/world case')
    if len(cases)!=len(expected) or set(got)!=expected or len(cases)!=config['denominators']['cases']:
        raise ValueError('case denominator differs from frozen contract')
    p=set(config['ecological_processes'])
    if len(p)!=config['denominators']['processes_per_case']:
        raise ValueError('process denominator changed')
    if len(cases)*len(p)!=config['denominators']['oracle_target_cells']:
        raise ValueError('oracle denominator changed')
    policies=set(config['comparisons'])
    for case in cases:
        if case['status']!='complete_finite_before_oracle' or set(case['oracle'])!=p:
            raise ValueError('case has missing or incomplete ODO reference')
        if set(case['consensus'])!=set(config['split_modes']):
            raise ValueError('split denominator changed')
        for mode,regimes in case['consensus'].items():
            if set(regimes)!=set(config['effort_regimes']):
                raise ValueError('effort denominator changed')
            for effort,policy_dict in regimes.items():
                if set(policy_dict)!=policies or any(set(states)!=p for states in policy_dict.values()):
                    raise ValueError('policy/process denominator changed')
                if any(st not in STATES for states in policy_dict.values() for st in states.values()):
                    raise ValueError('invalid consensus state')
    return True


def summarize_cases(cases:list[dict],config:dict):
    audit_case_denominators(cases,config)
    ref=Counter(s for case in cases for s in case['oracle'].values())
    output={'schema':'sdmr.nonlinear_effort_known_truth.aggregate.v2','cases':len(cases),
        'oracle_target_cells':sum(ref.values()),'reference_counts':dict(ref),'by_policy':{}}
    for mode in config['split_modes']:
        output['by_policy'][mode]={}
        for effort in config['effort_regimes']:
            output['by_policy'][mode][effort]={}
            for policy in config['comparisons']:
                cells=[(case['oracle'][process],case['consensus'][mode][effort][policy][process])
                       for case in cases for process in config['ecological_processes']]
                cc=Counter(s for _,s in cells)
                n=len(cells)
                output['by_policy'][mode][effort][policy]={
                    'cells':n,
                    'joint_authorized_cases':sum(bool(c['authorizations'][mode][effort][policy]) for c in cases),
                    'sharp':sum(cc[s] for s in SHARP),
                    'unresolved':cc['unresolved'],'unavailable':cc['unavailable'],
                    'positive_recovered':sum(r in POSITIVE and f in POSITIVE for r,f in cells),
                    'positive_denominator':sum(r in POSITIVE for r,_ in cells),
                    'false_positive_replaceable':sum(r=='replaceable' and f in POSITIVE for r,f in cells),
                    'replaceable_denominator':sum(r=='replaceable' for r,_ in cells),
                    'overresolved_unresolved':sum(r=='unresolved' and f in SHARP for r,f in cells),
                    'unresolved_denominator':sum(r=='unresolved' for r,_ in cells),
                    'sharp_on_unavailable':sum(r=='unavailable' and f in SHARP for r,f in cells),
                    'unavailable_denominator':sum(r=='unavailable' for r,_ in cells),
                    'state_counts':{s:cc[s] for s in sorted(STATES)},
                }
    return output


def safe_jsonable(value):
    """Encode scientific missing values as JSON null instead of illegal NaN."""
    if isinstance(value,dict):
        return {str(k):safe_jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [safe_jsonable(v) for v in value]
    if isinstance(value,np.generic):
        return safe_jsonable(value.item())
    if isinstance(value,float) and not np.isfinite(value):
        return None
    if isinstance(value,np.ndarray):
        return [safe_jsonable(v) for v in value.tolist()]
    return value
