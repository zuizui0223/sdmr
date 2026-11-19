"""Original tree-grain synthetic invariants only; no source network use."""
import importlib.util
from io import StringIO
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path("scripts").resolve()))
p=Path("scripts/hf253_hf453_parent_tree_grain_source_v1.py")
spec=importlib.util.spec_from_file_location("hf253_parent_grain",p)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def _csv():
    return "\n".join([
        "stem.tag,stem.id,tree.id,sp,dbh,status,CP",
        "ST1,S1,TreeA,X,10,A,1",
        "ST2,S2,TreeA,X,15,D,5",
        "ST3,S3,TreeB,Y,35,A,3",
        "ST4,S4,TreeC,Z,21,D,2",
        "OTHER,S5,TreeD,UNKNOWN,50,A,2",
    ])+"\n"


def test_parent_tree_grouping_does_not_count_stems_as_trees():
    source,meta=mod.source_parent_map(StringIO(_csv()))
    assert meta["n_HF253_original_rows"]==5
    assert meta["only_mechanical_identity_columns_used"] is True
    assert meta["species_diameter_status_and_canopy_values_not_read"] is True
    z=mod.audit_parent_tree_grain({"ST1","ST2","ST3","ST4"},source)
    assert z["n_stem_tag_matches_in_original_HF253"]==4
    assert z["n_distinct_original_tree_ID_candidates"]==3
    assert z["n_tree_IDs_with_at_least_two_matched_stems"]==1
    assert z["n_matched_stems_belonging_to_multi_stem_tree_IDs"]==2
    assert z["parent_stem_multiplicity_histogram"]["one"]==2
    assert z["parent_stem_multiplicity_histogram"]["two"]==1
    assert z["maximum_matched_stems_per_tree_ID"]==2
    assert z["status"]=="parent_tree_identity_incomplete_source_hold"  # fixture n!=30808


def test_ambiguous_source_parent_is_not_silently_deduplicated():
    src=_csv()+"ST1,S1,Tree_DIFFERENT,X,10,A,1\n"
    mapping,_=mod.source_parent_map(StringIO(src))
    q=mod.audit_parent_tree_grain({"ST1","ST2","ST3","ST4"},mapping)
    assert q["n_ambiguous_original_stem_to_parent_treeID"]==1
    assert q["n_source_resolved_stem_tags"]==3
    assert q["n_distinct_original_tree_ID_candidates"]==3
    assert q["physical_tree_independence_not_inferred_from_stem_tags"] is True


def test_missing_original_parent_and_unmatched_stem_remain_unknown():
    data=_csv().replace("ST2,S2,TreeA","ST2,S2,NA")
    m,_=mod.source_parent_map(StringIO(data))
    q=mod.audit_parent_tree_grain({"ST1","ST2","ST3","missing"},m)
    assert q["n_unmatched_HF453_StemTag"]==1
    assert q["n_missing_original_stem_or_tree_parentID"]==1
    assert q["n_source_resolved_stem_tags"]==2
    assert q["status"]=="parent_tree_identity_incomplete_source_hold"


def test_mutating_species_and_diameter_has_no_identity_effect():
    s=mod.source_parent_map(StringIO(_csv()))
    t=mod.source_parent_map(StringIO(_csv().replace(",X,10,A,1",",different,300,D,5")))
    assert s==t


def test_original_byte_sha_refusal_precedes_source_identity_open(monkeypatch):
    monkeypatch.setattr(mod,"get_frozen_hf453",lambda path:{
        "sha256":"0"*64,"md5":mod.FROZEN_HF453_MD5,
        "n_bytes":mod.FROZEN_HF453_SIZE,
    })
    monkeypatch.setattr(mod,"fetch_HF253_provider_bytes",lambda path:
        (_ for _ in ()).throw(AssertionError("must refuse before original source GET")))
    with pytest.raises(ValueError,match="HF453_original_source_byte"):
        mod.run_source_only()


def test_preflight_does_not_open_any_source(monkeypatch,tmp_path):
    monkeypatch.setattr(mod,"run_source_only",lambda:
        (_ for _ in ()).throw(AssertionError("preflight cannot open source")))
    out=tmp_path/"pre.json"
    monkeypatch.setattr(sys,"argv",["stage","--preflight-only","--out",str(out)])
    mod.main()
    import json
    d=json.loads(out.read_text())
    assert d["result"]["status"]=="preflight_no_original_tree_or_stem_data_read"
    assert not d["new_biological_status_size_or_species_values_opened"]
    assert d["HF453_original_status_CP_effect_untouched"]
    assert not d["Product_B_unblocked"]
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_CONTENT.replace(
        "no_model_refit_or_causal_claim=true","no_model_refit_or_causal_claim=false",
    ))
    monkeypatch.setattr(sys,"argv",["stage","--execute-lock",str(bad),
                                    "--out",str(tmp_path/"bad.json")])
    with pytest.raises(ValueError,match="lock_changed"):
        mod.main()
