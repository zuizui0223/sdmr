#!/usr/bin/env python3
"""Exploratory closure challenge with matched spatial folds and reliable learners.

Three separately reported objectives: original raw-feature L2, isotropic L2 in
train-standardized features, and unchanged shallow3 HGB. All scientific gates
are inherited unchanged; the original v5 remains closed. No sealed data input.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, sys, warnings, zipfile
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import scipy, sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from v5_objective_preserving_solver import fit_preserved_ridge
ROOT=Path(__file__).resolve().parents[1]
ARMS=('raw_objective_converged','standardized_isotropic_converged','shallow3_hgb')
PROCESSES=('thermal','water','seasonality','radiation_energy','soil_substrate','productivity')
SHARP={'replaceable','contributory','required'}
INPUT_SHA='9a2574ab03506123b1119ed92b5432f5929a293b4d790bed38ac5290ac281237'
REG_SHA='6e3e7fc8d3d46cbd4bb983914beadf315635d45b'
RULE_SHA='7ff69d91d88025bfcb5c69aac95aa7b9b723ae0c'

def hash_array(a):return hashlib.sha256(np.asarray(a).tobytes(order='C')).hexdigest()
def git_hash(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def load_rules():
 choices=[ROOT/'src/sdmr/process_id/states.py',ROOT/'sources/original_states.py']
 p=next((p for p in choices if p.exists()),None)
 if p is None:raise FileNotFoundError('byte-pinned original states.py required')
 if git_hash(p.read_bytes())!=RULE_SHA:raise ValueError('original scientific state rules changed')
 sp=importlib.util.spec_from_file_location('frozen_closure_rules',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 return m
RULES=load_rules()

def load_inputs(path):
 path=Path(path)
 if hashlib.sha256(path.read_bytes()).hexdigest()!=INPUT_SHA:raise ValueError('exact first10 input ZIP hash mismatch')
 rows=[]
 with zipfile.ZipFile(path) as archive:
  manifest=json.loads(archive.read('manifest.json'))
  if manifest['sealed_answer_check_read'] or manifest['original_v5_promotion']!='failed_closed':raise ValueError('sealed input boundary violated')
  if manifest['exported_taxa']!=10 or manifest['reference_taxa']!=50:raise ValueError('input denominator changed')
  for row in manifest['rows']:
   data=archive.read(row['file'])
   if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('NPZ hash mismatch')
   with np.load(io.BytesIO(data),allow_pickle=False) as z:
    x=z['x'];y=z['y'];groups=z['groups'];pred=z['predictors'].astype(str).tolist()
    folds=[(z[f'train_{i}'],z[f'test_{i}']) for i in range(3)]
   for a,k in [(x,'x_sha256'),(y,'y_sha256'),(groups,'groups_sha256')]:
    if hash_array(a)!=row[k]:raise ValueError('input array hash mismatch')
   replay=list(GroupKFold(n_splits=3).split(x,y,groups))
   for i,((tr,te),(savedtr,savedte)) in enumerate(zip(replay,folds,strict=True)):
    if not(np.array_equal(tr,savedtr) and np.array_equal(te,savedte)):raise ValueError('spatial fold changed')
    if set(groups[tr])&set(groups[te]):raise ValueError('spatial groups leaked')
    for a,k in [(x[tr],'train'),(x[te],'validation')]:
     if hash_array(a)!=row['reference']['fold_matrices'][i][k]['a_sha256']:raise ValueError('fold matrix hash mismatch')
   rows.append(dict(selection_rank=row['selection_rank'],scientific_name=row['scientific_name'],x=x,y=y,groups=groups,predictors=pred,splits=folds))
 if [r['selection_rank'] for r in rows]!=list(range(1,11)):raise ValueError('first10 order changed')
 return rows

def closure_columns(predictors,registry,process):
 carrier=set(registry.loc[registry.process==process,'predictor'].astype(str))
 if not carrier or not carrier<=set(predictors):raise ValueError('missing process or carrier')
 excluded=[p for p in predictors if p in carrier];kept=[p for p in predictors if p not in carrier]
 if not kept:raise ValueError('empty alternative route requires explicit unavailable handling')
 return excluded,kept

def balanced_score(y,p):
 y=np.asarray(y);p=np.clip(np.asarray(p),1e-9,1-1e-9)
 if set(np.unique(y))!={0,1}:raise ValueError('score requires both classes')
 return float(.5*(np.log(p[y==1]).mean()+np.log1p(-p[y==0]).mean()))

def authorize(oofs):
 score=float(np.mean([balanced_score(y,p) for y,p in oofs]));rng=np.random.default_rng(0);exceed=0
 for _ in range(999):exceed+=np.mean([balanced_score(rng.permutation(y),p) for y,p in oofs])>=score
 pv=float((1+exceed)/1000)
 return dict(score=score,gain_over_constant=float(score+np.log(2)),p_value=pv,
             authorized=bool(score>=-.75 and score+np.log(2)>=.01 and pv<=.001))

def fit_route(tx,ty,vx,arm):
 tx=np.asarray(tx,float);ty=np.asarray(ty,int);vx=np.asarray(vx,float)
 if arm=='shallow3_hgb':
  n=len(ty);sw=np.where(ty==1,n/(2*ty.sum()),n/(2*(n-ty.sum())))
  model=HistGradientBoostingClassifier(loss='log_loss',learning_rate=.05,max_iter=100,max_leaf_nodes=3,
      min_samples_leaf=40,l2_regularization=1.,early_stopping=False,random_state=0)
  model.fit(tx,ty,sample_weight=sw);p=model.predict_proba(vx)[:,1]
  return p,{'passed':bool(np.isfinite(p).all()),'criterion':'fixed_100_boosting_steps_finite_prediction_not_optimizer_stationarity','iterations':int(model.n_iter_)}
 if arm not in ARMS:raise ValueError('unknown learner')
 train_mean=tx.mean(axis=0).tolist()
 if arm=='standardized_isotropic_converged':
  scale=StandardScaler().fit(tx);tx=scale.transform(tx);vx=scale.transform(vx)
 # Original solver preserves L2 in its input units, also when its input is Z.
 one=fit_preserved_ridge(tx,ty,tol=1e-12,max_iter=100,start='zero')
 two=fit_preserved_ridge(tx,ty,tol=1e-12,max_iter=100,start='fixed')
 p=one.predict_proba(vx);gap=float(np.max(np.abs(p-two.predict_proba(vx))))
 passed=bool(one.converged and two.converged and gap<=2e-6 and np.isfinite(p).all())
 cert={'passed':passed,'criterion':'gradient_newton_decrement_and_two_starts',
       'iterations':int(one.iterations),'second_iterations':int(two.iterations),
       'gradient_inf':one.gradient_inf,'newton_decrement':one.newton_decrement,
       'second_gradient_inf':two.gradient_inf,'second_newton_decrement':two.newton_decrement,
       'two_start_gap':gap,'reason':one.reason,'second_reason':two.reason,'train_mean':train_mean}
 return p,cert

def state_from_scores(full,knockout,numerically_complete,auth):
 full=np.asarray(full,float);knockout=np.asarray(knockout,float)
 delta=full-knockout;mean=float(np.mean(delta));sem=float(np.std(delta,ddof=1)/np.sqrt(len(delta)))
 row=dict(route='matched',complete=bool(numerically_complete),full_adequate=bool(full.mean()>=-.75),
          knockout_adequate=bool(knockout.mean()>=-.75),delta_mean=mean,delta_sem=sem)
 state=RULES.classify_process_state(pd.DataFrame([row]),margin=.01,adequacy_floor=-.75,sem_multiplier=1.)
 reason='original_interval_rule'
 if not auth['authorized']:state='unavailable';reason='full_system_not_authorized'
 elif not numerically_complete:state='unresolved';reason='numerical_certificate_failed'
 return dict(state=state,reason=reason,delta_mean=mean,delta_sem=sem,lower=mean-sem,upper=mean+sem,
             full_score=float(full.mean()),knockout_score=float(knockout.mean()),complete=bool(numerically_complete))

def consensus(a,b):
 if a not in RULES.PROCESS_STATES or b not in RULES.PROCESS_STATES:raise ValueError('unknown state')
 if 'unavailable' in {a,b}:return 'unavailable'
 return a if a==b and a in SHARP else 'unresolved'

def summarize(report):
 rows=report['rows'];result={}
 for arm in ARMS:
  counts=Counter(s['state'] for r in rows for s in r['learners'][arm]['states'])
  fits=[f for r in rows for f in r['learners'][arm]['fits']]
  result[arm]={'authorized_taxa':sum(r['learners'][arm]['authorization']['authorized'] for r in rows),
      'mean_full_score':float(np.mean([r['learners'][arm]['authorization']['score'] for r in rows])),
      'state_counts':{s:counts[s] for s in RULES.PROCESS_STATES},'state_denominator':len(rows)*6,
      'fit_count':len(fits),'certified_fits':sum(f['certificate']['passed'] for f in fits)}
 result['pairs']={}
 for arm in ARMS[:2]:
  key=arm+'__vs_hgb';cs=Counter(s['state'] for r in rows for s in r['consensus'][key])
  common=sum(r['learners'][arm]['authorization']['authorized'] and r['learners']['shallow3_hgb']['authorization']['authorized'] for r in rows)
  result['pairs'][key]={'counts':{s:cs[s] for s in RULES.PROCESS_STATES},'denominator':len(rows)*6,
      'stable_sharp':sum(cs[s] for s in SHARP),'both_authorized_taxa':int(common),'conditional_denominator':int(common)*6}
 return result

def run(input_zip,registry_path,output):
 registry_path=Path(registry_path)
 if git_hash(registry_path.read_bytes())!=REG_SHA:raise ValueError('frozen registry byte identity changed')
 registry=pd.read_csv(registry_path);records=load_inputs(input_zip)
 report={'schema':'sdmr.v5.matched_reliable_closure_results.v1','status':'exploratory_postterminal',
         'original_v5_promotion':'failed_closed','sealed_answer_check_read':False,
         'reference_taxa':50,'tested_taxa':10,'cells_per_arm':60,'splits':'identical_original_spatial_three_folds',
         'versions':dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__),
         'input_zip_sha256':hashlib.sha256(Path(input_zip).read_bytes()).hexdigest(),'registry_blob_sha':REG_SHA,'state_classifier_blob_sha':RULE_SHA,
         'outcome_rules':dict(margin=.01,adequacy_floor=-.75,sem_multiplier=1.,perm_n=999,perm_alpha=.001,perm_seed=0),'rows':[]}
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 for rec in records:
  x,y,groups,predictors=rec['x'],rec['y'],rec['groups'],rec['predictors'];splits=rec['splits']
  row={'scientific_name':rec['scientific_name'],'selection_rank':rec['selection_rank'],
       'x_sha256':hash_array(x),'y_sha256':hash_array(y),'groups_sha256':hash_array(groups),'learners':{},'consensus':{}}
  challenges={'full':([],predictors)}
  for process in PROCESSES:challenges[process]=closure_columns(predictors,registry,process)
  for arm in ARMS:
   fits=[];scores={p:[] for p in challenges};certs={p:[] for p in challenges};full_oof=[]
   for fold,(tr,te) in enumerate(splits):
    for process,(excluded,kept) in challenges.items():
     inds=[predictors.index(p) for p in kept]
     p,c=fit_route(x[tr][:,inds],y[tr],x[te][:,inds],arm)
     score=balanced_score(y[te],p);scores[process].append(score);certs[process].append(c['passed'])
     fits.append({'fold':fold,'challenge':process,'excluded_predictors':excluded,'retained_predictors':kept,
                  'score':score,'certificate':c})
     if process=='full':full_oof.append((y[te],p))
   auth=authorize(full_oof);auth['numerically_certified']=all(certs['full']);auth['authorized_without_numeric_check']=auth['authorized']
   auth['authorized']=bool(auth['authorized'] and auth['numerically_certified'])
   states=[]
   for process in PROCESSES:
    s=state_from_scores(scores['full'],scores[process],all(certs['full']+certs[process]),auth)
    s.update(process=process,closure_predictors=','.join(challenges[process][0]),fold_deltas=(np.array(scores['full'])-np.array(scores[process])).tolist())
    states.append(s)
   states=RULES.apply_identical_closure_abstention(pd.DataFrame(states)).to_dict(orient='records')
   row['learners'][arm]={'authorization':auth,'states':states,'fits':fits}
  for arm in ARMS[:2]:
   a={s['process']:s['state'] for s in row['learners'][arm]['states']};b={s['process']:s['state'] for s in row['learners']['shallow3_hgb']['states']}
   row['consensus'][arm+'__vs_hgb']=[{'process':p,'linear_state':a[p],'hgb_state':b[p],'state':consensus(a[p],b[p])} for p in PROCESSES]
  report['rows'].append(row);report['summary']=summarize(report)
  output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
  print(rec['selection_rank'],rec['scientific_name'],{a:{'auth':row['learners'][a]['authorization']['authorized'],'states':dict(Counter(s['state'] for s in row['learners'][a]['states']))} for a in ARMS},flush=True)
 print(json.dumps(report['summary'],indent=2),flush=True)
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument('--input-zip',type=Path,required=True);p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();run(a.input_zip,a.registry,a.output)
if __name__=='__main__':main()
