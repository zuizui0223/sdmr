import pandas as pd

import sdmr.process_id.fresh.cohort_v3_support_runtime as rt


def test_v3_support_shards_cover_location_index_once():
    n=401_237
    ranges=[rt.spatial_shard_bounds(n,i,rt.SUPPORT_SHARDS) for i in range(rt.SUPPORT_SHARDS)]
    assert ranges[0][0]==0
    assert ranges[-1][1]==n
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    assert sum(stop-start for start,stop in ranges)==n
    assert max(stop-start for start,stop in ranges)-min(stop-start for start,stop in ranges)<=1


def test_v3_support_registry_is_exact_four_soilgrids():
    specs=rt.soil_specs("configs/sdmr_fresh_empirical_process_registry_v1.csv")
    assert tuple(specs)==rt.EXPECTED_SOIL
    assert len(specs)==4
    assert all(spec.source=="SoilGrids" for spec in specs.values())
    assert all(spec.uri.endswith(".vrt") for spec in specs.values())


def test_v3_support_shard_persists_boolean_bits_only(tmp_path, monkeypatch):
    import pytest
    pytest.importorskip("pyarrow")
    locations=pd.DataFrame({
        "location_id":range(64),
        "longitude":[float(i) for i in range(64)],
        "latitude":[0.0]*64,
    })
    candidates=pd.DataFrame({"candidate_rank":range(1,81),"scientific_name":[f"T{i}" for i in range(80)]})
    model=pd.DataFrame()
    bg=pd.DataFrame()
    monkeypatch.setattr(rt,"prepare_support_points",lambda **kwargs:(candidates,model,bg,locations))
    dummy=rt.RasterLayerSpec(
        predictor="sg_phh2o_0_5",
        uri="https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt",
        source="SoilGrids",version="2.0",scale=0.1,offset=0.0,
    )
    monkeypatch.setattr(rt,"soil_specs",lambda path:{"sg_phh2o_0_5":dummy})
    monkeypatch.setattr(rt,"_finite_mask_for_points",lambda points,spec:pd.Series([True]*len(points)).to_numpy())
    result=rt.extract_support_shard(
        predictor="sg_phh2o_0_5",shard_index=0,shard_count=32,
        candidate_path="unused",model_pool_path="unused",background_path="unused",
        process_registry_path="unused",output_dir=tmp_path,
    )
    part=pd.read_parquet(tmp_path/"support.parquet")
    assert list(part.columns)==["location_id","is_finite"]
    assert part["is_finite"].dtype==bool
    assert result["numeric_soil_values_persisted"] is False
    assert result["answer_check_support_read"] is False
    assert result["model_fitting_performed"] is False


def test_v3_support_thresholds_match_frozen_contract():
    c=rt.validate_contract("configs/sdmr_fresh_empirical_v3_soil_support_eligibility.json")
    assert c["soil_support_gate"]["model_pool_gate"]["minimum_joint_finite_fraction"]==0.80
    assert c["soil_support_gate"]["model_pool_gate"]["minimum_joint_finite_rows"]==50
    assert c["soil_support_gate"]["background_300km_gate"]["minimum_joint_finite_rows"]==4000
    assert c["soil_support_gate"]["background_300km_gate"]["denominator_rows"]==5000
