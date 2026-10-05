import csv
import json
import math
from pathlib import Path


CFG=Path("configs/sdmr_fresh_empirical_v4_all46_support.json")
EX=Path("configs/sdmr_fresh_empirical_v4_exclusion_manifest.csv")


def test_v4_exclusion_manifest_is_exact_214_unique_taxa():
    with EX.open(encoding="utf-8",newline="") as fh:
        rows=list(csv.DictReader(fh))
    assert len(rows)==214
    assert len({r["scientific_name"] for r in rows})==214
    assert all(r["scientific_name"].strip() for r in rows)


def test_v4_design_freezes_90_to_50_all46_support_order():
    c=json.loads(CFG.read_text(encoding="utf-8"))
    assert c["status"]=="design_frozen_before_v4_candidate_selection"
    assert c["candidate_roster"]["exact_candidates"]==90
    assert c["all46_support_eligibility"]["predictor_count"]==46
    assert c["all46_support_eligibility"]["final_taxa"]==50
    assert c["all46_support_eligibility"]["final_selection"]=="first_50_eligible_in_frozen_candidate_order"
    assert c["all46_support_eligibility"]["persist_numeric_environmental_values"] is False
    assert c["all46_support_eligibility"]["answer_check_support_read"] is False


def test_v4_keeps_complete_case_support_thresholds_unchanged():
    c=json.loads(CFG.read_text(encoding="utf-8"))
    g=c["all46_support_eligibility"]["gate"]
    assert g["model_pool_minimum_joint_usable_fraction"]==0.80
    assert g["model_pool_minimum_joint_usable_rows"]==50
    assert g["background_denominator_rows"]==5000
    assert g["background_minimum_joint_usable_rows"]==4000


def test_v4_structural_support_rules_are_exactly_six():
    c=json.loads(CFG.read_text(encoding="utf-8"))
    rules=c["all46_support_eligibility"]["structural_decoding_rules"]
    assert [r["predictor"] for r in rules]==[
        "fcf","swe","fgd","lgd","gdgfgd5","gdgfgd10"
    ]


def test_v4_planning_probability_is_conservative_and_not_a_gate():
    c=json.loads(CFG.read_text(encoding="utf-8"))
    p=c["planning"]
    assert p["conservative_support_eligibility_probability"]==0.65
    assert abs(p["probability_at_least_50_eligible_with_90_candidates"]-0.9751830563334861)<1e-12
    assert p["role"]=="denominator_planning_only_not_gate_calibration"
