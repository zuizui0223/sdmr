#!/usr/bin/env python3
"""Diagnostic solver preserving the ORIGINAL raw-feature L2 objective.

Optimizes mean weighted logistic loss + ||beta||^2/(2*C*sum(weight)),
using train-only standardized coordinates theta_j=scale_j*beta_j.
The penalty is theta_j^2/scale_j^2, not isotropic L2 in theta.
No historical scores, scientific state rules, or holdouts are changed.
"""
from __future__ import annotations
from dataclasses import dataclass
import warnings
import numpy as np
from scipy.linalg import solve, LinAlgWarning
from scipy.special import expit
from sklearn.preprocessing import StandardScaler


def objective_derivatives(theta, z, y, sample_weight, penalty_diag, *, C=1.):
    """Return scalar objective, analytic gradient, and positive Hessian."""
    theta=np.asarray(theta,float);z=np.asarray(z,float);y=np.asarray(y,float)
    sw=np.asarray(sample_weight,float);d=np.asarray(penalty_diag,float)
    mass=float(sw.sum());weights=sw/mass
    eta=z@theta[:-1]+theta[-1]
    loss=np.logaddexp(0.,np.where(y==1.,-eta,eta))
    reg=d/(C*mass)
    value=float(weights@loss+.5*np.dot(reg,theta[:-1]**2))
    residual=np.where(y==1.,-expit(-eta),expit(eta))*weights
    gradient=np.r_[z.T@residual+reg*theta[:-1],residual.sum()]
    curvature=weights*expit(eta)*expit(-eta)
    hessian=np.empty((len(theta),len(theta)))
    hessian[:-1,:-1]=z.T@(curvature[:,None]*z)+np.diag(reg)
    hessian[:-1,-1]=z.T@curvature
    hessian[-1,:-1]=hessian[:-1,-1]
    hessian[-1,-1]=curvature.sum()
    return value,gradient,hessian


@dataclass
class RidgeFit:
    theta: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    converged: bool
    iterations: int
    objective: float
    gradient_inf: float
    newton_decrement: float
    reason: str

    @property
    def coef(self):return self.theta[:-1]/self.scale

    @property
    def intercept(self):return float(self.theta[-1]-self.mean@self.coef)

    def predict_proba(self,x):
        x=np.asarray(x,float)
        if x.ndim!=2 or x.shape[1]!=len(self.scale) or not np.isfinite(x).all():
            raise ValueError('prediction features must be finite with matching dimension')
        return expit(((x-self.mean)/self.scale)@self.theta[:-1]+self.theta[-1])


def fit_preserved_ridge(x,y,*,C=1.,max_iter=100,tol=1e-9,start='zero'):
    """Newton/Armijo fit; failed convergence is explicit and never called valid."""
    x=np.asarray(x,float);y=np.asarray(y,int)
    if x.ndim!=2 or y.shape!=(len(x),) or len(x)<2 or not np.isfinite(x).all():
        raise ValueError('finite 2-D training matrix and aligned binary labels required')
    if set(np.unique(y))!={0,1}:raise ValueError('both label classes required')
    if not np.isfinite(C) or C<=0 or tol<=0 or max_iter<0:raise ValueError('invalid solver settings')
    n=len(y);sw=np.where(y==1,n/(2.*y.sum()),n/(2.*(n-y.sum())))
    scaler=StandardScaler().fit(x)
    z=scaler.transform(x)
    d=1./scaler.scale_**2
    t=np.zeros(x.shape[1]+1)
    if start=='fixed':t=np.linspace(-.05,.05,len(t))
    elif start!='zero':raise ValueError('start must be zero or fixed')
    converged=False;reason='iteration_limit';decrement=float('inf')
    for iteration in range(max_iter+1):
        value,g,h=objective_derivatives(t,z,y,sw,d,C=C)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',LinAlgWarning)
                step=solve(h,g,assume_a='pos',check_finite=True)
        except (np.linalg.LinAlgError,LinAlgWarning):
            reason='ill_conditioned_hessian';break
        decrement=float(np.sqrt(max(0.,g@step)))
        if np.max(np.abs(g))<=tol and decrement<=1e-9:
            converged=True;reason='gradient_and_newton_decrement';break
        if iteration==max_iter:break
        directional=float(g@step)
        if directional<=0 or not np.isfinite(directional):reason='non_descent_direction';break
        rate=1.
        for _ in range(45):
            trial=t-rate*step
            trialvalue,_,_=objective_derivatives(trial,z,y,sw,d,C=C)
            if trialvalue<=value-1e-4*rate*directional+5e-16:
                t=trial;break
            rate*=.5
        else:
            reason='line_search_failed';break
    value,g,_=objective_derivatives(t,z,y,sw,d,C=C)
    return RidgeFit(t,scaler.mean_.copy(),scaler.scale_.copy(),converged,iteration,
                    value,float(np.max(np.abs(g))),decrement,reason)
