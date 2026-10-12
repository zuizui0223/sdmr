import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

PATH=Path(__file__).resolve().parents[1]/'experiments/v5_objective_preserving_solver.py'
spec=importlib.util.spec_from_file_location('objective_solver',PATH)
s=importlib.util.module_from_spec(spec);sys.modules[spec.name]=s;spec.loader.exec_module(s)

def fixture():
    rng=np.random.default_rng(87123)
    x=rng.normal(size=(180,5))*np.array([.1,1,10,100,3])+np.array([0,2,5,30,-4])
    y=(rng.random(180)<expit((x[:,0]/.1)*.6-x[:,2]/10*.4)).astype(int)
    w=np.where(y==1,len(y)/(2*y.sum()),len(y)/(2*(len(y)-y.sum())))
    return x,y,w

def test_reparameterization_preserves_original_loss_and_penalty():
    x,y,sw=fixture();sc=StandardScaler().fit(x);z=sc.transform(x)
    beta=np.array([.3,.1,-.2,.001,.25]);intercept=.12
    theta=np.r_[sc.scale_*beta,intercept+sc.mean_@beta]
    value,g,h=s.objective_derivatives(theta,z,y,sw,1/sc.scale_**2,C=1.)
    eta=x@beta+intercept
    target=np.average(np.logaddexp(0,np.where(y==1,-eta,eta)),weights=sw)+.5*np.sum(beta**2)/sw.sum()
    assert value==pytest.approx(target,rel=1e-12,abs=1e-12)

def test_derivatives_match_central_differences():
    x,y,sw=fixture();sc=StandardScaler().fit(x);z=sc.transform(x)
    t=np.linspace(-.2,.3,6);d=1/sc.scale_**2
    val,g,h=s.objective_derivatives(t,z,y,sw,d,C=1.)
    eps=1e-5;num=[];hh=[]
    for j in range(6):
        step=np.eye(6)[j]*eps
        a,ga,_=s.objective_derivatives(t+step,z,y,sw,d,C=1.)
        b,gb,_=s.objective_derivatives(t-step,z,y,sw,d,C=1.)
        num.append((a-b)/(2*eps));hh.append((ga-gb)/(2*eps))
    assert np.allclose(g,num,rtol=1e-6,atol=1e-8)
    assert np.allclose(h,np.array(hh).T,rtol=1e-6,atol=1e-8)

def test_matches_independent_raw_newton_cholesky():
    x,y,sw=fixture()
    got=s.fit_preserved_ridge(x,y,C=1.,max_iter=100,tol=1e-9)
    ref=LogisticRegression(C=1.,solver='newton-cholesky',class_weight='balanced',tol=1e-10,max_iter=100).fit(x,y)
    assert got.converged
    assert np.max(np.abs(got.predict_proba(x)-ref.predict_proba(x)[:,1]))<1e-6
    assert got.gradient_inf<1e-8

def test_stopping_without_certificate_fails_closed():
    x,y,_=fixture();got=s.fit_preserved_ridge(x,y,max_iter=0)
    assert not got.converged

def test_constant_predictor_and_intercept_not_penalized():
    x,y,_=fixture();x=np.c_[x,np.full(len(x),5.)]
    got=s.fit_preserved_ridge(x,y,tol=1e-9)
    assert got.converged
    assert abs(got.coef[-1])<1e-9

def test_prediction_data_do_not_change_training_scaler():
    x,y,_=fixture();got=s.fit_preserved_ridge(x,y)
    before=got.mean.copy();got.predict_proba(x+10000)
    assert np.array_equal(got.mean,before)

def test_different_start_reaches_same_predictions():
    x,y,_=fixture()
    a=s.fit_preserved_ridge(x,y,start='zero',tol=1e-9)
    b=s.fit_preserved_ridge(x,y,start='fixed',tol=1e-9)
    assert a.converged and b.converged
    assert np.max(np.abs(a.predict_proba(x)-b.predict_proba(x)))<1e-6

@pytest.mark.parametrize('bad', ['nan','one_class'])
def test_invalid_input_rejected(bad):
    x,y,_=fixture()
    if bad=='nan':x[0,0]=np.nan
    else:y[:]=1
    with pytest.raises(ValueError):s.fit_preserved_ridge(x,y)
