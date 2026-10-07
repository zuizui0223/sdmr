import json

import numpy as np
import pandas as pd
import pytest

from sdmr.process_id.fresh.sealed_validation_v5 import (
    ALL_ROUTES,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    EXPECTED_TAXA,
    PRIMARY_ROUTES,
    REPORT_ROUTES,
    SOIL_SHARD_COUNT,
    _bootstrap_mean_ci,
    abstention_integrity_violations,
    answer_id_table,
    apply_structural_decoding,
    capacity_filtering_claim_supported,
    spatial_shard_bounds,
    validate_contract,
)


def test_sealed_validation_contract_freezes_all_emp_thresholds():
    c=validate_contract("configs/sdmr_fresh_empirical_v5_sealed_validation.json")
    assert c["upstream_requirements"]["exact_taxa"]==50
    assert c["answer_check_features"]["predictor_count"]==46
    assert c["promotion"]["EMP_A"]["minimum"]==0.01
    assert c["promotion"]["EMP_B"]["bootstrap_replicates"]==20_000
    assert c["promotion"]["EMP_B"]["bootstrap_seed"]==20260926
    assert c["promotion"]["EMP_C"]["minimum_mean_auc_difference"]==-0.02
    assert c["promotion"]["EMP_D"]["denominator_cells"]==300
    assert c["promotion"]["EMP_F"]["exact_taxa"]==50


def test_answer_id_table_uses_only_final50_answer_rows(tmp_path):
    selected=pd.DataFrame({
        "selection_rank":range(1,51),
        "scientific_name":[f"Taxon {i:02d}" for i in range(1,51)],
    })
    outer=[]
    for name in selected.scientific_name:
        outer.append({
            "scientific_name":name,
            "occurrence_id":f"{name}|100",
            "spatial_block":1,
            "outer_role":"model_pool",
        })
        outer.append({
            "scientific_name":name,
            "occurrence_id":f"{name}|200",
            "spatial_block":2,
            "outer_role":"answer_check",
        })
    # Non-final taxon must be ignored.
    outer.append({
        "scientific_name":"Other",
        "occurrence_id":"Other|999",
        "spatial_block":3,
        "outer_role":"answer_check",
    })
    sp=tmp_path/"selected.csv";op=tmp_path/"outer.csv"
    selected.to_csv(sp,index=False);pd.DataFrame(outer).to_csv(op,index=False)
    got=answer_id_table(selected_path=sp,outer_split_path=op)
    assert len(got)==50
    assert got.scientific_name.nunique()==50
    assert got.gbifid.eq("200").all()
    assert "Other" not in set(got.scientific_name)


def test_answer_id_table_rejects_duplicate_sealed_ids(tmp_path):
    selected=pd.DataFrame({
        "selection_rank":range(1,51),
        "scientific_name":[f"T{i}" for i in range(1,51)],
    })
    rows=[
        {"scientific_name":name,"occurrence_id":f"{name}|1","spatial_block":1,"outer_role":"answer_check"}
        for name in selected.scientific_name
    ]
    rows.append(rows[0].copy())
    sp=tmp_path/"s.csv";op=tmp_path/"o.csv"
    selected.to_csv(sp,index=False);pd.DataFrame(rows).to_csv(op,index=False)
    with pytest.raises(ValueError,match="unique"):
        answer_id_table(selected_path=sp,outer_split_path=op)


def test_structural_decoding_is_exactly_the_frozen_six_rules():
    frame=pd.DataFrame({
        "location_id":[1,2],
        "fcf":[np.nan,2.0],"bio6":[1.0,-1.0],
        "swe":[np.nan,3.0],"scd":[0.0,10.0],
        "fgd":[np.nan,100.0],"gsl":[365.0,200.0],
        "lgd":[np.nan,300.0],
        "gdgfgd5":[np.nan,50.0],"ngd5":[365.0,100.0],
        "gdgfgd10":[np.nan,70.0],"ngd10":[365.0,80.0],
    })
    decoded,ledger=apply_structural_decoding(frame)
    assert decoded.loc[0,"fcf"]==0.0
    assert decoded.loc[0,"swe"]==0.0
    assert decoded.loc[0,"fgd"]==1.0
    assert decoded.loc[0,"lgd"]==365.0
    assert decoded.loc[0,"gdgfgd5"]==1.0
    assert decoded.loc[0,"gdgfgd10"]==1.0
    assert len(ledger)==6
    assert ledger.corrected_rows.sum()==6


def test_emp_b_bootstrap_is_deterministic_and_exact_50():
    gains=np.linspace(-0.01,0.03,EXPECTED_TAXA)
    a=_bootstrap_mean_ci(gains)
    b=_bootstrap_mean_ci(gains.copy())
    assert a==b
    assert BOOTSTRAP_REPLICATES==20_000
    assert BOOTSTRAP_SEED==20260926
    with pytest.raises(ValueError):
        _bootstrap_mean_ci(gains[:-1])


