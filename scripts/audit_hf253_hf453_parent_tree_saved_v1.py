"""Independent, no-source HF253→HF453 parent-tree first receipt audit.

Recomputes physical parent-ID and original stem-tag denominators from the
immutable aggregate original source-only result. Does NOT fetch or inspect
tree/stem IDs, biological outcomes, species, DBH or original CSV.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

MAIN = Path("evidence/hf253_hf453_parent_tree_grain_v1.json")
CROSSWALK = Path("evidence/hf253_hf453_original_stem_tag_crosswalk_v2.json")


def audit_parent_receipts(parent:dict, link:dict)->dict:
    if parent.get("schema")!="sdmr.hf253_hf453_parent_tree_first_source_checkpoint.v1":
        raise ValueError("original_parent_receipt_schema_mismatch")
    if link.get("schema")!="sdmr.hf253_hf453_first_original_stem_tag_crosswalk_checkpoint.v1":
        raise ValueError("original_crosswalk_schema_mismatch")
    expected={
        "original_HF253_sha256":"bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7",
        "original_HF453_sha256":"0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74",
        "original_artifact_zip_sha256":"1528147b05ef632b468a51d5c77400c8041f5842bf5cd36047c202edfbe92930",
        "original_inner_result_json_sha256":"a60b2adb646876cac411c60be635393f3a56322a22c1df8683033275820ea2aa",
        "first_source_run_id":44544941037,
        "scientific_status":"parent_tree_identity_mapped_source_only",
    }
    for name,value in expected.items():
        if parent.get(name)!=value:
            raise ValueError("frozen_original_parent_source_receipt_changed:"+name)
    if (link.get("HF253_first_SHA256")!=parent["original_HF253_sha256"]
            or link.get("HF453_source_SHA256")!=parent["original_HF453_sha256"]
            or link.get("first_source_run")!=44543555701):
        raise ValueError("source_lineage_versions_do_not_reconcile")
    total=parent["n_HF453_source_StemTag"]
    stem=parent["n_exact_HF253_stem_tag_matches"]
    resolved=parent["n_original_matched_stem_IDs"]
    unique=parent["n_distinct_original_parent_tree_ID_candidates"]
    counts=[
        parent["n_single_stem_parent_tree_IDs"],
        parent["n_parent_tree_IDs_with_two_matched_stems"],
        parent["n_parent_tree_IDs_with_three_matched_stems"],
        parent["n_parent_tree_IDs_with_four_matched_stems"],
        parent["n_parent_tree_IDs_with_five_or_more_matched_stems"],
    ]
    if any(type(n) is not int or n<0 for n in [total,stem,resolved,unique,*counts]):
        raise ValueError("invalid_negative_or_nonnumeric_source_count")
    if (total!=30808 or stem!=total or resolved!=total or unique<1
            or link.get("exact_match_with_2019_stem_tag")!=total
            or parent["n_unmatched_tags"]!=0
            or parent["n_missing_original_parent_or_stem_ID"]!=0
            or parent["n_ambiguous_stem_parent_ID_mapping"]!=0):
        raise ValueError("full_original_stem_parent_denominator_not_reconciled")
    if sum(counts)!=unique or unique!=27688:
        raise ValueError("original_parent_stem_histogram_not_reconciled")
    single,two,three,four,fiveplus=counts
    multi=two+three+four+fiveplus
    if multi!=parent["n_parent_tree_IDs_with_2plus_matched_stems"]:
        raise ValueError("multi_stem_parent_count_mismatch")
    if (stem-unique!=parent["excess_stem_tags_beyond_distinct_parent_IDs"]
            or stem-single!=parent["n_matched_stems_in_multi_stem_trees"]):
        raise ValueError("stem_to_parent_excess_or_multi_membership_mismatch")
    last_stems=stem-single-2*two-3*three-4*four
    max_stems=parent["max_matched_stems_per_parent_tree_ID"]
    if last_stems<5*fiveplus or last_stems>max_stems*fiveplus or max_stems!=8:
        raise ValueError("five_plus_stem_parent_range_impossible")
    if (link.get("exact_match_with_2019_tree_tag")!=27673
            or link.get("exact_match_only_stem_tag")!=3135
            or link.get("original_parent_treeID_count_for_30808_matched_stems") is not None):
        raise ValueError("previous_pre_parent_source_receipt_mutated")
    if (parent.get("species_DBH_status_CP_growth_or_mortality_values_opened") is not False
            or parent.get("earlier_HF453_status_effect_reclassified") is not False
            or parent.get("independent_biological_replication") is not False
            or parent.get("causal_process_identified") is not False
            or parent.get("product_B_unblocked") is not False):
        raise ValueError("source_only_nonpromotion_contract_violated")
    return {
        "schema":"sdmr.hf253_hf453_parent_tree_first_receipt_independent_audit.v1",
        "status":"source_only_original_unit_arithmetic_reconciled",
        "n_original_stem_tags":stem,
        "n_distinct_parent_tree_id_candidates":unique,
        "n_extra_stems_vs_parent_ids":stem-unique,
        "n_parent_tree_ids_with_multiple_matched_stems":multi,
        "n_stem_tags_in_multistem_parent_ids":stem-single,
        "n_stems_in_fiveplus_parent_ids":last_stems,
        "n_source_first_run":parent["first_source_run_id"],
        "source_lineage_first_match_run":link["first_source_run"],
        "original_HF253_CSV_opened":False,
        "original_HF453_CSV_opened":False,
        "biological_values_opened":False,
        "models_fit":0,
        "new_biological_or_causal_claim":False,
        "independent_forest_replication":False,
        "Product_B_unblocked":False,
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--parent",type=Path,default=MAIN)
    p.add_argument("--crosswalk",type=Path,default=CROSSWALK)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    x=audit_parent_receipts(json.loads(args.parent.read_text()),
                            json.loads(args.crosswalk.read_text()))
    args.out.parent.mkdir(exist_ok=True,parents=True)
    args.out.write_text(json.dumps(x,sort_keys=True,indent=2)+"\n")
    print("SOURCE-ONLY HF253 parent source receipt independently reconciled")
