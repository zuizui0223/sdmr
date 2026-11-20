"""Independent arithmetic-only audit of first corrected HF453 spatial 100m result.

Reads only immutable aggregate source receipt JSON. No source CSV, individual
identifiers, ecological outcome records, model fit, or prospective seed opening.
This is a saved-score consistency check, not a second biological replication.
"""
from __future__ import annotations

from math import isclose
import json
from pathlib import Path

RESULT=Path("evidence/hf453_spatial100_axis_corrected_v2_first_result.json")


def audit_saved_spatial_result(result:dict)->dict:
    if result.get("schema")!="sdmr.hf453_spatial100_axis_corrected_v2_first_result_checkpoint.v1":
        raise ValueError("unknown_original_spatial_result_schema")
    fixed={
        "first_corrected_run":44752128595,
        "artifact_id":14636880470,
        "artifact_sha256":"599e98a6fc590da964dddce6e95372d4b6921251614f1c392b52963c2c121213",
        "original_result_json_sha256":"440f35179a90d50a8fc7a5b1014d6e349ed71a62029b9d518334fe39730de303",
        "source_HF253_sha256":"bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7",
        "source_HF453_sha256":"0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74",
        "first_incorrect_frame_source_hold_run":44749714741,
        "independent_source_only_correct_xy_run":44750670871,
        "n_geo_scored_stems":21769,
        "n_parent_ids_scored":19872,
        "original_full_source_parent_centroid_blocks_100m":35,
        "coverage_of_old_parent_CV_sample":1.0,
    }
    for k,v in fixed.items():
        if result.get(k)!=v:
            raise ValueError("frozen_first_source_spatial_result_changed:"+k)
    if (result["n_geo_excluded_stems"]!=0
        or result["n_group_folds"]!=5
        or result["n_known_death_events"]!=454
        or result["source_missing_xy"]!=0
        or result["source_outside_correct_x700_y500"]!=0):
        raise ValueError("frozen_source_spatial_denominator_or_geometry_changed")
    for name in ("parent_grouped","spatial100_grouped"):
        group=result[name]
        if (group["n_test_parent_overlap"]!=0 or
            group["n_scored_stem_events"]!=21769):
            raise ValueError("parent_independence_or_score_denominator_invalid")
        for metric in ("logloss","brier"):
            b=group[f"{metric}_baseline"]
            p=group[f"{metric}_plus_CP"]
            diff=group[f"delta_{metric}_baseline_minus_CP"]
            if not isclose(b-p,diff,rel_tol=0,abs_tol=1e-9):
                raise ValueError("saved_score_arithmetic_does_not_reconcile:"+name+":"+metric)
    geo=result["spatial100_grouped"]
    folds=geo.get("folds")
    if (len(folds)!=5 or
        sum(f["n_source_blocks"] for f in folds)!=35 or
        sum(f["n_stems"] for f in folds)!=21769 or
        sum(f["n_parents"] for f in folds)!=19872 or
        sum(f["n_known_death"] for f in folds)!=454):
        raise ValueError("geographic_fold_totals_do_not_match_original_cohort")
    if (result["parent_grouped"]["delta_logloss_baseline_minus_CP"]<=0 or
        geo["delta_logloss_baseline_minus_CP"]<=0 or
        geo["delta_brier_baseline_minus_CP"]>=0):
        raise ValueError("metric_signs_reinterpreted_or_original_result_changed")
    for key in ("not_independent_forest_replication","not_statistical_CI_or_p_value",
                "not_causal_process_identification","no_original_status_or_parent_prior_result_changed",
                "no_original_raw_rows_or_identifiers_exported","Product_B_unblocked"):
        required=key!="Product_B_unblocked"
        if result.get(key) is not required:
            raise ValueError("source_nonpromotion_semantics_changed:"+key)
    return {
        "schema":"sdmr.hf453_spatial100_axis_corrected_archive_audit_v1",
        "status":"original_saved_source_spatial_metrics_reconciled",
        "original_first_run":result["first_corrected_run"],
        "n_original_scored_stem_events":21769,
        "n_original_scored_parent_tree_IDs":19872,
        "n_original_source_100m_cells":35,
        "logloss_CP_increment_parent":result["parent_grouped"]["delta_logloss_baseline_minus_CP"],
        "logloss_CP_increment_spatial":geo["delta_logloss_baseline_minus_CP"],
        "brier_CP_increment_spatial":geo["delta_brier_baseline_minus_CP"],
        "interpretation":"small logloss gain in both layouts; spatial Brier worsens; no causal/ecosystem transfer",
        "new_field_source_gets":0,
        "new_model_fits":0,
        "independent_forest_replicates_added":0,
        "product_A_M5_unmodified":True,
        "Product_B_unblocked":False,
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint",type=Path,default=RESULT)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    receipt=audit_saved_spatial_result(json.loads(a.checkpoint.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("Original first corrected spatial result reconciled without source GET/model refit")
