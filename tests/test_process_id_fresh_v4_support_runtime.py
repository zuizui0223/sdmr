import numpy as np
import pandas as pd
import pytest

import sdmr.process_id.fresh.cohort_v4_all46_support as s


def test_v4_support_design_and_runtime_constants_match():
    c=s.validate_contract("configs/sdmr_fresh_empirical_v4_all46_support.json")
    assert c["candidate_roster"]["exact_candidates"]==90
    assert c["all46_support_eligibility"]["predictor_count"]==46
    assert c["all46_support_eligibility"]["final_taxa"]==50
    assert s.MODEL_MIN_FRACTION==0.80
    assert s.MODEL_MIN_ROWS==50
    assert s.BACKGROUND_MIN_ROWS==4000
    assert s.BACKGROUND_ROWS_PER_CANDIDATE==5000


def test_structural_support_rules_are_exactly_six():
    assert list(s.STRUCTURAL_RULES)==[
        "fcf","swe","fgd","lgd","gdgfgd5","gdgfgd10"
    ]


def test_structural_usable_support_decodes_only_predeclared_states():
    frame=pd.DataFrame({
        "fcf":[np.nan,1.0,np.nan],
        "bio6":[5.0,-2.0,-3.0],
        "swe":[np.nan,2.0,np.nan],
        "scd":[0.0,10.0,2.0],
        "fgd":[np.nan,3.0,np.nan],
        "gsl":[365.0,100.0,200.0],
        "lgd":[np.nan,300.0,np.nan],
        "gdgfgd5":[np.nan,4.0,np.nan],
        "ngd5":[365.0,200.0,100.0],
        "gdgfgd10":[np.nan,5.0,np.nan],
        "ngd10":[365.0,200.0,100.0],
    })
    assert s._usable_from_values(predictor="fcf",featured=frame).tolist()==[True,True,False]
    assert s._usable_from_values(predictor="swe",featured=frame).tolist()==[True,True,False]
    assert s._usable_from_values(predictor="fgd",featured=frame).tolist()==[True,True,False]
    assert s._usable_from_values(predictor="lgd",featured=frame).tolist()==[True,True,False]
    assert s._usable_from_values(predictor="gdgfgd5",featured=frame).tolist()==[True,True,False]
    assert s._usable_from_values(predictor="gdgfgd10",featured=frame).tolist()==[True,True,False]


def test_ordinary_predictor_support_is_finite_only():
    frame=pd.DataFrame({"gdd10":[1.0,np.nan,0.0]})
    assert s._usable_from_values(
        predictor="gdd10",featured=frame
    ).tolist()==[True,False,True]


def test_soil_spatial_shards_cover_locations_exactly_once():
    n=517_321
    ranges=[
        s.spatial_shard_bounds(n,i,s.SOIL_SHARD_COUNT)
        for i in range(s.SOIL_SHARD_COUNT)
    ]
    assert ranges[0][0]==0
    assert ranges[-1][1]==n
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    assert sum(stop-start for start,stop in ranges)==n
    assert max(stop-start for start,stop in ranges)-min(
        stop-start for start,stop in ranges
    )<=1


def test_support_job_persists_boolean_bits_only(tmp_path,monkeypatch):
    pytest.importorskip("pyarrow")
    candidates=pd.DataFrame({
        "candidate_rank":range(1,91),
        "scientific_name":[f"T{i}" for i in range(90)],
        "family":[f"F{i}" for i in range(90)],
        "genus":[f"G{i}" for i in range(90)],
        "selection_hash":[f"{i:064x}" for i in range(90)],
    })
    locations=pd.DataFrame({
        "location_id":range(3),
        "longitude":[0.0,1.0,2.0],
        "latitude":[0.0,1.0,2.0],
    })
    monkeypatch.setattr(
        s,"prepare_support_points",
        lambda **kwargs:(candidates,pd.DataFrame(),pd.DataFrame(),locations)
    )
    class Spec:
        predictor="bio1"
        source="CHELSA"
    monkeypatch.setattr(
        s,"_specs",lambda **kwargs:({"bio1":Spec()},pd.DataFrame())
    )
    monkeypatch.setattr(
        s,"extract_raster_values",
        lambda *args,**kwargs:(
            pd.DataFrame({"location_id":[0,1,2],"bio1":[1.0,np.nan,2.0]}),
            pd.DataFrame(),
        )
    )
    result=s.extract_chelsa_support(
        predictor="bio1",
        candidate_path="unused",
        model_pool_path="unused",
        background_path="unused",
        process_registry_path="unused",
        chelsa_manifest_path="unused",
        output_dir=tmp_path,
    )
    part=pd.read_parquet(tmp_path/"support.parquet")
    assert list(part.columns)==["location_id","is_usable"]
    assert part["is_usable"].tolist()==[True,False,True]
    assert result["numeric_environmental_values_persisted"] is False
    assert result["answer_check_support_read"] is False
    assert result["model_fitting_performed"] is False


def test_candidate_loader_requires_exact_90(tmp_path):
    p=tmp_path/"c.csv"
    pd.DataFrame({
        "candidate_rank":range(1,91),
        "scientific_name":[f"T{i}" for i in range(90)],
        "family":[f"F{i}" for i in range(90)],
        "genus":[f"G{i}" for i in range(90)],
        "selection_hash":[f"{i:064x}" for i in range(90)],
    }).to_csv(p,index=False)
    df=s.load_candidates(p)
    assert len(df)==90
    assert df["candidate_rank"].tolist()==list(range(1,91))