def test_sealed_soil_shards_cover_index_once():
    n=123_457
    ranges=[spatial_shard_bounds(n,i,SOIL_SHARD_COUNT) for i in range(SOIL_SHARD_COUNT)]
    assert SOIL_SHARD_COUNT==16
    assert ranges[0][0]==0
    assert ranges[-1][1]==n
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    assert sum(stop-start for start,stop in ranges)==n


def test_emp_e_requires_exact_final50_by_six_process_grid():
    selected=pd.DataFrame({
        "selection_rank":range(1,51),
        "scientific_name":[f"Taxon {i:02d}" for i in range(1,51)],
    })
    processes=(
        "thermal","water","seasonality",
        "radiation_energy","soil_substrate","productivity",
    )
    rows=[
        {
            "scientific_name":taxon,
            "process":process,
            "stable_state":"required",
            "stable_sharp":True,
        }
        for taxon in selected.scientific_name
        for process in processes
    ]
    stable=pd.DataFrame(rows)
    assert abstention_integrity_violations(stable,selected)==0

    missing=stable.iloc[:-1].copy()
    assert abstention_integrity_violations(missing,selected)>0

    wrong=stable.copy()
    wrong.loc[0,"scientific_name"]="Unexpected taxon"
    assert abstention_integrity_violations(wrong,selected)>0

    bad_abstention=stable.copy()
    bad_abstention.loc[0,"stable_state"]="unresolved"
    bad_abstention.loc[0,"stable_sharp"]=True
    assert abstention_integrity_violations(bad_abstention,selected)>0


def test_capacity_control_is_report_only_and_does_not_change_emp_conjunction():
    c=validate_contract("configs/sdmr_fresh_empirical_v5_sealed_validation.json")
    assert "full_46_flat_hgb" in c["routes"]["report_only"]
    assert c["capacity_control"]["promotion_gate"] is False
    assert c["capacity_control"]["route"]=="full_46_flat_hgb"
    assert c["promotion"]["strict_conjunction"]==[
        "EMP-A","EMP-B","EMP-C","EMP-D","EMP-E","EMP-F"
    ]
    cap=json.load(open("configs/sdmr_fresh_empirical_v5_capacity_control_amendment.json"))
    assert cap["original_promotion"]["EMP_A_to_EMP_F_unchanged"] is True
    assert cap["interpretation_boundary"]["does_not_affect_EMP_promotion"] is True


def test_sealed_route_set_matches_frozen_contract_exactly():
    c=validate_contract("configs/sdmr_fresh_empirical_v5_sealed_validation.json")
    assert PRIMARY_ROUTES==(
        "sdmr_process_first",
        "matched_learner_flat_predictive_selector",
    )
    assert REPORT_ROUTES==tuple(c["routes"]["report_only"])
    assert REPORT_ROUTES==(
        "auc_oriented_flat_selector",
        "correlation_vif_flat_filter",
        "full_46_flat_hgb",
    )
    assert ALL_ROUTES==PRIMARY_ROUTES+REPORT_ROUTES
    assert "full_46_flat_hgb" in ALL_ROUTES


def test_capacity_filtering_claim_requires_all_50_evaluable():
    import sdmr.process_id.fresh.sealed_validation_v5 as m

    assert m.EXPECTED_TAXA==50
    cap=json.load(open("configs/sdmr_fresh_empirical_v5_capacity_control_amendment.json"))
    boundary=cap["interpretation_boundary"]
    assert boundary["require_all_50_capacity_comparisons_evaluable_for_strong_filtering_claim"] is True
    assert "all 50 capacity comparisons are evaluable" in boundary[
        "process_first_filtering_predictive_advantage_supported_if"
    ]


def test_capacity_filtering_claim_fails_with_49_of_50_evaluable():
    assert capacity_filtering_claim_supported([True]*50,0.001) is True
    flags=[True]*50
    flags[-1]=False
    assert capacity_filtering_claim_supported(flags,0.001) is False
    assert capacity_filtering_claim_supported([True]*50,0.0) is False
    with pytest.raises(ValueError):
        capacity_filtering_claim_supported([True]*49,0.1)


def test_emp_e_rejects_invalid_state_and_inconsistent_sharp_flag():
    selected=pd.DataFrame({
        "selection_rank":range(1,51),
        "scientific_name":[f"Taxon {i:02d}" for i in range(1,51)],
    })
    processes=(
        "thermal","water","seasonality",
        "radiation_energy","soil_substrate","productivity",
    )
    stable=pd.DataFrame([
        {
            "scientific_name":taxon,
            "process":process,
            "stable_state":"required",
            "stable_sharp":True,
        }
        for taxon in selected.scientific_name
        for process in processes
    ])
    bad_state=stable.copy()
    bad_state.loc[0,"stable_state"]="mystery"
    bad_state.loc[0,"stable_sharp"]=False
    assert abstention_integrity_violations(bad_state,selected)>0

    bad_flag=stable.copy()
    bad_flag.loc[0,"stable_sharp"]=False
    assert abstention_integrity_violations(bad_flag,selected)>0
