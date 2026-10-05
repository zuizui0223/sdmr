import json
from pathlib import Path

import pandas as pd
import pytest

import sdmr.process_id.fresh.features_v5 as f


CONFIG=Path("configs/sdmr_fresh_empirical_v5_feature_gate.json")


def test_v5_feature_contract_matches_preeligibility_gate():
    c=f.validate_contract(CONFIG)
    assert c["taxon_count"]==50
    assert c["predictor_count"]==46
    assert c["complete_case_gate"]["minimum_model_pool_retention_fraction"]==0.80
    assert c["complete_case_gate"]["minimum_model_pool_complete_rows"]==50
    assert c["complete_case_gate"]["minimum_background_complete_rows"]==4000
    assert c["information_boundary"]["answer_check_access"] is False
    assert c["information_boundary"]["model_fitting"] is False


def test_v5_feature_structural_rules_are_exactly_frozen_six():
    c=json.loads(CONFIG.read_text())
    assert len(c["structural_source_decoding"])==6
    assert [x["predictor"] for x in c["structural_source_decoding"]]==[
        "fcf","swe","fgd","lgd","gdgfgd5","gdgfgd10"
    ]


def test_v5_feature_decoding_is_deterministic():
    x=pd.DataFrame({
      "fcf":[float("nan"),1.0],"bio6":[1.0,-1.0],
      "swe":[float("nan"),3.0],"scd":[0.0,20.0],
      "fgd":[float("nan"),100.0],"gsl":[365.0,200.0],
      "lgd":[float("nan"),300.0],
      "gdgfgd5":[float("nan"),20.0],"ngd5":[365.0,100.0],
      "gdgfgd10":[float("nan"),30.0],"ngd10":[365.0,80.0],
    })
    y,ledger=f.apply_structural_decoding(x)
    assert y.loc[0,"fcf"]==0.0
    assert y.loc[0,"swe"]==0.0
    assert y.loc[0,"fgd"]==1.0
    assert y.loc[0,"lgd"]==365.0
    assert y.loc[0,"gdgfgd5"]==1.0
    assert y.loc[0,"gdgfgd10"]==1.0
    assert ledger["corrected_rows"].sum()==6


def test_v5_soil_shards_cover_once():
    n=321_987
    ranges=[f.spatial_shard_bounds(n,i,f.SOIL_SHARD_COUNT) for i in range(f.SOIL_SHARD_COUNT)]
    assert ranges[0][0]==0
    assert ranges[-1][1]==n
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    assert sum(b-a for a,b in ranges)==n
