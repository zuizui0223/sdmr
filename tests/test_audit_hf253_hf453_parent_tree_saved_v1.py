"""Source-only parent-tree receipt regression tests (no original files or outcomes)."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

source=Path("scripts/audit_hf253_hf453_parent_tree_saved_v1.py")
spec=importlib.util.spec_from_file_location("hf253_hf453_parent_receipts",source)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def saved():
    p=json.loads(Path("evidence/hf253_hf453_parent_tree_grain_v1.json").read_text())
    l=json.loads(Path("evidence/hf253_hf453_original_stem_tag_crosswalk_v2.json").read_text())
    return p,l


def test_first_original_parent_source_and_multiplicity_reconciles_without_data(saved):
    p,l=saved
    x=mod.audit_parent_receipts(p,l)
    assert x["status"]=="source_only_original_unit_arithmetic_reconciled"
    assert x["n_original_stem_tags"]==30808
    assert x["n_distinct_parent_tree_id_candidates"]==27688
    assert x["n_extra_stems_vs_parent_ids"]==3120
    assert x["n_parent_tree_ids_with_multiple_matched_stems"]==2331
    assert x["n_stem_tags_in_multistem_parent_ids"]==5451
    assert x["n_stems_in_fiveplus_parent_ids"]==285
    assert x["models_fit"]==0
    assert x["biological_values_opened"] is False
    assert x["independent_forest_replication"] is False


@pytest.mark.parametrize("mutator,pattern",[
    (lambda p,l:p.update(n_distinct_original_parent_tree_ID_candidates=27687),
        "original_parent_stem_histogram"),
    (lambda p,l:p.update(n_original_matched_stem_IDs=30807),
        "full_original_stem_parent_denominator"),
    (lambda p,l:p.update(n_ambiguous_stem_parent_ID_mapping=1),
        "full_original_stem_parent_denominator"),
    (lambda p,l:p.update(n_stem_tags_in_multistem_parent_ids=5000),
        "stem_to_parent_excess_or_multi_membership"),
    (lambda p,l:p.update(n_parent_tree_IDs_with_two_matched_stems=1776),
        "original_parent_stem_histogram"),
    (lambda p,l:p.update(max_matched_stems_per_parent_tree_ID=5),
        "five_plus_stem_parent_range"),
    (lambda p,l:p.update(species_DBH_status_CP_growth_or_mortality_values_opened=True),
        "source_only_nonpromotion_contract"),
    (lambda p,l:l.update(exact_match_with_2019_tree_tag=27688),
        "previous_pre_parent_source_receipt_mutated"),
])
def test_immutable_ledger_mutations_are_rejected(saved,mutator,pattern):
    p,l=map(deepcopy,saved)
    mutator(p,l)
    with pytest.raises(ValueError,match=pattern):
        mod.audit_parent_receipts(p,l)
