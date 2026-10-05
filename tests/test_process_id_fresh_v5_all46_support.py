import pandas as pd
import pytest

import sdmr.process_id.fresh.cohort_v5_all46_support as s


def _candidates():
    return pd.DataFrame({
      "candidate_rank":range(1,121),
      "scientific_name":[f"T{i:03d}" for i in range(120)],
      "family":[f"F{i:03d}" for i in range(120)],
      "genus":[f"G{i:03d}" for i in range(120)],
      "selection_hash":[f"{i:064x}" for i in range(120)],
    })


def test_v5_support_design_matches_frozen_contract():
    c=s.validate_contract("configs/sdmr_fresh_empirical_v5_preeligibility.json")
    assert c["candidate_roster"]["exact_candidates"]==120
    assert c["all46_support_eligibility"]["predictor_count"]==46
    assert c["final_selection"]["final_taxa"]==50
    assert s.MODEL_MIN_FRACTION==0.80
    assert s.MODEL_MIN_ROWS==50
    assert s.BACKGROUND_MIN_ROWS==4000


def test_v5_structural_support_rules_remain_exactly_six():
    assert list(s.STRUCTURAL_RULES)==[
      "fcf","swe","fgd","lgd","gdgfgd5","gdgfgd10"
    ]


def test_v5_candidate_loader_requires_exact120(tmp_path):
    p=tmp_path/"c.csv"
    _candidates().to_csv(p,index=False)
    df=s.load_candidates(p)
    assert len(df)==120
    assert df.candidate_rank.tolist()==list(range(1,121))


def test_v5_support_spatial_shards_cover_once():
    n=633_217
    ranges=[s.spatial_shard_bounds(n,i,s.SOIL_SHARD_COUNT) for i in range(s.SOIL_SHARD_COUNT)]
    assert ranges[0][0]==0
    assert ranges[-1][1]==n
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    assert sum(b-a for a,b in ranges)==n


def test_v5_support_job_persists_boolean_only(tmp_path,monkeypatch):
    pytest.importorskip("pyarrow")
    candidates=_candidates()
    geometry=pd.DataFrame({
      "candidate_rank":range(1,121),
      "scientific_name":[f"T{i:03d}" for i in range(120)],
      "geometry_eligible":[True]*120,
      "source_gate_passed":[True]*120,
      "background_points":[5000]*120,
      "model_pool_occurrences":[100]*120,
    })
    locations=pd.DataFrame({
      "location_id":[0,1,2],
      "longitude":[0.0,1.0,2.0],
      "latitude":[0.0,1.0,2.0],
    })
    monkeypatch.setattr(
      s,"prepare_support_points",
      lambda **kwargs:(candidates,geometry,pd.DataFrame(),pd.DataFrame(),locations)
    )
    class Spec:
        predictor="bio1"
        source="CHELSA"
    monkeypatch.setattr(s,"_specs",lambda **kwargs:({"bio1":Spec()},pd.DataFrame()))
    monkeypatch.setattr(
      s,"extract_raster_values",
      lambda *args,**kwargs:(
        pd.DataFrame({"location_id":[0,1,2],"bio1":[1.0,float("nan"),2.0]}),
        pd.DataFrame(),
      )
    )
    result=s.extract_chelsa_support(
      predictor="bio1",candidate_path="x",model_pool_path="x",
      background_path="x",geometry_path="x",process_registry_path="x",
      chelsa_manifest_path="x",output_dir=tmp_path
    )
    part=pd.read_parquet(tmp_path/"support.parquet")
    assert list(part.columns)==["location_id","is_usable"]
    assert part.is_usable.tolist()==[True,False,True]
    assert result["numeric_environmental_values_persisted"] is False
    assert result["answer_check_support_read"] is False
    assert result["model_fitting_performed"] is False
