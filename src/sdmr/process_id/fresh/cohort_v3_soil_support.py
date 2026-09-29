"""Deterministic final-cohort selection after frozen SoilGrids support eligibility."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

PROGRAM="sdmr-fresh-empirical-v3-soil-support-eligibility"
EXPECTED_CANDIDATES=80
EXPECTED_FINAL=50
EXPECTED_SOIL=(
    "sg_phh2o_0_5",
    "sg_clay_0_5",
    "sg_soc_0_5",
    "sg_nitrogen_0_5",
)

def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_contract(path):
    c=json.loads(Path(path).read_text())
    if c.get("program")!=PROGRAM:
        raise ValueError("wrong v3 soil-support program")
    roster=c["candidate_roster"]
    if int(roster["exact_candidates"])!=EXPECTED_CANDIDATES:
        raise ValueError("candidate denominator changed")
    if int(roster["final_taxa"])!=EXPECTED_FINAL:
        raise ValueError("final denominator changed")
    gate=c["soil_support_gate"]
    if tuple(gate["predictors"])!=EXPECTED_SOIL:
        raise ValueError("SoilGrids support predictor set changed")
    if gate.get("persisted_information")!="finite_or_missing_bit_only":
        raise ValueError("soil eligibility may persist only support bits")
    if gate.get("raw_numeric_soil_values_persisted") is not False:
        raise ValueError("raw numeric soil values became persistable")
    if gate.get("answer_check_soil_support_read") is not False:
        raise ValueError("answer-check soil support became readable")
    mp=gate["model_pool_gate"]; bg=gate["background_300km_gate"]
    if float(mp["minimum_joint_finite_fraction"])!=0.80:
        raise ValueError("model-pool finite fraction changed")
    if int(mp["minimum_joint_finite_rows"])!=50:
        raise ValueError("model-pool row gate changed")
    if int(bg["minimum_joint_finite_rows"])!=4000 or int(bg["denominator_rows"])!=5000:
        raise ValueError("background support gate changed")
    final=c["final_selection"]
    if int(final["minimum_support_eligible_candidates"])!=EXPECTED_FINAL:
        raise ValueError("minimum eligible count changed")
    for key in ("replacement_after_final_selection","threshold_relaxation","predictor_deletion"):
        if final.get(key) is not False:
            raise ValueError(f"fail-closed final-selection rule changed: {key}")
    return c

def select_final(candidate_path, support_path, contract_path):
    c=validate_contract(contract_path)
    cand=pd.read_csv(candidate_path)
    support=pd.read_csv(support_path)
    required_c={
        "candidate_rank","scientific_name","family","genus","selection_hash"
    }
    required_s={
        "scientific_name",
        "model_pool_rows",
        "model_pool_joint_finite_rows",
        "model_pool_joint_finite_fraction",
        "background_300km_rows",
        "background_300km_joint_finite_rows",
        "answer_check_support_read",
        "numeric_soil_values_persisted",
    }
    if required_c-set(cand.columns):
        raise ValueError("candidate roster missing columns")
    if required_s-set(support.columns):
        raise ValueError("support audit missing columns")
    if len(cand)!=EXPECTED_CANDIDATES or cand["scientific_name"].astype(str).nunique()!=EXPECTED_CANDIDATES:
        raise ValueError("candidate roster must be exactly 80 unique taxa")
    ranks=sorted(pd.to_numeric(cand["candidate_rank"],errors="raise").astype(int))
    if ranks!=list(range(1,EXPECTED_CANDIDATES+1)):
        raise ValueError("candidate ranks must be 1..80")
    if support["scientific_name"].astype(str).nunique()!=EXPECTED_CANDIDATES or len(support)!=EXPECTED_CANDIDATES:
        raise ValueError("support audit must cover all 80 candidates exactly once")
    if support["answer_check_support_read"].astype(bool).any():
        raise ValueError("answer-check support was read")
    if support["numeric_soil_values_persisted"].astype(bool).any():
        raise ValueError("numeric soil values were persisted")

    mp=c["soil_support_gate"]["model_pool_gate"]
    bg=c["soil_support_gate"]["background_300km_gate"]
    joined=cand.merge(support,on="scientific_name",how="left",validate="one_to_one")
    joined["soil_support_eligible"]=(
        (pd.to_numeric(joined["model_pool_joint_finite_fraction"],errors="raise")>=float(mp["minimum_joint_finite_fraction"]))
        & (pd.to_numeric(joined["model_pool_joint_finite_rows"],errors="raise")>=int(mp["minimum_joint_finite_rows"]))
        & (pd.to_numeric(joined["background_300km_rows"],errors="raise")==int(bg["denominator_rows"]))
        & (pd.to_numeric(joined["background_300km_joint_finite_rows"],errors="raise")>=int(bg["minimum_joint_finite_rows"]))
    )
    eligible=joined.loc[joined["soil_support_eligible"]].sort_values(
        ["candidate_rank","scientific_name"],kind="mergesort"
    )
    if len(eligible)<EXPECTED_FINAL:
        return joined,pd.DataFrame(),{
            "program":PROGRAM,
            "status":"terminal_unavailable_before_final_cohort_freeze",
            "candidate_count":EXPECTED_CANDIDATES,
            "support_eligible_count":int(len(eligible)),
            "final_selected_count":0,
            "numeric_soil_values_persisted":False,
            "answer_check_support_read":False,
            "model_fitting_performed":False,
        }
    final=eligible.head(EXPECTED_FINAL).copy()
    final.insert(0,"selection_rank",range(1,EXPECTED_FINAL+1))
    if final["genus"].astype(str).value_counts().max()>int(c["candidate_roster"]["breadth_constraints"]["maximum_per_genus"]):
        raise RuntimeError("genus cap violated in final cohort")
    if final["family"].astype(str).value_counts().max()>int(c["candidate_roster"]["breadth_constraints"]["maximum_per_family"]):
        raise RuntimeError("family cap violated in final cohort")
    return joined,final,{
        "program":PROGRAM,
        "status":"final_50_frozen_after_soil_support_eligibility",
        "candidate_count":EXPECTED_CANDIDATES,
        "support_eligible_count":int(len(eligible)),
        "final_selected_count":EXPECTED_FINAL,
        "numeric_soil_values_persisted":False,
        "answer_check_support_read":False,
        "model_fitting_performed":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--contract",required=True)
    p.add_argument("--candidates",required=True)
    p.add_argument("--support-audit",required=True)
    p.add_argument("--output-dir",required=True)
    args=p.parse_args()
    audit,final,result=select_final(args.candidates,args.support_audit,args.contract)
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    audit.to_csv(out/"candidate_soil_support_audit.csv",index=False)
    if len(final):
        final.to_csv(out/"selected_fresh_taxa_v3.csv",index=False)
        result["selected_manifest_sha256"]=_sha256(out/"selected_fresh_taxa_v3.csv")
    (out/"selection_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
