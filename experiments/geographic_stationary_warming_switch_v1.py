"""Exact + sorted-exposure climate-pressure switches under fixed hypothetical response.

This is a conditional model applied to authentic CHELSA environmental cells.
It neither fits biological parameters nor uses GBIF occurrences. A pressure
component is a modelled *negative log-fitness penalty*, NOT field limitation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq

EXPECTED_SOURCE_SHA256="4b7d5bb9a23e3ef6c4c74448698409be4174d9199765d3ba7bd4eb4f9eddb633"
T_OPT=9.0
P_OPT=900.0
T_SCALE=3.0
P_SCALE=250.0
DELTAS=(0.0,1.0,2.0,3.0,4.0,5.0,6.0)
REQUIRED=("region","taxon","cell_id","temperature","moisture")


def validate(frame:pd.DataFrame,source_sha256:str)->pd.DataFrame:
    if source_sha256!=EXPECTED_SOURCE_SHA256:
        raise ValueError("Source bytes SHA mismatch; do not use reparsed or incomplete climate")
    if set(REQUIRED)-set(frame.columns):raise ValueError("Missing climate-only source columns")
    x=frame[list(REQUIRED)].sort_values(["region","cell_id"],kind="mergesort").reset_index(drop=True)
    if x.duplicated(["region","cell_id"]).any():raise ValueError("Duplicated source climate cells")
    if not np.isfinite(x[["temperature","moisture"]].to_numpy(float)).all():raise ValueError("Nonfinite climate")
    if len(x)!=571 or x.region.nunique()!=10:raise ValueError("Fixed 10-window/571-cell source denominator incomplete")
    if any(x.groupby("region").taxon.nunique()!=1):raise ValueError("Region taxon inconsistent")
    return x


def penalty_parts(temp:np.ndarray,precip:np.ndarray,warming:float,*,habitat_sorted:bool=False)->tuple[float,float]:
    t=((np.asarray(temp,dtype=float)+warming-T_OPT)/T_SCALE)**2
    p=((np.asarray(precip,dtype=float)-P_OPT)/P_SCALE)**2
    if habitat_sorted:
        logits=-t-p
        weights=np.exp(logits-np.max(logits));weights/=weights.sum()
    else:
        weights=np.ones(len(t),dtype=float)/len(t)
    return float(weights@t),float(weights@p)


def exact_crossings(temp:np.ndarray,precip:np.ndarray,max_warming:float=6)->list[float]:
    # E[(T+delta-T*)^2]/sT^2 - E[(P-P*)^2]/sP^2 = 0.
    x=np.asarray(temp,dtype=float)-T_OPT
    water=float(np.mean(((np.asarray(precip,dtype=float)-P_OPT)/P_SCALE)**2))
    a=1.;b=2*float(np.mean(x));c=float(np.mean(x*x))-T_SCALE*T_SCALE*water
    roots=np.roots([a,b,c]);out=[]
    for z in roots:
        if abs(z.imag)>1e-9 or not 0<z.real<max_warming:continue
        d=float(z.real)
        eps=min(1e-4,d/2,(max_warming-d)/2)
        before=penalty_parts(temp,precip,d-eps)
        after=penalty_parts(temp,precip,d+eps)
        if (before[0]-before[1])*(after[0]-after[1])<0:out.append(d)
    return sorted(out)


def sorted_crossings(temp:np.ndarray,precip:np.ndarray,max_warming:float=6)->list[float]:
    def d(v):
        a,b=penalty_parts(temp,precip,v,habitat_sorted=True)
        return a-b
    # Explicit numerical bracket grid; a hypothetical sorted state, not measured occupancy.
    grid=np.linspace(0,max_warming,601)
    v=np.array([d(x) for x in grid])
    roots=[]
    for lo,hi,a,b in zip(grid[:-1],grid[1:],v[:-1],v[1:]):
        if a*b<0:
            root=float(brentq(d,float(lo),float(hi),xtol=1e-12))
            roots.append(root)
    return roots


def classify(t:float,p:float)->str:
    return "temperature" if t>p+1e-12 else "moisture" if p>t+1e-12 else "tie"


def analyze(frame:pd.DataFrame,source_sha256:str)->dict:
    x=validate(frame,source_sha256)
    regions=[]
    for name,g in x.groupby("region",sort=True):
        temp=g.temperature.to_numpy(float); rain=g.moisture.to_numpy(float)
        empirical=[];sorted_hypothetical=[]
        for delta in DELTAS:
            t,p=penalty_parts(temp,rain,delta)
            empirical.append({"warming_c":delta,"temperature_penalty":t,"moisture_penalty":p,"dominant_pressure":classify(t,p)})
            t,p=penalty_parts(temp,rain,delta,habitat_sorted=True)
            sorted_hypothetical.append({"warming_c":delta,"temperature_penalty":t,"moisture_penalty":p,"dominant_pressure":classify(t,p)})
        regions.append({"taxon_label_for_source":str(g.taxon.iloc[0]),"region":str(name),
                        "n_equal_area_climate_cells":len(g),
                        "source_temperature_mean_c":float(np.mean(temp)),
                        "source_precipitation_mean_mm":float(np.mean(rain)),
                        "equal_area":empirical,"hypothetically_habitat_sorted":sorted_hypothetical,
                        "exact_equal_area_crossings_between_0_and_6_c":exact_crossings(temp,rain),
                        "numeric_habitat_sorted_crossings_between_0_and_6_c":sorted_crossings(temp,rain)})
    return {"study":"geographic_stationary_warming_switch_v1",
            "empirical_fitness_or_causal_claim_allowed":False,"source_sha256":source_sha256,
            "n_fixed_regions":len(regions),"n_fixed_cells":len(x),
            "stationary_hypothetical_parameters":{"thermal_optimum_c":T_OPT,"precipitation_optimum_mm":P_OPT,
                                                 "thermal_scale_c":T_SCALE,"precipitation_scale_mm":P_SCALE,
                                                 "thermal_water_weight_ratio":1.0,"shape":"quadratic"},
            "external_perturbation":"uniform_additive_temperature_only_0_to_6_c_not_a_climate_projection",
            "note":"One shared illustrative response across all regions; does not infer actual survival, growth or species physiological limits",
            "regions":regions}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); b=a.source.read_bytes()
    result=analyze(pd.read_csv(a.source),hashlib.sha256(b).hexdigest())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for r in result["regions"]:
        print(r["region"],"roots_equal_area",[round(x,3) for x in r["exact_equal_area_crossings_between_0_and_6_c"]],
              "roots_sorted",[round(x,3) for x in r["numeric_habitat_sorted_crossings_between_0_and_6_c"]])

if __name__=="__main__":main()
