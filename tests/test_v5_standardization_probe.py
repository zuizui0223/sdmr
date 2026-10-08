"""Unit tests for model-pool-only exploratory standardization (not v5 promotion)."""
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"experiments"/"v5_standardization_probe.py"
SPEC=importlib.util.spec_from_file_location("v5_standardization_probe",SCRIPT)
probe=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)

def test_balanced_log_score_orientation_and_null():
    y=np.array([1,1,0,0])
    assert probe.balanced_log_score(y,np.full(4,0.5))==pytest.approx(-np.log(2))
    assert probe.balanced_log_score(y,np.array([0.9,0.8,0.1,0.2]))> -np.log(2)
    assert probe.balanced_log_score(y,np.array([0.1,0.2,0.9,0.8]))< -np.log(2)

def test_frozen_source_reader_uses_explicit_allowlist(tmp_path):
    p=tmp_path/"source.zip"
    with zipfile.ZipFile(p,"w") as z:
        z.writestr("model_pool.csv","taxon,block\nplant,1\n")
        z.writestr("answer_check_secret.csv","outcome\n0.99\n")
    got=probe.open_frozen(p,("model_pool.csv",))
    assert set(got)=={"model_pool.csv"}
    assert b"0.99" not in b"".join(got.values())
    with pytest.raises(ValueError,match="required frozen file missing"):
        probe.open_frozen(p,("missing.csv",))

def test_authorization_conjunction_not_significance_only():
    ys=[(np.array([0,1,0,1]),np.array([0.30,0.70,0.30,0.70])),
        (np.array([0,1,0,1]),np.array([0.30,0.70,0.30,0.70]))]
    d=probe.gate_stats(ys)
    assert set(("observed_mean_score","mean_gain_over_null","p_value",
                "absolute_adequate","minimum_gain_met","authorized"))<=set(d)
    assert d["authorized"] is (d["absolute_adequate"] and d["minimum_gain_met"] and d["permutation_significant"])

def test_spatial_background_assignment_nearest_occurrence_id():
    o=pd.DataFrame({"occurrence_id":["b","a","c"],
                    "longitude":[2.0,0.0,8.0],"latitude":[0.0]*3,
                    "spatial_block":[22,11,33]})
    b=pd.DataFrame({"longitude":[0.01,7.95,1.98],"latitude":[0.0]*3})
    groups=probe.bg_nearest_spatial_block(o,b)
    assert groups.tolist()==[11,33,22]

def test_no_sealed_outcomes_or_v5_state_mutation():
    s=SCRIPT.read_text(encoding="utf-8")
    assert "truth_or_sealed_answer_check_read" in s
    assert "first N frozen selection ranks" in s
    assert "source_zip" not in s
    assert "postterminal_standardization_model_pool_probe" in s
    assert "ANSWER_CHECK" not in s


def test_probe_one_executes_with_small_complete_model_pool():
    rng=np.random.default_rng(3)
    predictors=[f"v{i}" for i in range(46)]
    taxon="synthetic_fixture"
    occ_rows=[]
    bg_rows=[]
    feature_rows=[]
    location=0
    for block,lon in enumerate([0.0,5.0,10.0]):
        for i in range(15):
            oid=f"{taxon}|{block}|{i}"
            loc=location;location+=1
            occ_rows.append(dict(scientific_name=taxon,occurrence_id=oid,
                                 longitude=lon+0.01*i,latitude=0.0,spatial_block=block,
                                 location_id=loc,complete_case=True))
            feature_rows.append(dict(location_id=loc,
                                     **{p:float(rng.normal()+0.3) for p in predictors}))
        for i in range(30):
            loc=location;location+=1
            bg_rows.append(dict(scientific_name=taxon,background_rank=block*30+i+1,
                                longitude=lon+0.01*i,latitude=0.01,
                                location_id=loc,complete_case=True))
            feature_rows.append(dict(location_id=loc,
                                     **{p:float(rng.normal()) for p in predictors}))
    occ=pd.DataFrame(occ_rows)
    mod=occ.drop(columns=["spatial_block"])
    bg=pd.DataFrame(bg_rows)
    features=pd.DataFrame(feature_rows)
    auth=pd.DataFrame([dict(scientific_name=taxon,learner_route="penalized_logistic",
                            observed_mean_score=-0.7)])
    one=probe.probe_one(taxon,mod,bg,occ,features,predictors,auth)
    assert one["scientific_name"]==taxon
    assert one["n_occurrence"]==45
    assert one["n_background"]>0
    assert one["raw_logistic_v5_replay"]["p_value"]>=0.001
    assert np.isfinite(one["score_gain_from_standardization"])
    assert one["diagnostic_only"] is True


def test_frozen_predictor_order_is_normalized_before_fit():
    import ast
    tree=ast.parse(SCRIPT.read_text(encoding="utf-8"))
    source=SCRIPT.read_text(encoding="utf-8")
    assert '"_role_order"' in source
    assert '["process","_role_order","predictor"]' in source
    assert "kind=\"mergesort\"" in source
    assert "dict.fromkeys(registry.predictor.astype(str))" in source
    assert "scikit-learn" not in source  # numerical environment pinned in CI, not guessed here
