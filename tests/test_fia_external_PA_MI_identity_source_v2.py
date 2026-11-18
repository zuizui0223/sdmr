"""PA/MI v2 first source-only census identity, no NOAA or biological effects."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_external_PA_MI_identity_source_v2 as g
from test_fia_external_PA_MI_first_source_v1 import make_zip,source_panel,source_row


def config():
    return json.loads((ROOT/"configs/fia_PA_MI_identity_only_v2.json").read_text())


def test_v1_original_NOAA_failure_kept_and_new_v2_source_only():
    c=config()
    g.verify_contract(c)
    assert g.ORIGINAL_V1_SOURCE_ONLY_RUN==44236792668
    assert g.ORIGINAL_V1_STOP_ARTIFACT==14397208729
    assert c["old_NOAA_20261006_unavailable_not_replaced"]
    assert g.STATES==("PA","MI")
    assert len(g.SPECIES)==13 and len(g.PRIORITY)==5
    assert c["no_initial_TREE_DIA_STATUSCD_access"]
    assert "temperature_anomaly_c" not in g.COLUMNS
    assert "STATUSCD" not in g.COLUMNS
    assert "DIA" not in g.COLUMNS


def test_identity_contract_cannot_change_states_thresholds_or_prior_stop():
    c=config()
    cases=[
       ("holdout_states",["VA","MI"]),
       ("priority_5",["129"]),
       ("minimum_holdout_state_counties",2),
       ("historical_first_source_stop_run",0),
       ("old_NOAA_20261006_unavailable_not_replaced",False),
       ("original_training_csv_sha256","0"*64),
    ]
    for k,v in cases:
        x=dict(c);x[k]=v
        with pytest.raises(ValueError,match="contract changed"):
            g.verify_contract(x)


def synthetic_plot_meta():
    return {
        "p0":("","42001",(2000,7)),
        "p1":("p0","42001",(2007,7)),
        "p2":("p1","42001",(2014,7)),
        "q0":("","42003",(2000,7)),
        "q1":("q0","42005",(2010,7)),
        "r0":("","42007",(2014,7)),
        "r1":("r0","42007",(2010,7)),
        "s0":("","42009",(1990,7)),
        "s1":("s0","42009",(2026,7)),
    }


def test_source_plot_revisits_require_stable_county_and_forward_time():
    plots=synthetic_plot_meta()
    roots={"p0":"p0","p1":"p0","p2":"p0","q0":"q0","q1":"q0",
           "r0":"r0","r1":"r0","s0":"s0","s1":"s0"}
    eligible,reason=g.collect_candidate_plot_intervals(plots,roots,{"q0"})
    assert set(eligible)=={"p1","p2"}
    assert eligible["p1"][-1]==7*12
    assert reason["n_eligible_source_revisit_intervals_no_climate_join"]==2
    assert reason["unstable_or_unknown_whole_PLOT_chain"]==1
    assert reason["nonforward_or_more_than_21y_revisit"]>=1


def test_tree_prior_visit_species_does_not_read_status_dia(tmp_path):
    raw=make_zip("PA_TREE.csv",("PLT_CN","SPCD","DIA","STATUSCD"),[
        ("p0",129,"BAD DIAMETER VALUE","UNREAD"),
        ("p0",316,"99999","INVALID"),
        ("p1",129,"not numeric","2"),
        ("p2",802,"0","1")])
    zip_path=tmp_path/"PA_TREE.zip";zip_path.write_bytes(raw)
    plots=synthetic_plot_meta()
    roots={k:("p0" if k.startswith("p") else k) for k in plots}
    allowed={"p1":("p0","42001","p0",(2000,7),(2007,7),84),
             "p2":("p1","42001","p0",(2007,7),(2014,7),84)}
    rows,meta=g.first_prior_species_source_rows("PA",allowed,zip_path,"PA_TREE.csv")
    assert len(rows)==3
    assert {x["species_code"] for x in rows}=={"129","316"}
    assert all(x["remeasurement_months"]==84 for x in rows)
    assert meta["TREE_SPCD_PLT_CN_only"]["n_tree_identity_rows_read"]==4
    assert rows[0]["prior_visit_year"]==2000
    assert rows[-1]["current_visit_year"]==2014


def test_full_taxon_denominator_time_only_no_fake_climate_overlap():
    train,holdout=source_panel()
    # Old source panel with 2 observed year-cohorts, both regions supporting.
    for i, row in enumerate(train):
        row["interval_end_year"]=2010 if int(row["county_fips"][2:])%2 else 2015
    identity=[]
    for row in holdout:
        z={**row,
           "prior_visit_year":row["interval_end_year"]-6,
           "prior_visit_month":7,
           "current_visit_year":row["interval_end_year"],
           "current_visit_month":7,
           "remeasurement_months":72}
        identity.append(z)
    # Ensure two distinct holdout 5-year periods with all other eligibility.
    for z in identity:
        if int(z["county_fips"][2:])%2==0:
            z["interval_end_year"]=2015
            z["current_visit_year"]=2015
    out=g.cohort_source_gate(train,identity)
    assert out["source_species_denominator"]==13
    assert out["n_primary_both_holdouts_identity_time_ready"]==1
    assert not out["NOAA_PA_MI_monthly_exposure_available"]
    assert out["n_independent_biological_effect_tests"]==0
    assert out["species"][0]["species_code"]=="68"
    p129=next(x for x in out["species"] if x["species_code"]=="129")
    assert p129["both_holdout_states_identity_time_ready"]
    assert p129["training_VA_WI_shared_five_year_cohorts"]==[4,5]
    assert p129["holdout_states"]["MI"]["n_distinct_plot_chains"]==30


def test_no_species_is_not_biological_zero():
    train,holdout=source_panel()
    data=g.cohort_source_gate(train,[])
    q=next(x for x in data["species"] if x["species_code"]=="129")
    assert not q["both_holdout_states_identity_time_ready"]
    assert q["holdout_states"]["PA"]["source_time_cohort_plot_fraction"] is None
    assert not data["biological_promotion_authorized"]


def test_bad_training_source_sha_never_fetches_unopened_FIA(tmp_path):
    folder=tmp_path/"training";folder.mkdir()
    (folder/"fia_new_cohort_joint_source_only_county_stable_v2.csv").write_text("bad")
    (folder/"derived_receipt.json").write_text("{}")
    calls=[]
    def getter(st,table):
        calls.append((st,table))
        raise AssertionError("should never acquire after training SHA fails")
    with pytest.raises(ValueError,match="SHA mismatch"):
        g.run(tmp_path/"out",folder,ROOT/"configs/fia_joint_climate_support_gate_v1.json",
              ROOT/"configs/fia_PA_MI_identity_only_v2.json",fetcher=getter)
    assert calls==[]


def test_first_source_only_status_and_github_archive_are_not_growth():
    assert g.PROGRAM=="fia_PA_MI_unopened_holdout_identity_only_v2"
    assert g.MAX_END_YEAR==2025
    assert g.MAX_GAP_MONTHS==252
    assert g.MIN_STATE_COUNTIES==5
    assert g.MIN_STATE_PLOT_CHAINS==25
    assert g.MIN_SHARED_COHORTS==2
