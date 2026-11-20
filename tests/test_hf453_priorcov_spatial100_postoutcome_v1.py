"""Synthetic-only HF453 100m spatial-block postoutcome validation tests."""
from copy import deepcopy
from io import StringIO
import importlib.util
import json
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path("scripts").resolve()))
source=Path("scripts/hf453_priorcov_spatial100_postoutcome_v1.py")
spec=importlib.util.spec_from_file_location("sdmr_hf453_geo100",source)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def config():
    return json.loads(Path("configs/hf453_spatial_block_priorcov_postoutcome_v1.json").read_text())


def test_spatial100_source_contract_freezes_2019_position_and_5fold(config):
    mod.validate_spatial_contract(config)
    for key,value in (
        ("block_size_m",200),
        ("minimum_distinct_source_blocks",3),
        ("min_fraction_geo_complete_of_original_CV_stems",0.5),
    ):
        broken=deepcopy(config)
        broken["fold_geometry"][key]=value
        with pytest.raises(ValueError,match="geographic_holdout_geometry"):
            mod.validate_spatial_contract(broken)
    broken=deepcopy(config)
    broken["previous_priorcov_result_run"]=0
    with pytest.raises(ValueError,match="postoutcome_original_CP"):
        mod.validate_spatial_contract(broken)


def _source():
    return (
        "stem.tag,tree.id,gx,gy,sp,dbh,df.status\n"
        "ST1,Parent1,25,25,sp1,20,A\n"
        "ST2,Parent1,190,60,sp2,35,D\n"
        "ST3,Parent2,500,700,sp3,NA,D\n"
        "ST4,Parent3,120,NA,sp4,20,A\n"
        "ST5,Parent4,-5,100,sp5,11,A\n"
    )


def test_old_source_only_2D_geometry_is_outcome_invariant_and_edges_fixed():
    target={"ST1","ST2","ST3","ST4","ST5"}
    cells,meta=mod.parse_original_source_locations(
        StringIO(_source()),target,expected_rows=5,expected_targets=5)
    assert meta["n_original_source_rows"]==5
    assert meta["n_source_stems_with_missing_unusable_position"]==1
    assert meta["n_source_stems_outside_fixed_plot_rectangle"]==1
    parents,groups=mod.original_parent_centroid_blocks(cells,expected_parents=4)
    assert parents["Parent1"]==(1,0)  # center x 107.5, y 42.5
    assert parents["Parent2"]==(4,6)  # exact max plot boundary
    assert "Parent3" not in parents and "Parent4" not in parents
    assert groups["n_parent_IDs_with_any_missing_or_out_of_rectangle_stem_position"]==2
    assert groups["n_original_parent_IDs_with_valid_full_source_positions"]==2
    assert groups["n_parents_with_matched_stems_in_multiple_native_100m_cells"]==1
    assert groups["parent_centroids_from_original_stems_before_reading_new_2022_Y"]
    assert not any("coordinates" in key for key in groups)
    changed=_source().replace("sp1,20,A","different_species,999,dead")
    recoded,meta2=mod.parse_original_source_locations(
        StringIO(changed),target,expected_rows=5,expected_targets=5)
    assert (recoded,meta2)==(cells,meta)


def test_missing_any_stem_position_invalidates_entire_original_parent_group():
    csv=("stem.tag,tree.id,gx,gy\n"
         "A,Parent0,10,10\nB,Parent0,NA,NA\n"
         "C,Parent1,100,200\n")
    target={"A","B","C"}
    src,stats=mod.parse_original_source_locations(
        StringIO(csv),target,expected_rows=3,expected_targets=3)
    parents,s=mod.original_parent_centroid_blocks(src,expected_parents=2)
    assert "Parent0" not in parents
    assert parents["Parent1"]==(1,2)
    assert s["n_parent_IDs_with_any_missing_or_out_of_rectangle_stem_position"]==1
    assert stats["n_source_valid_stem_positions"]==2


def test_spatial_and_parent_grouped_folds_never_split_one_parent():
    rows=[]
    for parent in range(150):
        for stem in range(2):
            baseline_unhealthy=(parent%4)==0
            outcome="p" if parent%7==0 else "z"  # no event-class alias with the 20 synthetic blocks
            rows.append({
                "tag":f"ST{parent:05d}:{stem}",
                "parent":f"tree_{parent}",
                "sp":["sp1","sp2","sp3"][parent%3],
                "logdb":math.log1p(12+parent%25),
                "prior_unhealthy":int(baseline_unhealthy),
                "cp_more":int(parent%3==0),
                "response":outcome,
                "spatial_block":f"block_{parent%20}",
            })
    for mode in ("parent","spatial100"):
        output=mod.evaluate_grouped_same_model(rows,mode)
        assert output["status"]=="postoutcome_one_forest_groupfold_descriptive"
        assert output["mode"]==mode
        assert output["n_original_known_outcome_stems"]==300
        assert output["n_original_parent_tree_IDs"]==150
        assert output["n_folds"]==5
        assert output["n_heldout_parent_overlap"]==0
        assert sum(f["n_heldout_original_stems"] for f in output["folds"])==300
        assert sum(f["n_heldout_source_parent_IDs"] for f in output["folds"])==150
        assert all(f["n_training_heldout_shared_parent_IDs"]==0 for f in output["folds"])
        assert math.isfinite(output["delta_logloss"])
        assert output["not_independent_forest_or_causal_confirmation"]


def test_bad_source_identity_stops_before_biological_status_access(monkeypatch,config):
    def get_original(path):
        return {"sha256":"0"*64,"md5":mod.FROZEN_HF453_MD5,
                "n_bytes":mod.FROZEN_HF453_SIZE}
    monkeypatch.setattr(mod,"get_frozen_hf453",get_original)
    monkeypatch.setattr(mod,"fetch_HF253_provider_bytes",lambda path:
        (_ for _ in ()).throw(AssertionError("HF253 must not be fetched")))
    with pytest.raises(ValueError,match="HF453_original_file_bytes_changed"):
        mod.run_spatial_sensitivity(config)


def test_lock_preflight_does_not_open_tree_coordinates_or_outcomes(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"run_spatial_sensitivity",lambda cfg:
        (_ for _ in ()).throw(AssertionError("preflight cannot open original files")))
    pre=tmp_path/"preflight.json"
    monkeypatch.setattr(sys,"argv",["script","--preflight-only","--out",str(pre)])
    mod.main()
    d=json.loads(pre.read_text())
    assert d["preflight"] is True
    assert d["result"]["status"]=="source_unopened_spatial_contract_only"
    assert d["post_original_HF453_Y_and_prior_CP_result_opening"]
    assert not d["no_causal_process_identified"] is False
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_CONTENT.replace("block=100m","block=200m"))
    monkeypatch.setattr(sys,"argv",["script","--execute-lock",str(bad),
                                    "--out",str(tmp_path/"bad.json")])
    with pytest.raises(ValueError,match="protocol_changed"):
        mod.main()
