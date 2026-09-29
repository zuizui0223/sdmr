import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.fresh.cohort_v3_soil_support import select_final, validate_contract

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"configs/sdmr_fresh_empirical_v3_soil_support_eligibility.json"

def _candidate():
    return pd.DataFrame({
        "candidate_rank":range(1,81),
        "scientific_name":[f"Taxon {i}" for i in range(1,81)],
        "family":[f"Family {i//2}" for i in range(1,81)],
        "genus":[f"Genus {i}" for i in range(1,81)],
        "selection_hash":[f"{i:064x}" for i in range(1,81)],
    })

def _support(n_pass=60):
    rows=[]
    for i in range(1,81):
        good=i<=n_pass
        rows.append({
            "scientific_name":f"Taxon {i}",
            "model_pool_rows":100,
            "model_pool_joint_finite_rows":90 if good else 70,
            "model_pool_joint_finite_fraction":0.90 if good else 0.70,
            "background_300km_rows":5000,
            "background_300km_joint_finite_rows":4500 if good else 3500,
            "answer_check_support_read":False,
            "numeric_soil_values_persisted":False,
        })
    return pd.DataFrame(rows)

def test_contract_keeps_soil_support_only_boundary():
    c=validate_contract(CONTRACT)
    assert c["candidate_roster"]["exact_candidates"]==80
    assert c["candidate_roster"]["final_taxa"]==50
    assert c["soil_support_gate"]["persisted_information"]=="finite_or_missing_bit_only"
    assert c["soil_support_gate"]["raw_numeric_soil_values_persisted"] is False
    assert c["soil_support_gate"]["answer_check_soil_support_read"] is False

def test_first_50_support_eligible_are_frozen_in_candidate_order(tmp_path):
    cand=_candidate(); sup=_support(60)
    cp=tmp_path/"c.csv"; sp=tmp_path/"s.csv"
    cand.to_csv(cp,index=False); sup.to_csv(sp,index=False)
    audit,final,result=select_final(cp,sp,CONTRACT)
    assert result["status"]=="final_50_frozen_after_soil_support_eligibility"
    assert final["candidate_rank"].tolist()==list(range(1,51))
    assert audit["soil_support_eligible"].sum()==60

def test_fewer_than_50_passes_is_terminal_unavailable(tmp_path):
    cand=_candidate(); sup=_support(49)
    cp=tmp_path/"c.csv"; sp=tmp_path/"s.csv"
    cand.to_csv(cp,index=False); sup.to_csv(sp,index=False)
    _,final,result=select_final(cp,sp,CONTRACT)
    assert final.empty
    assert result["status"]=="terminal_unavailable_before_final_cohort_freeze"
    assert result["support_eligible_count"]==49

def test_answer_check_or_numeric_soil_leak_fails(tmp_path):
    cand=_candidate(); sup=_support(60)
    sup.loc[0,"answer_check_support_read"]=True
    cp=tmp_path/"c.csv"; sp=tmp_path/"s.csv"
    cand.to_csv(cp,index=False); sup.to_csv(sp,index=False)
    try:
        select_final(cp,sp,CONTRACT)
    except ValueError as exc:
        assert "answer-check support" in str(exc)
    else:
        raise AssertionError("answer-check support leak did not fail")
