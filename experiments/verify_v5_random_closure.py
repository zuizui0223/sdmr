#!/usr/bin/env python3
"""Independent arithmetic/denominator audit, without refitting or p-value recomputation."""
from pathlib import Path
import sys
from collections import Counter
import json,csv,statistics,math,hashlib
ROOT=Path(__file__).resolve().parents[1]
RESULT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/random_location_closure_first10.json'
REGISTRY=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'experiments/frozen_v5_process_registry.csv'
D=json.loads(RESULT.read_text())
A=('raw_objective_converged','standardized_isotropic_converged','shallow3_hgb')
P=('thermal','water','seasonality','radiation_energy','soil_substrate','productivity')
S=('replaceable','contributory','required','unresolved','unavailable')
assert D['original_v5_promotion']=='failed_closed' and D['sealed_answer_check_read'] is False
assert D['tested_taxa']==10 and D['reference_taxa']==50 and len(D['rows'])==10
R=list(csv.DictReader(REGISTRY.open()))
REG={p:{r['predictor'] for r in R if r['process']==p} for p in P}
ALL=set(x['predictor'] for x in R);assert len(ALL)==46
cnt={a:Counter() for a in A};pair={a:Counter() for a in A[:2]};certificate_counts=Counter();auth_counts=Counter()
for row in D['rows']:
 assert sorted(row['learners'])==sorted(A)
 for a in A:
  q=row['learners'][a];fits=q['fits'];assert len(fits)==21; assert len(q['states'])==6
  by={(f['fold'],f['challenge']):f for f in fits};assert len(by)==21
  for fit in fits:
   keep=set(fit['retained_predictors']);ex=set(fit['excluded_predictors'])
   if fit['challenge']=='full':assert keep==ALL and not ex
   else:assert ex==REG[fit['challenge']] and keep==ALL-ex
   assert math.isfinite(fit['score'])
   certificate_counts[a]+=int(fit['certificate']['passed'])
   if a=='shallow3_hgb':continue
   if fit['certificate']['passed']:
    c=fit['certificate'];assert c['gradient_inf']<=1e-12 and c['second_gradient_inf']<=1e-12
    assert c['newton_decrement']<=1e-9 and c['second_newton_decrement']<=1e-9
    assert c['two_start_gap']<=2e-6
  full=[by[i,'full']['score'] for i in range(3)]
  auth=q['authorization'];num=all(by[i,'full']['certificate']['passed'] for i in range(3))
  expected=(statistics.mean(full)>=-.75 and statistics.mean(full)+math.log(2)>=.01 and auth['p_value']<=.001 and num)
  assert auth['authorized']==expected
  assert auth['numerically_certified']==num
  assert auth['failed_numeric_folds']==sum(not by[i,'full']['certificate']['passed'] for i in range(3))
  auth_counts[a]+=expected
  for state in q['states']:
   proc=state['process'];ko=[by[i,proc]['score'] for i in range(3)]
   diff=[x-y for x,y in zip(full,ko)]
   mean=statistics.mean(diff);sem=statistics.stdev(diff)/math.sqrt(3)
   assert abs(state['delta_mean']-mean)<1e-12 and abs(state['delta_sem']-sem)<1e-12
   numerically_complete=num and all(by[i,proc]['certificate']['passed'] for i in range(3))
   if not expected:target='unavailable'
   elif not numerically_complete:target='unresolved'
   elif statistics.mean(ko)>=-.75 and mean+sem<=.01:target='replaceable'
   elif mean-sem<=.01:target='unresolved'
   elif statistics.mean(ko)>=-.75:target='contributory'
   else:target='required'
   assert state['state']==target,(row['scientific_name'],a,proc,state['state'],target)
   cnt[a][target]+=1
 for a in A[:2]:
  for item in row['consensus'][a+'__vs_hgb']:
   l=next(x['state'] for x in row['learners'][a]['states'] if x['process']==item['process'])
   h=next(x['state'] for x in row['learners']['shallow3_hgb']['states'] if x['process']==item['process'])
   target='unavailable' if 'unavailable' in (l,h) else l if l==h and l in ('replaceable','contributory','required') else 'unresolved'
   assert item['state']==target
   pair[a][target]+=1
for a in A:
 summary=D['summary'][a];assert summary['authorized_taxa']==auth_counts[a]
 assert summary['state_counts']=={s:cnt[a][s] for s in S}
 assert sum(cnt[a].values())==60 and summary['state_denominator']==60
 assert summary['fit_count']==210 and summary['certified_fits']==certificate_counts[a]
for a in A[:2]:
 summary=D['summary']['pairs'][a+'__vs_hgb']; assert summary['counts']=={s:pair[a][s] for s in S}
 assert summary['both_authorized_taxa']==sum(r['learners'][a]['authorization']['authorized'] and r['learners']['shallow3_hgb']['authorization']['authorized'] for r in D['rows'])
 assert sum(pair[a].values())==60
print(json.dumps({'audit':'PASS','process_cells_checked':180,'pair_states_checked':120,
                  'fit_records_checked':630,'numeric_certificates_passed':dict(certificate_counts),
                  'authorizations':dict(auth_counts)},indent=2))
