"""HF253×HF453 v2 source-only synthetic checks; original v1 STOP unchanged."""
from io import StringIO
import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path("scripts").resolve()))
source=Path("scripts/hf253_hf453_original_tag_crosswalk_v2.py")
spec=importlib.util.spec_from_file_location("hf253_hf453_source_only_v2",source)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def _hf453():
    data=["StemTag,year,status,CP,sensitive"]
    for tag in ("T1","T2","T3","T4"):
        for y in (2021,2022,2023,2024):
            data.append(f"{tag},{y},DC,1,not_looked_at")
    return "\n".join(data)+"\n"


def _hf253():
    # 2019 multi-stem tree T1 repeats same original tree.id (not ambiguous).
    # T3 matches both tree tag and stem tag; T4 absent; T2 stem-tag only.
    return "\n".join([
        "tag,stem.tag,tree.id,stem.id,sp,dbh,df.status,gx",
        "T1,X1,tree_1,stem_1,species_ignored,10,A,0.0",
        "T1,X2,tree_1,stem_2,species_ignored,15,D,0.1",
        "other,T2,tree_2,stem_3,species_ignored,25,A,0.2",
        "T3,T3,tree_3,stem_4,species_ignored,30,D,0.3",
    ])+"\n"


def test_source_contract_pins_new_original_2019_without_outcome_columns():
    d=json.loads(Path("configs/hf253_hf453_source_identity_prefreeze_v1.json").read_text())
    mod.validate_source_contract(d)
    assert d["HF253"]["original_data_fields_to_index"] == [
        "tag","stem.tag","tree.id","stem.id",
    ]
    d["admission"]["case_folding"]=True
    with pytest.raises(ValueError,match="literal_tag"):
        mod.validate_source_contract(d)


def test_exact_tag_vs_stem_tag_comparison_preserves_ambiguous_and_missing():
    targets=mod.original_HF453_2021_tag_source(StringIO(_hf453()),expected=4)
    assert targets=={"T1","T2","T3","T4"}
    tr,stem,meta=mod.scan_HF253_prior_identity(StringIO(_hf253()))
    assert meta["n_HF253_original_rows"]==4
    assert meta["n_distinct_nonempty_tree_tags"]==3
    assert meta["n_distinct_nonempty_stem_tags"]==4
    assert meta["n_tree_tags_mapping_to_multiple_distinct_tree_ids"]==0
    assert meta["only_four_identity_columns_indexed"] is True
    assert meta["species_size_status_plot_columns_interpreted"] is False
    result=mod.compare_literal_tag_keys(targets,tr,stem)
    assert result["n_HF453_original_2021_tags"]==4
    assert result["n_exact_tag_column_matches"]==2
    assert result["n_exact_stem_tag_column_matches"]==2
    assert result["n_exact_match_both_columns"]==1
    assert result["n_exact_match_only_tag_column"]==1
    assert result["n_exact_match_only_stem_tag_column"]==1
    assert result["n_unmatched_in_both_2019_keys"]==1
    assert result["identity_match_not_physical_tree_validation"] is True
    assert result["unmatched_2019_tag_not_biological_absence"] is True


def test_ambiguous_original_tree_tag_count_cannot_be_pretended_unique():
    src=_hf253()+"T1,Z9,tree_DIFFERENT,stem_5,ignored,3,A,5\n"
    tree,stem,meta=mod.scan_HF253_prior_identity(StringIO(src))
    assert meta["n_tree_tags_mapping_to_multiple_distinct_tree_ids"]==1
    r=mod.compare_literal_tag_keys({"T1","T2"},tree,stem)
    assert r["n_tag_column_ambiguous_tree_id_matches"]==1


def test_source_exposure_only_uses_four_columns_not_species_diameter_or_status():
    before=mod.scan_HF253_prior_identity(StringIO(_hf253()))
    after=mod.scan_HF253_prior_identity(StringIO(
        _hf253().replace("species_ignored","OTHER_UNKNOWN")
                .replace(",10,A,0.0",",99.9,D,999")
    ))
    assert before==after


def test_url_redirect_refuses_provider_or_version_substitution():
    assert mod.source_url_verified(mod.HF253_ORIGINAL_URL)
    assert mod.source_url_verified(mod.HF253_ORIGINAL_URL.replace(
        "harvardforest.fas.harvard.edu",
        "harvardforest1.fas.harvard.edu",
    ))
    for url in (
        mod.HF253_ORIGINAL_URL.replace("https:","http:"),
        mod.HF253_ORIGINAL_URL+"?version=latest",
        mod.HF253_ORIGINAL_URL.replace("hf253-06","hf253-05"),
        mod.HF253_ORIGINAL_URL.replace("harvardforest.fas.harvard.edu","evil.example"),
    ):
        with pytest.raises(ValueError,match="original_file_url"):
            mod.source_url_verified(url)


def test_same_original_HF453_SHA_is_required_before_any_new_HF253_get(monkeypatch):
    config=json.loads(Path("configs/hf253_hf453_source_identity_prefreeze_v1.json").read_text())
    monkeypatch.setattr(mod,"get_frozen_hf453",lambda path:{
        "sha256":"0"*64,
        "md5":mod.FROZEN_HF453_MD5,
        "n_bytes":mod.FROZEN_HF453_SIZE
    })
    monkeypatch.setattr(mod,"fetch_HF253_provider_bytes",lambda path:
        (_ for _ in ()).throw(AssertionError("new source must not be fetched"))
    )
    with pytest.raises(ValueError,match="known_HF453_source_sha"):
        mod.run(config)


def test_preflight_never_uses_external_bytes_and_mutant_lock_refused(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,"run",lambda config:
        (_ for _ in ()).throw(AssertionError("preflight cannot fetch any source"))
    )
    path=tmp_path/"pre.json"
    monkeypatch.setattr(sys,"argv",["test","--preflight-only","--out",str(path)])
    mod.main()
    receipt=json.loads(path.read_text())
    assert receipt["result"]["status"]=="source_only_preflight_no_original_field_values"
    assert receipt["species_or_size_values_opened"] is False
    assert receipt["HF453_status_CP_or_mortality_reopened"] is False
    assert receipt["biological_effect_estimated"] is False
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_CONTENT.replace(
        "no_favorable_outcome_driven_key_selection=true",
        "no_favorable_outcome_driven_key_selection=false",
    ))
    monkeypatch.setattr(sys,"argv",["test","--execute-lock",str(bad),
                                    "--out",str(tmp_path/"bad.json")])
    with pytest.raises(ValueError,match="lock_mismatch"):
        mod.main()


def test_keeping_ambiguities_is_mandatory_not_configurable():
    cfg=json.loads(Path("configs/hf253_hf453_source_identity_prefreeze_v1.json").read_text())
    assert cfg["admission"]["drop_ambiguous_matches"] is False
    mod.validate_source_contract(cfg)
    cfg["admission"]["drop_ambiguous_matches"]=True
    with pytest.raises(ValueError,match="literal_tag_matching_contract_changed"):
        mod.validate_source_contract(cfg)


def test_v1_preflight_stop_not_presented_as_new_ecology():
    assert mod.PROGRAM.endswith("_v2")
    assert "v1_preflight_source_GET=zero_run_44542568429" in mod.LOCK_CONTENT
    assert mod.FROZEN_HF453_SHA=="0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74"
