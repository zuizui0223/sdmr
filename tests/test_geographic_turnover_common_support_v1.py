"""Outcome-blind preflight selection tests against controlled environmental cells."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location("matchscan",ROOT/"experiments/geographic_turnover_common_support_v1.py")
mod=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
CFG=json.loads((ROOT/"configs/geographic_turnover_common_support_v1.json").read_text())


def _stub_grid(w,cell_km):
    n=42
    i=np.arange(n)
    return pd.DataFrame({"region":w["region"],"cell_id":[str(k) for k in i],
                         "spatial_block":(i%4).astype(str),"longitude":w["west"]+0.3+i*0.005,
                         "latitude":w["south"]+0.3+i*0.005})


def _stub_raster(points,layers,**kwargs):
    x=points.copy();i=np.arange(len(x))
    name=x.region.iloc[0]
    if name.endswith("FI_SW"):
        t=-1.5
    else:
        t=0
    x["temperature"]=8.0+t + np.sin(i/9)
    x["moisture"]=800.0+70*np.cos(i/10)
    return x,pd.DataFrame([{"predictor":v.predictor,"source":"stub"} for v in layers])


def test_all_candidates_and_failure_denominator_preserved():
    r,cells=mod.assemble(CFG,grid_builder=_stub_grid,extractor=_stub_raster)
    assert r["n_declared_windows"]==10
    assert r["n_pairs"]==20
    assert len(cells)==420
    assert len(r["source_windows"])==10
    assert all(x["uses_gbif_occurrences"] is False for x in r["source_windows"])
    assert r["selection_uses_occurrence_or_effort"] is False


def test_selection_ignores_all_observation_fields():
    r,c=mod.assemble(CFG,grid_builder=_stub_grid,extractor=_stub_raster)
    statuses={x["region"]:x["status"] for x in r["source_windows"]}
    first=mod.evaluate_pairs(c,CFG,region_status=statuses)
    altered=c.sample(frac=1,random_state=41).copy()
    altered["n_occ"]=np.arange(len(altered))*2
    altered["effort"]=np.arange(len(altered))+1
    assert mod.evaluate_pairs(altered,CFG,region_status=statuses)==first


def test_failed_source_is_not_zero_imputed_or_replaced():
    def broken(points,layers,**kwargs):
        if points.region.iloc[0]=="quercus_DE_SW":
            raise OSError("source missing")
        return _stub_raster(points,layers,**kwargs)
    out,c=mod.assemble(CFG,grid_builder=_stub_grid,extractor=broken)
    assert len(out["source_windows"])==10
    assert any(x["status"]=="climate_unavailable" for x in out["source_windows"])
    assert len(c)==42*9
    impacted=[x for x in out["candidates"] if x["region_a"]=="quercus_DE_SW" or x["region_b"]=="quercus_DE_SW"]
    assert len(impacted)==4
    assert all(not x["eligible"] and x["reasons"] for x in impacted)


def test_invalid_design_fails():
    x=copy.deepcopy(CFG);x["study_status"]="postoutcome"
    with pytest.raises(ValueError,match="contract"):mod.validate_design(x)
    x=copy.deepcopy(CFG);x["candidate_windows"][0]["region"]=x["candidate_windows"][1]["region"]
    with pytest.raises(ValueError,match="unique"):mod.validate_design(x)


def test_exact_environment_matching_controls():
    a=pd.DataFrame({"temperature":np.linspace(2,9,40),"moisture":np.linspace(700,900,40)})
    b=a.copy()
    assert mod._pooled_bins(a,b,bins=6)==pytest.approx(1.0)
    assert mod._nn_coverage(a,b,0.5)["minimum"]==pytest.approx(1.0)
    shifted=b.copy();shifted["temperature"]+=100
    assert mod._pooled_bins(a,shifted,bins=6)==pytest.approx(0)
    assert mod._nn_coverage(a,shifted,0.5)["minimum"]==pytest.approx(0)


def test_geography_gate_rejects_same_window_pair():
    r,c=mod.assemble(CFG,grid_builder=_stub_grid,extractor=_stub_raster)
    # All equal-area cells represent declared regions, not taxon-fitted M.
    assert all("n_available_cells_a" in z and "reasons" in z for z in r["candidates"])
    assert all(z["region_a"]!=z["region_b"] for z in r["candidates"])
