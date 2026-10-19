"""Fixed stationary fitness pressure: algebra, invariance, and source integrity."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location("warming",ROOT/"experiments/geographic_stationary_warming_switch_v1.py")
mod=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(mod)
SOURCE=ROOT/"results/geographic_turnover_common_support_v1/all_candidate_climate_cells.csv"

def test_sha_denominator_all_regions():
    b=SOURCE.read_bytes();frame=pd.read_csv(SOURCE)
    result=mod.analyze(frame,hashlib.sha256(b).hexdigest())
    assert result["n_fixed_regions"]==10 and result["n_fixed_cells"]==571
    assert result["empirical_fitness_or_causal_claim_allowed"] is False
    assert all(r["n_equal_area_climate_cells"]>=35 for r in result["regions"])


def test_invariance_to_obs_columns_and_input_permutation():
    df=pd.read_csv(SOURCE);sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    a=mod.analyze(df,sha)
    df=df.sample(frac=1,random_state=24).copy();df["GBIF_records"]=-1;df["observation_effort"]=999
    assert a==mod.analyze(df,sha)


def test_exact_equal_area_roots_and_numerical_crossing():
    temp=np.array([7.0,8.0,9.0,10.0]);rain=np.array([860,920,900,880]);
    roots=mod.exact_crossings(temp,rain,max_warming=6)
    for root in roots:
        t,w=mod.penalty_parts(temp,rain,root)
        assert t==pytest.approx(w,abs=1e-10)
        da=np.subtract(*mod.penalty_parts(temp,rain,root-0.001))
        db=np.subtract(*mod.penalty_parts(temp,rain,root+0.001))
        assert da*db<0


def test_habitat_sorted_not_actual_GBIF():
    df=pd.read_csv(SOURCE);result=mod.analyze(df,hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    assert any(r["numeric_habitat_sorted_crossings_between_0_and_6_c"] for r in result["regions"])
    for r in result["regions"]:
        assert len(r["equal_area"])==7 and len(r["hypothetically_habitat_sorted"])==7
        assert all(x["temperature_penalty"]>=0 and x["moisture_penalty"]>=0 for x in r["equal_area"])


def test_wrong_source_fails():
    df=pd.read_csv(SOURCE)
    with pytest.raises(ValueError,match="SHA mismatch"):
        mod.analyze(df,"NOT_SHA")
    good=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match="incomplete"):
        mod.analyze(df.iloc[:200],good)


def test_result_snapshot_exact():
    df=pd.read_csv(SOURCE)
    actual=mod.analyze(df,hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    path=ROOT/"results/geographic_stationary_warming_switch_v1.json"
    assert actual==json.loads(path.read_text())
