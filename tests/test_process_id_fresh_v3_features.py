import pandas as pd

import sdmr.process_id.fresh.features_v3 as f


def test_v3_feature_contract_freezes_final50_and_46_predictors():
    c=f.validate_contract("configs/sdmr_fresh_empirical_v3_feature_gate.json")
    assert c["taxon_count"]==50
    assert c["predictor_count"]==46
    assert c["selected_manifest_sha256"]==f.EXPECTED_SELECTED_SHA256
    assert c["information_boundary"]["answer_check_access"] is False
    assert c["information_boundary"]["model_fitting"] is False


def test_structural_decoding_rules_are_exactly_six_and_deterministic():
    frame=pd.DataFrame({
        "location_id":[0,1,2,3,4,5],
        "fcf":[float("nan"),1,1,1,1,1],
        "bio6":[5,-1,-1,-1,-1,-1],
        "swe":[1,float("nan"),1,1,1,1],
        "scd":[1,0,1,1,1,1],
        "fgd":[1,1,float("nan"),1,1,1],
        "lgd":[365,365,float("nan"),365,365,365],
        "gsl":[100,100,365,100,100,100],
        "gdgfgd5":[1,1,1,float("nan"),1,1],
        "gdgfgd10":[1,1,1,1,float("nan"),1],
        "ngd5":[100,100,100,365,100,100],
        "ngd10":[100,100,100,100,365,100],
    })
    out,ledger=f.apply_structural_decoding(frame)
    assert len(ledger)==6
    assert out.loc[0,"fcf"]==0
    assert out.loc[1,"swe"]==0
    assert out.loc[2,"fgd"]==1
    assert out.loc[2,"lgd"]==365
    assert out.loc[3,"gdgfgd5"]==1
    assert out.loc[4,"gdgfgd10"]==1
    assert ledger["rule_is_predeclared"].all()


def test_soil_spatial_shards_cover_location_index_exactly_once():
    n=293_849
    ranges=[f.spatial_shard_bounds(n,i,f.SOIL_SHARD_COUNT) for i in range(f.SOIL_SHARD_COUNT)]
    assert ranges[0][0]==0
    assert ranges[-1][1]==n
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    assert sum(b-a for a,b in ranges)==n
    assert max(b-a for a,b in ranges)-min(b-a for a,b in ranges)<=1


def test_final50_manifest_is_exact_and_support_eligible():
    df=f.load_final50("configs/sdmr_fresh_empirical_v3_selected_taxa.csv")
    assert len(df)==50
    assert df["scientific_name"].nunique()==50
    assert df["soil_support_eligible"].astype(bool).all()
    assert df["model_pool_rows"].sum()==f.EXPECTED_MODEL_POOL_ROWS
