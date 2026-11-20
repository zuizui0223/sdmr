"""New one-forest post-HF453-outcome confounding tests; synthetic only."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
from pathlib import Path
import importlib.util
import json
import math
import sys

import pytest

sys.path.insert(0,str(Path("scripts").resolve()))
source=Path("scripts/hf453_prior_species_size_confounding_postoutcome_v1.py")
spec=importlib.util.spec_from_file_location("hf453_prior_covariate_exploration",source)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def contract():
    return json.loads(
        Path("configs/hf453_prior_species_size_postoutcome_v1.json").read_text()
    )


def test_frozen_design_disallows_y_driven_adjustment_changes(contract):
    mod.validate_config(contract)
    mutant=deepcopy(contract)
    mutant["source_HF453"]["expected_known_dead_next"]=460
    with pytest.raises(ValueError,match="original_source_or_first_response"):
        mod.validate_config(mutant)
    mutant=deepcopy(contract)
    mutant["primary_information_test"]["n_splits"]=4
    with pytest.raises(ValueError,match="learner_or_parent"):
        mod.validate_config(mutant)
    mutant=deepcopy(contract)
    mutant["secondary_stratification"]["primary_min_n_per_CP_in_each_stratum"]=1
    with pytest.raises(ValueError,match="overlap_or_strata"):
        mod.validate_config(mutant)
    mutant=deepcopy(contract)
    mutant["status"]["next_unresolved"]=[]
    with pytest.raises(ValueError,match="original_status_or_CP"):
        mod.validate_config(mutant)


def test_fixed_prior_dbh_bins_use_centimeters():
    assert mod.size_bin(9.99)=="small"
    assert mod.size_bin(10)=="medium"
    assert mod.size_bin(20)=="large"
    assert mod.size_bin(39.99)=="large"
    assert mod.size_bin(40)=="very_large"
    for v in (0,-1,float("nan"),float("inf")):
        with pytest.raises(ValueError):
            mod.size_bin(v)


def test_HF253_source_field_grammar_misses_without_imputation():
    csv=StringIO(
        "stem.tag,stem.id,tree.id,sp,dbh,df.status,gx\n"
        "T1,S1,P1,acrrub,8.1,dead,10\n"
        "T2,S2,P1,querc,NA,alive,11\n"
        "T3,S3,P2,NA,20.0,alive,12\n"
        "T4,S4,P3,pinstro,40.5,prior,13\n"
    )
    panel,meta=mod.read_HF253_prior(csv,expected_rows=4)
    assert len(panel)==4 and meta["original_rows"]==4
    assert panel["T1"]["dbh"]==8.1
    assert panel["T2"]["dbh"] is None
    assert panel["T3"]["sp"] is None
    assert panel["T4"]["dbh"]==40.5
    assert meta["source_missing_species_rows"]==1
    assert meta["source_missing_diameter_rows"]==1
    assert meta["original_2019_status_and_spatial_fields_never_used"]
    assert panel["T1"]["parent"]==panel["T2"]["parent"]


def test_HF253_biological_source_status_column_not_accessed():
    x=(
        "stem.tag,stem.id,tree.id,sp,dbh,df.status,gx\n"
        "T1,S1,P1,acrrub,8.1,dead,10\n"
    )
    y=x.replace("dead,10","alive,999")
    assert mod.read_HF253_prior(StringIO(x),expected_rows=1)==(
        mod.read_HF253_prior(StringIO(y),expected_rows=1)
    )


def test_HF453_only_prior_cp_and_2022_status_not_future_cp():
    a=(
        "StemTag,year,status,CP,health_notes\n"
        "T1,2021,AU,1,foo\nT1,2022,DC,5,bar\n"
        "T1,2023,DS,NA,z\nT1,2024,DS,NA,z\n"
        "T2,2021,A,4,foo\nT2,2022,DN,1,bar\n"
        "T2,2023,DS,NA,z\nT2,2024,DS,NA,z\n"
    )
    x=mod.read_HF453_first_interval(StringIO(a),expected_stems=2)
    assert x["T1"]=={"2021":("AU","1"),"2022":("DC","")}
    assert x["T2"]=={"2021":("A","4"),"2022":("DN","")}
    b=a.replace("2022,DC,5","2022,DC,2").replace("2022,DN,1","2022,DN,5")
    assert mod.read_HF453_first_interval(StringIO(b),expected_stems=2)==x


def test_strata_partial_identification_excludes_nonoverlap_explicitly():
    sample=[]
    for cp,labels in ((0,["p"]*4+["z"]*5+["m"]),
                      (1,["p"]+["z"]*8+["m"])):
        for response in labels:
            sample.append({"sp":"sp1","size_bin":"large",
                           "prior_unhealthy":0,"cp_more":cp,
                           "response":response})
    for response in ["z"]*5:
        sample.append({"sp":"only_one_CP","size_bin":"small",
                       "prior_unhealthy":1,"cp_more":0,"response":response})
    x=mod.sharp_stratified_standardization(sample,10)
    assert x["n_in_strata_with_both_CP_groups_eligible"]==20
    assert x["n_excluded_from_fixed_overlap"]==5
    assert x["n_included_strata"]==1
    assert x["n_excluded_strata"]==1
    assert x["lower"]=="-2/5"
    assert x["upper"]=="-1/5"
    assert x["sign"]=="negative_for_all_unknown_outcomes"
    assert x["not_a_statistical_confidence_interval"]
    assert x["not_full_HF453_cohort_estimate"]


def test_parent_grouped_OOF_preserves_parent_and_score_denominator():
    # 150 distinct parents, with two differently tagged stems each.
    # The binary outcome is a synthetic CP-related variable, not a field claim.
    data=[]
    for tree in range(150):
        for stem in range(2):
            cp=(tree+stem)%3==0
            y= "p" if (cp and tree%3==0) or tree%17==0 else "z"
            data.append({
                "tag":f"T{tree:04d}_{stem}",
                "parent":f"P{tree:04d}",
                "sp":["sp1","sp2","sp3"][tree%3],
                "dbh":float(8+tree%40),
                "logdb":math.log1p(8+tree%40),
                "size_bin":"medium",
                "prior_unhealthy":int(tree%5==0),
                "cp_more":int(cp),
                "response":y,
            })
    output=mod.evaluate_parent_group_cv(data,n_splits=5)
    assert output["status"]=="postoutcome_parent_grouped_OOF_description_only"
    assert output["n_original_scored_stem_events"]==300
    assert output["n_distinct_test_parent_trees"]==150
    assert output["n_folds"]==5
    assert sum(f["n_scored_parent_trees"] for f in output["fold_reports"])==150
    assert sum(f["n_scored_stems"] for f in output["fold_reports"])==300
    assert all(f["n_training_parent_tree_overlap"]==0 for f in output["fold_reports"])
    assert math.isfinite(output["delta_logloss_baseline_minus_plus_CP"])
    assert output["learner_agreement_or_increment_not_causal_process_identity"]
    assert output["no_biome_or_geographic_transfer_claim"]


def test_preflight_is_source_free_and_exact_lock_required(contract,tmp_path,monkeypatch):
    def impossible(_):
        raise AssertionError("preflight cannot download or open biological data")
    monkeypatch.setattr(mod,"run_exploration",impossible)
    pre=tmp_path/"pre.json"
    monkeypatch.setattr(sys,"argv",["preflight","--preflight-only","--out",str(pre)])
    mod.main()
    r=json.loads(pre.read_text())
    assert r["preflight"] is True
    assert r["result"]["status"]=="source_free_scientific_preflight_only"
    assert r["no_new_independent_ecological_replication"]
    assert r["not_SDMR_productA_M5_repromotion"]
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_TEXT.replace("folds=GroupKFold_5","folds=GroupKFold_3"))
    monkeypatch.setattr(
        sys,"argv",["attempt","--execute-lock",str(bad),
                    "--out",str(tmp_path/"bad.json")]
    )
    with pytest.raises(ValueError,match="scientific_lock_changed"):
        mod.main()
