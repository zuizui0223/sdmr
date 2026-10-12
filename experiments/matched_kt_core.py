"""Pure denominator and split-primitives for preregistered SDMR known-truth comparison.

No training, generator truth, prospective seed sampling, or adaptive selection.
"""
from __future__ import annotations

from collections import Counter
from itertools import product
import numpy as np
from sklearn.model_selection import GroupKFold, KFold

SHARP = frozenset(('replaceable', 'contributory', 'required'))
POSITIVE = frozenset(('contributory', 'required'))
STATES = SHARP | frozenset(('unresolved', 'unavailable'))


def make_case_splits(cell_ids, spatial_groups, labels, *, split_mode: str, n_splits: int = 3):
    cells = np.asarray(cell_ids)
    groups = np.asarray(spatial_groups)
    y = np.asarray(labels)
    if cells.ndim != 1 or cells.size != len(groups) or len(groups) != len(y):
        raise ValueError('cell IDs, groups and labels must be aligned 1-D inputs')
    if n_splits != 3:
        raise ValueError('frozen matched benchmark uses three folds')
    if set(np.unique(y)) != {0, 1}:
        raise ValueError('both classes required')
    if split_mode == 'spatial':
        if len(np.unique(groups)) < n_splits:
            raise ValueError('insufficient unique spatial groups')
        folds=list(GroupKFold(n_splits=n_splits).split(cells,y,groups=groups))
    elif split_mode == 'random_cell':
        unique=np.unique(cells)
        if len(unique) < n_splits:
            raise ValueError('insufficient unique sampled cell IDs')
        splitter=KFold(n_splits=n_splits,shuffle=True,random_state=0)
        folds=[(np.flatnonzero(np.isin(cells,unique[train])),
                np.flatnonzero(np.isin(cells,unique[test])))
               for train,test in splitter.split(unique)]
    else:
        raise ValueError('unknown frozen split mode')
    for train,test in folds:
        if len(train)==0 or len(test)==0 or set(np.unique(y[train]))!={0,1} or set(np.unique(y[test]))!={0,1}:
            raise ValueError('a declared fold is missing a class or rows')
        if set(cells[train]) & set(cells[test]):
            raise ValueError('sampled cell leakage')
        if split_mode=='spatial' and set(groups[train]) & set(groups[test]):
            raise ValueError('spatial group leakage')
    if sorted(np.concatenate([test for _,test in folds]).tolist()) != list(range(len(cells))):
        raise ValueError('fold assignment failed to cover all sampled records')
    return folds


def consensus_state(a: str, b: str) -> str:
    if a not in STATES or b not in STATES:
        raise ValueError('unknown process state')
    if 'unavailable' in (a,b):
        return 'unavailable'
    if a==b and a in SHARP:
        return a
    return 'unresolved'


def _fraction(n:int,d:int):
    return {'numerator':int(n),'denominator':int(d),'rate':None if d==0 else n/d}


def aggregate_cases(cases: list[dict], contract: dict) -> dict:
    expected={(int(seed),str(world)) for seed,world in product(contract['seeds'],contract['worlds'])}
    observed=[(int(c['seed']),str(c['world'])) for c in cases]
    if len(cases)!=len(expected) or set(observed)!=expected or len(set(observed))!=len(observed):
        raise ValueError('case set does not match the frozen seed-by-world denominator')
    if len(cases)!=int(contract['denominators']['world_seed_cases']):
        raise ValueError('case denominator changed')
    modes=tuple(contract['finite']['split_modes'])
    if set(modes)!={'random_cell','spatial'}:
        raise ValueError('split mode contract changed')
    process_n=int(contract['denominators']['processes_per_case'])
    if process_n*len(cases)!=int(contract['denominators']['consensus_cells_per_split']):
        raise ValueError('fixed process-cell denominator inconsistent')
    if process_n*len(cases)!=int(contract['denominators']['oracle_targets']):
        raise ValueError('ODO reference-cell denominator inconsistent')
    output={'paired_world_seed_cases':len(cases), 'oracle_target_cells':process_n*len(cases)}
    for mode in modes:
        pairs=[];authorized=0
        for case in cases:
            if case.get('status')!='completed_all_declared_states':
                raise ValueError('incomplete prospective case')
            oracle=case['oracle']
            table=case['consensus']
            if set(table)!=set(modes) or len(oracle)!=process_n:
                raise ValueError('case missing frozen mode or process cell')
            if set(table[mode])!=set(oracle):
                raise ValueError('ODO/finite process-cell alignment mismatch')
            authorized+=int(bool(case['authorization'][mode]))
            for process,truth in oracle.items():
                state=table[mode][process]
                if truth not in STATES or state not in STATES:
                    raise ValueError('unknown oracle or finite state')
                pairs.append((truth,state))
        counts=Counter(v for _,v in pairs)
        op=sum(t in POSITIVE for t,_ in pairs)
        pos=sum(t in POSITIVE and f in POSITIVE for t,f in pairs)
        rep=sum(t=='replaceable' for t,_ in pairs)
        fp=sum(t=='replaceable' and f in POSITIVE for t,f in pairs)
        unres=sum(t=='unresolved' for t,_ in pairs)
        over=sum(t=='unresolved' and f in SHARP for t,f in pairs)
        unavailable=sum(t=='unavailable' for t,_ in pairs)
        unsafe=sum(t=='unavailable' and f in SHARP for t,f in pairs)
        output[mode]={
            'denominator':len(pairs),
            'joint_authorized':_fraction(authorized,len(cases)),
            'stable_sharp':sum(counts[k] for k in SHARP),
            'unresolved':counts['unresolved'],
            'unavailable':counts['unavailable'],
            'state_counts':{state:int(counts[state]) for state in sorted(STATES)},
            'positive_recovery':_fraction(pos,op),
            'false_positive_on_replaceable':_fraction(fp,rep),
            'overresolution_on_unresolved':_fraction(over,unres),
            'sharp_on_unavailable':_fraction(unsafe,unavailable),
        }
    # A direction-of-effect summary, NOT an inferential significance test.
    diffs=[]
    for c in cases:
        sp=sum(v in SHARP for v in c['consensus']['spatial'].values())
        ra=sum(v in SHARP for v in c['consensus']['random_cell'].values())
        diffs.append(ra-sp)
    output['paired_sharp_count_differences']={'n':len(diffs),
        'random_higher':int(sum(d>0 for d in diffs)),
        'spatial_higher':int(sum(d<0 for d in diffs)),
        'tied':int(sum(d==0 for d in diffs)),
        'mean_random_minus_spatial':float(np.mean(diffs))}
    return output
