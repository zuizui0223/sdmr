"""Synthetic original-source xy axes only; no real HF253/HF453 download."""
import importlib.util
from io import StringIO
from pathlib import Path
import sys
import json

import pytest

sys.path.insert(0,str(Path("scripts").resolve()))
p=Path("scripts/hf253_original_xy_axis_source_diagnosis_v1.py")
spec=importlib.util.spec_from_file_location("hf253_2019_xy_source_only",p)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def _source():
    return (
        "stem.tag,tree.id,gx,gy,status,dbh,sp\n"
        "T1,P1,150,100,DC,30,A\n"
        "T2,P1,650,100,A,15,B\n"
        "T3,P2,300,300,D,80,C\n"
        "T4,P2,420,200,AU,50,D\n"
        "OTHER,P3,100,100,A,8,E\n"
    )


def test_source_axes_must_be_diagnosed_without_2022_biology():
    r=mod.inspect_original_xy(
        StringIO(_source()),{"T1","T2","T3","T4"},
        expected_rows=5,expected_targets=4,expected_parents=2
    )
    assert r["status"]=="original_source_xy_axis_support_diagnosed_only"
    assert r["n_original_2019_rows"]==5
    assert r["original_x_min"]==150
    assert r["original_x_max"]==650
    assert r["original_y_min"]==100
    assert r["original_y_max"]==300
    assert r["n_source_x_gt_500"]==1
    assert r["n_source_x_gt_700"]==0
    assert r["n_source_y_gt_500"]==0
    a=r["fixed_geometry_candidate_receipts"]["assumed_x500_y700"]
    b=r["fixed_geometry_candidate_receipts"]["alternate_x700_y500"]
    assert a["n_source_valid_stems"]==3
    assert a["n_full_original_parent_IDs_with_valid_source_positions"]==1
    assert b["n_source_valid_stems"]==4
    assert b["n_full_original_parent_IDs_with_valid_source_positions"]==2
    assert r["zero_original_HF453_outcomes_or_covariate_models_opened"]
    assert r["axis_orientation_not_demonstrated_by_coordinate_ranges_alone"]


def test_source_biology_mutations_leave_xy_audit_identical():
    raw=_source()
    altered=raw.replace("DC,30,A","DS,5,other_species").replace(
        "AU,50,D","NA,999,Z"
    )
    a=mod.inspect_original_xy(StringIO(raw),{"T1","T2","T3","T4"},
                             expected_rows=5,expected_targets=4,expected_parents=2)
    b=mod.inspect_original_xy(StringIO(altered),{"T1","T2","T3","T4"},
                             expected_rows=5,expected_targets=4,expected_parents=2)
    assert a==b


def test_no_missing_parent_or_duplicate_original_tag_fabricated():
    raw=_source()+"T1,P1,150,100,DC,30,A\n"
    with pytest.raises(ValueError,match="source_tag_or_parent_identity"):
        mod.inspect_original_xy(StringIO(raw),{"T1","T2","T3","T4"},
                                expected_rows=6,expected_targets=4,expected_parents=2)
    missing=_source().replace("T2,P1,650,100","T2,P1,NA,NA")
    r=mod.inspect_original_xy(StringIO(missing),{"T1","T2","T3","T4"},
                               expected_rows=5,expected_targets=4,expected_parents=2)
    assert r["n_missing_original_gx_or_gy"]==1


def test_preflight_never_fetches_original_source(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"run_source_axis_only",lambda:
        (_ for _ in ()).throw(AssertionError("no original file in preflight")))
    out=tmp_path/"pre.json"
    monkeypatch.setattr(sys,"argv",["axis","--preflight-only","--out",str(out)])
    mod.main()
    r=json.loads(out.read_text())
    assert r["result"]["status"]=="response_free_xy_source_preflight_only"
    assert not r["new_HF453_biological_outcome_read"]
    assert r["new_model_fits"]==0
    wrong=tmp_path/"wrong.lock"
    wrong.write_text(mod.LOCK.replace("x500_y700_and_x700_y500","x700_y500"))
    monkeypatch.setattr(sys,"argv",["axis","--execute-lock",str(wrong),
                                    "--out",str(tmp_path/"not.json")])
    with pytest.raises(ValueError,match="contract_changed"):
        mod.main()
