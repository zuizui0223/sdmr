"""New prospective matched-known-truth audit: checks before implementation."""
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
from matched_kt_core import make_case_splits, consensus_state, aggregate_cases


def test_random_cell_keeps_duplicates_in_one_fold():
    cells=np.array([1,2,1,3,4,2,5,6,7,8,9,10])
    groups=np.array([0,0,0,1,1,0,1,1,2,2,2,2])
    labels=np.array([1,0,1,0,1,0,1,0,1,0,1,0])
    folds=make_case_splits(cells,groups,labels,split_mode='random_cell',n_splits=3)
    assert len(folds)==3
    assert sorted(np.concatenate([test for _,test in folds]).tolist())==list(range(len(cells)))
    for train,test in folds:
        assert set(cells[train]).isdisjoint(set(cells[test]))


def test_spatial_group_never_leaks():
    cells=np.arange(24)
    groups=np.repeat(np.arange(6),4)
    labels=np.tile([0,1],12)
    folds=make_case_splits(cells,groups,labels,split_mode='spatial',n_splits=3)
    for train,test in folds:
        assert set(groups[train]).isdisjoint(set(groups[test]))
        assert set(labels[train])==set(labels[test])=={0,1}


def test_consensus_abstains_instead_of_scoring_missing_as_negative():
    assert consensus_state('unavailable','replaceable')=='unavailable'
    assert consensus_state('required','unresolved')=='unresolved'
    assert consensus_state('contributory','contributory')=='contributory'
    assert consensus_state('replaceable','replaceable')=='replaceable'


def test_aggregation_keeps_declared_denominators_and_odo_truth():
    cases=[]
    for seed in [9,10]:
        oracle={'a':'contributory','b':'replaceable'}
        states={
            'random_cell':{'a':'contributory','b':'replaceable'},
            'spatial':{'a':'unavailable','b':'unavailable'},
        }
        cases.append({'seed':seed,'world':'toy','oracle':oracle,'consensus':states,
                      'authorization':{'random_cell':True,'spatial':False},
                      'status':'completed_all_declared_states'})
    cfg={'seeds':[9,10],'worlds':['toy'],'finite':{'split_modes':['random_cell','spatial']},
         'denominators':{'world_seed_cases':2,'oracle_targets':4,
                         'consensus_cells_per_split':4,'processes_per_case':2}}
    x=aggregate_cases(cases,cfg)
    assert x['random_cell']['stable_sharp']==4
    assert x['random_cell']['positive_recovery']=={'numerator':2,'denominator':2,'rate':1.}
    assert x['spatial']['stable_sharp']==0
    assert x['spatial']['positive_recovery']=={'numerator':0,'denominator':2,'rate':0.}
    assert x['spatial']['unavailable']==4
    assert x['paired_world_seed_cases']==2


def test_aggregation_rejects_missing_or_duplicate_cases():
    cfg={'seeds':[9,10],'worlds':['toy'],'finite':{'split_modes':['random_cell','spatial']},
         'denominators':{'world_seed_cases':2,'oracle_targets':4,
                         'consensus_cells_per_split':4,'processes_per_case':2}}
    base={'seed':9,'world':'toy','oracle':{'a':'replaceable','b':'unresolved'},
          'consensus':{'random_cell':{'a':'replaceable','b':'unresolved'},
                       'spatial':{'a':'unavailable','b':'unavailable'}},
          'authorization':{'random_cell':True,'spatial':False},
          'status':'completed_all_declared_states'}
    with pytest.raises(ValueError,match='case set'):
        aggregate_cases([base],cfg)
    with pytest.raises(ValueError,match='case set'):
        aggregate_cases([base,base],cfg)
