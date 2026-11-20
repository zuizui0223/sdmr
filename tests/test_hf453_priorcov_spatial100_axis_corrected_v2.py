"""Only synthetic HF453 axis-corrected v2 contract and heldout model tests."""
from copy import deepcopy
from io import StringIO
import importlib.util
import json
import math
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path("scripts").resolve()))
source=Path("scripts/hf453_priorcov_spatial100_axis_corrected_v2.py")
spec=importlib.util.spec_from_file_location("hf453_spatial100_axis_corrected_v2",source)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def config():
    return json.loads(Path("configs/hf453_spatial_block_priorcov_axis_corrected_v2.json").read_text())


def test_source_axis_correction_is_only_geometry_change(config):
    mod.validate_spatial_contract(config)
    assert mod.WIDTH==700 and mod.HEIGHT==500 and mod.BLOCK==100
    assert config["source_only_axis_diagnostic_run"]==44750670871
    assert config["first_spatial_source_hold_run"]==44749714741
    assert config["source_only_axis_diagnostic_receipt_sha256"]=="8a065d3c7d3a44edd39ebaf0062ce9e3a5e8f9b2b2b86478175c8f1cdad1725c"
    assert config["axis_only_change_from_v1"]
    assert config["no_change_to_old_Y_or_priorcov_learners"]
    for update in (
        lambda d:d["source_coordinate"].update(source_plot_width_m=500),
        lambda d:d["fold_geometry"].update(block_size_m=200),
        lambda d:d.update(source_only_axis_diagnostic_run=0),
    ):
        bad=deepcopy(config);update(bad)
        with pytest.raises(ValueError):
            mod.validate_spatial_contract(bad)


def test_source_full_xy_700x500_and_edge_bins():
    src=("stem.tag,tree.id,gx,gy,status,dbh\n"
         "ST1,P1,25,25,DS,30\n"
         "ST2,P1,190,60,A,45\n"
         "ST3,P2,700,500,DC,70\n"
         "ST4,P3,120,NA,A,10\n"
         "ST5,P4,-5,100,A,30\n")
    target={"ST1","ST2","ST3","ST4","ST5"}
    coords,source=mod.parse_original_source_locations(
        StringIO(src),target,expected_rows=5,expected_targets=5)
    assert source["n_source_valid_stem_positions"]==3
    assert source["n_source_stems_with_missing_unusable_position"]==1
    assert source["n_source_stems_outside_fixed_plot_rectangle"]==1
    centroid,c=mod.original_parent_centroid_blocks(coords,expected_parents=4)
    assert centroid["P1"]==(1,0)
    assert centroid["P2"]==(6,4)
    assert "P3" not in centroid and "P4" not in centroid
    assert c["n_original_parent_IDs_with_valid_full_source_positions"]==2
    assert c["n_parents_with_matched_stems_in_multiple_native_100m_cells"]==1
    assert c["parent_centroids_from_original_stems_before_reading_new_2022_Y"]
    changed=src.replace("DS,30","A,900").replace("DC,70","NA,1")
    coords2,source2=mod.parse_original_source_locations(
        StringIO(changed),target,expected_rows=5,expected_targets=5)
    assert (coords2,source2)==(coords,source)


def test_parent_group_and_spatial_group_keep_source_tree_together():
    rows=[]
    for parent in range(150):
        for stem in range(2):
            rows.append({
                "tag":f"ST_{parent}_{stem}",
                "parent":f"P_{parent}",
                "sp":["sp1","sp2","sp3"][parent%3],
                "logdb":math.log1p(10+parent%21),
                "prior_unhealthy":int(parent%4==0),
                "cp_more":int(parent%3==0),
                "response":"p" if parent%7==0 else "z",
                "spatial_block":f"G_{parent%20}",
            })
    for mode in ("parent","spatial100"):
        result=mod.evaluate_grouped_same_model(rows,mode)
        assert result["status"]=="postoutcome_one_forest_groupfold_descriptive"
        assert result["n_original_known_outcome_stems"]==300
        assert result["n_original_parent_tree_IDs"]==150
        assert result["n_folds"]==5
        assert result["n_heldout_parent_overlap"]==0
        assert all(q["n_training_heldout_shared_parent_IDs"]==0 for q in result["folds"])
        assert math.isfinite(result["delta_logloss"])
        assert result["not_independent_forest_or_causal_confirmation"]


def test_original_source_identity_stops_before_new_2022_Y(monkeypatch,config):
    monkeypatch.setattr(mod,"get_frozen_hf453",lambda path:{
        "sha256":"0"*64,"md5":mod.FROZEN_HF453_MD5,
        "n_bytes":mod.FROZEN_HF453_SIZE,
    })
    monkeypatch.setattr(mod,"fetch_HF253_provider_bytes",lambda path:
        (_ for _ in ()).throw(AssertionError("must not fetch changed original")))
    with pytest.raises(ValueError,match="HF453_original_file_bytes_changed"):
        mod.run_spatial_sensitivity(config)


def test_response_free_preflight_and_v2_exact_execute_lock(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"run_spatial_sensitivity",lambda d:
        (_ for _ in ()).throw(AssertionError("preflight cannot open original Y")))
    pre=tmp_path/"preflight.json"
    monkeypatch.setattr(sys,"argv",["script","--preflight-only","--out",str(pre)])
    mod.main()
    out=json.loads(pre.read_text())
    assert out["preflight"] is True
    assert out["result"]["status"]=="source_unopened_spatial_contract_only"
    assert out["post_original_HF453_Y_and_prior_CP_result_opening"]
    assert out["original_first_status_and_priorCV_receipts_unchanged"]
    assert out["no_causal_process_identified"]
    wrong=tmp_path/"bad.lock"
    wrong.write_text(mod.LOCK_CONTENT.replace("plot_dimensions_m=700_x_500","plot_dimensions_m=500_x_700"))
    monkeypatch.setattr(sys,"argv",["script","--execute-lock",str(wrong),
                                    "--out",str(tmp_path/"not.json")])
    with pytest.raises(ValueError,match="protocol_changed"):
        mod.main()
