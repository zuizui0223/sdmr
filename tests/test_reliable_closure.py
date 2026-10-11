from pathlib import Path
import importlib.util, sys
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments'))

def module():
 p=ROOT/'experiments/v5_reliable_closure_probe.py'
 assert p.exists(),'closure diagnostic is not implemented yet'
 spec=importlib.util.spec_from_file_location('closureprobe',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_whole_carrier_deletion_not_single_variable():
 m=module();reg=pd.DataFrame({'predictor':['t','e','pet','pet','w'],'process':['thermal','thermal','thermal','water','water']})
 exc,keep=m.closure_columns(['t','w','e','pet'],reg,'thermal')
 assert exc==['t','e','pet'] and keep==['w']
 with pytest.raises(ValueError):m.closure_columns(['t','w','e','pet'],reg,'unknown')

def test_unavailable_is_not_biological_absence():
 m=module();auth={'authorized':False}
 d=m.state_from_scores([-.9]*3,[-.8]*3,True,auth)
 assert d['state']=='unavailable' and d['reason']=='full_system_not_authorized'

def test_failed_numerical_certificate_cannot_make_sharp_call():
 m=module();d=m.state_from_scores([-.4]*3,[-.6]*3,False,{'authorized':True})
 assert d['state']=='unresolved'

def test_positive_noninferior_and_uncertain_states():
 m=module()
 assert m.state_from_scores([-.4]*3,[-.5]*3,True,{'authorized':True})['state']=='contributory'
 assert m.state_from_scores([-.4]*3,[-.9]*3,True,{'authorized':True})['state']=='required'
 assert m.state_from_scores([-.4]*3,[-.4]*3,True,{'authorized':True})['state']=='replaceable'
 assert m.state_from_scores([-.4]*3,[-.6,-.1,-.5],True,{'authorized':True})['state']=='unresolved'

def test_consensus_counts_unavailable_and_unresolved_in_fixed_denominator():
 m=module()
 assert m.consensus('required','required')=='required'
 assert m.consensus('required','replaceable')=='unresolved'
 assert m.consensus('unavailable','required')=='unavailable'
 assert m.consensus('unresolved','unresolved')=='unresolved'

def test_mean_plus_one_sem_is_not_ninetyfive_ci():
 m=module();f=np.array([-.4,-.4,-.4]);k=np.array([-.41,-.5,-.39]);d=m.state_from_scores(f,k,True,{'authorized':True})
 assert d['delta_sem']==pytest.approx(np.std(f-k,ddof=1)/np.sqrt(3))
 assert d['lower']==pytest.approx(np.mean(f-k)-d['delta_sem'])
 assert d['upper']==pytest.approx(np.mean(f-k)+d['delta_sem'])

def test_two_converged_logistic_routes_train_only_and_equivalent_objective():
 m=module();rng=np.random.default_rng(12);x=rng.normal(size=(120,3))*[1,100,.02]
 y=(rng.uniform(size=120)<1/(1+np.exp(-x[:,0]))).astype(int);v=x[:7]+.01
 for route in ('raw_objective_converged','standardized_isotropic_converged'):
  p,c=m.fit_route(x,y,v,route)
  assert p.shape==(7,) and np.isfinite(p).all() and c['passed']
  assert c['two_start_gap']<=2e-6
  assert c['train_mean']==pytest.approx(x.mean(axis=0))
  p2,c2=m.fit_route(x,y,np.vstack([v,x[0]+100]),route)
  assert p2[:7]==pytest.approx(p,abs=1e-10)

def test_chance_predictor_fails_authorization():
 m=module();y=np.array([0,1]*20);d=m.authorize([(y,np.full(len(y),.5))]*3)
 assert d['score']==pytest.approx(-np.log(2)) and not d['authorized']

def test_existing_input_archive_detects_corruption_and_fixed_ranks():
 m=module();p=ROOT/'sources/sdmr_v5_objective_preserving_inputs_first10.zip'
 if not p.exists():pytest.skip('large scientific input archive is not installed')
 records=m.load_inputs(p)
 assert len(records)==10 and [r['selection_rank'] for r in records]==list(range(1,11))
 assert all(len(r['predictors'])==46 and len(r['splits'])==3 for r in records)
