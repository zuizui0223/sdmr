#!/usr/bin/env python3
"""Same-runtime, model-pool-only diagnostic; never opens sealed input files."""
from __future__ import annotations
import argparse,hashlib,io,json,sys,warnings,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import scipy,sklearn
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from v5_objective_preserving_solver import fit_preserved_ridge,objective_derivatives

def bhash(a):return hashlib.sha256(np.asarray(a).tobytes(order='C')).hexdigest()

def bls(y,p):
    p=np.clip(p,1e-9,1-1e-9)
    return float(.5*(np.log(p[y==1]).mean()+np.log1p(-p[y==0]).mean()))

def gate(oofs):
    score=np.mean([bls(y,p) for y,p in oofs]);rng=np.random.default_rng(0)
    exceed=0
    for _ in range(999):exceed+=np.mean([bls(rng.permutation(y),p) for y,p in oofs])>=score
    pv=float((1+exceed)/1000.)
    return {'score':float(score),'gain_over_constant':float(score+np.log(2)),'p_value':pv,
            'authorized':bool(score>=-.75 and score+np.log(2)>=.01 and pv<=.001)}

def original_objective(x,y,coef,intercept,C=1.):
    n=len(y);sw=np.where(y==1,n/(2*y.sum()),n/(2*(n-y.sum())))
    eta=x@coef+intercept
    return float(np.average(np.logaddexp(0.,np.where(y==1,-eta,eta)),weights=sw)+.5*(coef@coef)/(C*sw.sum()))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-zip',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--limit',type=int,default=10)
    a=ap.parse_args()
    if not 1<=a.limit<=10:raise ValueError('only prespecified first 1..10 permitted')
    archive=zipfile.ZipFile(a.input_zip)
    manifest=json.loads(archive.read('manifest.json'))
    assert manifest['sealed_answer_check_read'] is False
    assert manifest['model_fitting_performed'] is False
    assert manifest['original_v5_promotion']=='failed_closed'
    assert manifest['exported_taxa']==10
    taxa=[r['scientific_name'] for r in manifest['rows']]
    refs={r['scientific_name']:r['reference'] for r in manifest['rows']}
    report={'schema':'sdmr.v5.objective_preserving_results.v1','scope':'postterminal model-pool development, not archived v5 improvement','original_v5_promotion':'failed_closed','sealed_answer_check_read':False,'reference_taxa':50,'tested_taxa':a.limit,'input_archive_sha256':hashlib.sha256(a.input_zip.read_bytes()).hexdigest(),'versions':{'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__},'rows':[]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for rank,taxon in enumerate(taxa[:a.limit],1):
        item=manifest['rows'][rank-1];data=archive.read(item['file'])
        assert hashlib.sha256(data).hexdigest()==item['sha256']
        with np.load(io.BytesIO(data),allow_pickle=False) as loaded:
            x=loaded['x'];y=loaded['y'];g=loaded['groups']
            saved_splits=[(loaded[f'train_{f}'],loaded[f'test_{f}']) for f in range(3)]
        ref=refs[taxon]
        for arr,key in [(x,'matrix'),(y,'labels'),(g,'groups')]:
            if bhash(arr)!=ref[key]['a_sha256']:raise ValueError('exact input parity failed: '+taxon+' '+key)
        splits=list(GroupKFold(n_splits=3).split(x,y,g))
        assert all(np.array_equal(u,w) and np.array_equal(v,z) for (u,v),(w,z) in zip(splits,saved_splits))
        row={'scientific_name':taxon,'selection_rank':rank,'exact_input_hash_match':True,'x_sha256':bhash(x),'folds':[]}
        oofs={k:[] for k in ('raw_lbfgs','preserved_newton','scaled_isotropic')}
        for fold,(tr,te) in enumerate(splits):
            tx=x[tr];vx=x[te];ty=y[tr];vy=y[te]
            for arr,key in [(tx,'train'),(vx,'validation')]:
                if bhash(arr)!=ref['fold_matrices'][fold][key]['a_sha256']:raise ValueError('fold parity failed')
            raw=LogisticRegression(C=1.,solver='lbfgs',max_iter=1000,tol=1e-4,class_weight='balanced',random_state=0)
            with warnings.catch_warnings(record=True) as warnings_raw:
                warnings.simplefilter('always',ConvergenceWarning);raw.fit(tx,ty)
            kept=fit_preserved_ridge(tx,ty,tol=1e-12,max_iter=100,start='zero')
            cross=fit_preserved_ridge(tx,ty,tol=1e-12,max_iter=100,start='fixed')
            scaler=StandardScaler().fit(tx)
            iso=LogisticRegression(C=1.,solver='lbfgs',max_iter=1000,tol=1e-4,class_weight='balanced',random_state=0)
            with warnings.catch_warnings(record=True) as warnings_iso:
                warnings.simplefilter('always',ConvergenceWarning);iso.fit(scaler.transform(tx),ty)
            independent=LogisticRegression(C=1.,solver='newton-cholesky',max_iter=100,tol=1e-9,class_weight='balanced',random_state=0)
            with warnings.catch_warnings(record=True) as warnings_ref:
                warnings.simplefilter('always');independent.fit(tx,ty)
            n=len(ty);weights=np.where(ty==1,n/(2*ty.sum()),n/(2*(n-ty.sum())))
            z=scaler.transform(tx);penalty=1/scaler.scale_**2
            fn=lambda theta:objective_derivatives(theta,z,ty,weights,penalty,C=1.)
            trust=minimize(lambda theta:fn(theta)[0],np.zeros(tx.shape[1]+1),
                           jac=lambda theta:fn(theta)[1],hess=lambda theta:fn(theta)[2],
                           method='trust-exact',options={'gtol':1e-9,'maxiter':200})
            ptrust=expit(scaler.transform(vx)@trust.x[:-1]+trust.x[-1])
            p0=raw.predict_proba(vx)[:,1];p1=kept.predict_proba(vx);p2=iso.predict_proba(scaler.transform(vx))[:,1]
            pref=independent.predict_proba(vx)[:,1]
            objective_raw=original_objective(tx,ty,raw.coef_[0],raw.intercept_[0])
            objective_kept=original_objective(tx,ty,kept.coef,kept.intercept)
            independent_agreement=float(np.max(np.abs(p1-pref)))
            start_agreement=float(np.max(np.abs(p1-cross.predict_proba(vx))))
            trust_agreement=float(np.max(np.abs(p1-ptrust)))
            certificate=bool(kept.converged and cross.converged and start_agreement<=2e-6 and trust.success and trust_agreement<=2e-6 and objective_kept<=objective_raw+1e-10 and abs(objective_kept-kept.objective)<=1e-10)
            foldrow={'fold':fold,'train_rows':len(tr),'validation_rows':len(te),'raw_score':bls(vy,p0),'preserved_score':bls(vy,p1),'scaled_isotropic_score':bls(vy,p2),'raw_iterations':int(raw.n_iter_[0]),'scaled_iterations':int(iso.n_iter_[0]),'newton_iterations':kept.iterations,'newton_converged':kept.converged,'newton_reason':kept.reason,'gradient_inf':kept.gradient_inf,'newton_decrement':kept.newton_decrement,'original_objective_raw_fit':objective_raw,'original_objective_preserved_fit':objective_kept,'objective_identity_error':abs(objective_kept-kept.objective),'two_start_prediction_gap':start_agreement,'independent_solver_prediction_gap':independent_agreement,'independent_solver_warnings':[str(w.message)[:180] for w in warnings_ref],'trust_solver_converged':bool(trust.success),'trust_solver_gradient_inf':float(np.max(np.abs(trust.jac))),'trust_solver_prediction_gap':trust_agreement,'trust_solver_iterations':int(trust.nit),'certificate_passed':certificate}
            row['folds'].append(foldrow)
            for k,p in zip(oofs,[p0,p1,p2]):oofs[k].append((vy,p))
        row['all_numerical_certificates_passed']=all(f['certificate_passed'] for f in row['folds'])
        row['scores_and_gates']={k:gate(v) for k,v in oofs.items()}
        row['original_objective_heldout_change']=row['scores_and_gates']['preserved_newton']['score']-row['scores_and_gates']['raw_lbfgs']['score']
        row['penalty_change_heldout_change']=row['scores_and_gates']['scaled_isotropic']['score']-row['scores_and_gates']['preserved_newton']['score']
        report['rows'].append(row)
        a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(rank,taxon,'cert',row['all_numerical_certificates_passed'],{k:round(v['score'],5) for k,v in row['scores_and_gates'].items()},flush=True)
    report['all_numerical_certificates_passed']=all(r['all_numerical_certificates_passed'] for r in report['rows'])
    report['summary']={k:{'authorized_taxa':sum(r['scores_and_gates'][k]['authorized'] for r in report['rows']),'mean_score':float(np.mean([r['scores_and_gates'][k]['score'] for r in report['rows']]))} for k in oofs}
    report['summary']['optimization_only']={'better_taxa':sum(r['original_objective_heldout_change']>0 for r in report['rows']),'mean_change':float(np.mean([r['original_objective_heldout_change'] for r in report['rows']])),'median_change':float(np.median([r['original_objective_heldout_change'] for r in report['rows']]))}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2))

if __name__=='__main__':main()
