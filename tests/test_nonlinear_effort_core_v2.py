import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).parents[1] / 'experiments'))
from nonlinear_effort_core_v2 import (
    known_effort_features, ecological_closure_index, predict_forest,
    consensus, audit_case_denominators, summarize_cases,
)


def test_known_effort_is_joined_by_cell_and_not_by_row():
    x=np.array([[1.0,2.0],[3.0,4.0],[5.0,6.0]])
    cells=np.array([3,1,2])
    env=pd.DataFrame({'cell_id':[1,2,3], 'sampling_effort':[0.5,0.25,1.0],
                      'true_suitability':[.99,.01,.8], 'generating_process_state':['secret']*3})
    untouched=known_effort_features(x,cells,env,available=False)
    assert np.array_equal(untouched,x)
    more=known_effort_features(x,cells,env,available=True)
    assert more.shape==(3,3)
    assert np.array_equal(more[:,:2],x)
    assert np.allclose(more[:,2],np.log([1.0,.5,.25]))
    env['true_suitability']=[.02,.99,.01]
    assert np.array_equal(known_effort_features(x,cells,env,available=True),more)
    with pytest.raises(ValueError, match='positive'):
        known_effort_features(x,cells,pd.DataFrame({'cell_id':[1,2,3], 'sampling_effort':[0,1,2]}),available=True)
    with pytest.raises(ValueError,match='duplicate'):
        known_effort_features(x,cells,pd.DataFrame({'cell_id':[1,1,3], 'sampling_effort':[1,2,3]}),available=True)


def test_complete_closure_retains_sampling_nuisance_and_never_retains_carriers():
    predictor_names=['thermal_a','shared_pet','water_b','other']
    closure=['thermal_a','shared_pet']
    assert ecological_closure_index(predictor_names,closure,with_effort=False)==[2,3]
    assert ecological_closure_index(predictor_names,closure,with_effort=True)==[2,3,4]
    with pytest.raises(ValueError,match='undeclared'):
        ecological_closure_index(predictor_names,['missing'],with_effort=True)


def test_fixed_forest_is_deterministic_probabilistic_and_seed_pinned():
    rng=np.random.default_rng(2)
    x=rng.normal(size=(240,5))
    y=((x[:,0]*x[:,1]+.35*x[:,2])>0).astype(int)
    p,c=predict_forest(x[:180],y[:180],x[180:])
    q,d=predict_forest(x[:180],y[:180],x[180:])
    assert c['passed'] and d['passed']
    assert c['n_trees']==256 and c['max_leaf_nodes']==7
    assert np.array_equal(p,q)
    assert np.isfinite(p).all() and (p>=0).all() and (p<=1).all()


def test_consensus_keeps_shared_unavailability_and_abstention():
    assert consensus('contributory','contributory')=='contributory'
    assert consensus('required','contributory')=='unresolved'
    assert consensus('replaceable','unresolved')=='unresolved'
    assert consensus('unavailable','contributory')=='unavailable'
    with pytest.raises(ValueError):consensus('absent','contributory')


def fake_case(world,seed,reference,policy_states):
    return {'world':world,'seed':seed,'status':'complete_finite_before_oracle',
        'oracle':reference,'consensus':policy_states,
        'authorizations':{mode:{effort:{policy:True for policy in policy_dict} for effort,policy_dict in regimes.items()} for mode,regimes in policy_states.items()}}


def test_aggregate_preserves_denominators_and_reports_overresolution_separately():
    config={'seeds':[1,2],'worlds':['a'],'ecological_processes':['thermal','water'],
        'split_modes':{'spatial':{},'random_cell':{}},
        'comparisons':{'baseline_pair':['hgb','logit'],'nonlinear_pair':['hgb','forest']},
        'effort_regimes':{'unavailable':{},'known_effort_upper_bound':{}},
        'denominators':{'cases':2,'processes_per_case':2,'oracle_target_cells':4,'cells_per_policy_split':4}}
    def policies(seed):
        out={}
        for split in ['spatial','random_cell']:
            out[split]={}
            for effort in config['effort_regimes']:
                out[split][effort]={'baseline_pair':{'thermal':'contributory','water':'replaceable'},
                                    'nonlinear_pair':{'thermal':'unresolved' if seed==2 else 'contributory',
                                                      'water':'contributory' if seed==1 else 'replaceable'}}
        return out
    cases=[fake_case('a',1,{'thermal':'contributory','water':'replaceable'},policies(1)),
           fake_case('a',2,{'thermal':'unresolved','water':'unavailable'},policies(2))]
    result=summarize_cases(cases,config)
    p=result['by_policy']['spatial']['unavailable']['nonlinear_pair']
    assert p['cells']==4 and p['positive_recovered']==1 and p['positive_denominator']==1
    assert p['false_positive_replaceable']==1 and p['replaceable_denominator']==1
    assert p['overresolved_unresolved']==0 and p['unresolved_denominator']==1
    assert p['sharp_on_unavailable']==1 and p['unavailable_denominator']==1
    assert result['reference_counts']=={'contributory':1,'replaceable':1,'unresolved':1,'unavailable':1}
    with pytest.raises(ValueError,match='denominator'):
        summarize_cases(cases[:1],config)
    with pytest.raises(ValueError,match='duplicate'):
        audit_case_denominators([cases[0],cases[0]],config)


def test_reference_evidence_nan_is_explicit_null_not_nonstandard_json():
    import json
    from nonlinear_effort_core_v2 import safe_jsonable
    case={'a':[float('nan'),np.float64('inf'),np.float64(0.25)],'b':np.int64(2)}
    cleaned=safe_jsonable(case)
    assert cleaned=={'a':[None,None,0.25],'b':2}
    assert json.loads(json.dumps(cleaned,allow_nan=False))==cleaned


def test_consensus_description_is_not_mistaken_for_third_model_policy():
    c={'seeds':[1],'worlds':['unique_process'],
       'ecological_processes':['thermal','water'],
       'split_modes':{'spatial':{},'random_cell':{}},
       'effort_regimes':{'unavailable':{},'known_effort_upper_bound':{}},
       'comparisons':{'baseline_pair':['hgb','logit'],
                      'nonlinear_pair':['hgb','rf'],
                      'consensus':'same exact sharp class, else abstain'},
       'denominators':{'cases':1,'processes_per_case':2,'oracle_target_cells':2,'cells_per_policy_split':2}}
    cp={}
    for split in c['split_modes']:
        cp[split]={}
        for eff in c['effort_regimes']:
            cp[split][eff]={p:{'thermal':'replaceable','water':'unresolved'}
                             for p in ('baseline_pair','nonlinear_pair')}
    case={'seed':1,'world':'unique_process','status':'complete_finite_before_oracle',
          'oracle':{'thermal':'replaceable','water':'unresolved'},
          'consensus':cp,
          'authorizations':{sp:{e:{p:True for p in ('baseline_pair','nonlinear_pair')}
                         for e in ep} for sp,ep in cp.items()}}
    r=summarize_cases([case],c)
    assert sorted(r['by_policy']['spatial']['unavailable'])==['baseline_pair','nonlinear_pair']
