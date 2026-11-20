"""Archive-only reconciliation of first HF453 covariate-control result.

Reads aggregate original source receipts only. No HF253/HF453 original CSV,
model refitting, species coefficients, stem IDs, or biological response rows.
An internal arithmetic consistency check is not independent replication.
"""
from __future__ import annotations
import json
from math import isclose
from pathlib import Path

RECEIPT = Path("evidence/hf453_postoutcome_prior_species_size_first_result_v1.json")


def audit_saved_results(z:dict)->dict:
    if z.get("schema")!="sdmr.hf453_postoutcome_prior_species_size_first_result_checkpoint.v1":
        raise ValueError("source_evidence_schema_changed")
    fixed={
        "source_run_id":44747246917,
        "artifact_id":14633317466,
        "artifact_zip_sha256":"63e4e32ec18e15396ceee5981e660807c5821bea55f62be85226b41e19c3798b",
        "result_json_sha256":"cd1b4b42b99bd6dcb380718199a35fa22c3cbab8bb8d3e047c02308647f770e1",
        "source_HF253_SHA256":"bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7",
        "source_HF453_SHA256":"0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74",
        "n_original_2021_alive_stem_events":21846,
        "n_original_CP_known":21842,
        "n_original_next_observed_dead":461,
        "n_original_next_unknown":5,
        "n_parent_tree_IDs_in_original_30808_stem_panel":27688,
    }
    for key, val in fixed.items():
        if z.get(key)!=val:raise ValueError("frozen_source_or_historical_outcome_changed:"+key)
    if (z["n_original_CP_known"]!=z["n_complete_sp_dbh_CP"]+z["n_CP_known_excluded_missing_prior_dbh"]
        or z["n_complete_sp_dbh_CP"]!=z["n_complete_next_known_for_CV"]+5
        or z["n_complete_next_known_for_CV"]!=z["n_complete_next_dead_for_CV"]+z["n_complete_next_alive_for_CV"]
        or z["n_complete_parent_trees_for_CV"]>z["n_parent_tree_IDs_in_original_30808_stem_panel"]):
        raise ValueError("frozen_source_covariate_complete_denominator_drift")
    for label in ("strict","loose"):
        key=label+"_strata_"
        if z[key+"eligible_n"]+z[key+"excluded_n"]!=z["n_complete_sp_dbh_CP"]:
            raise ValueError("original_covariate_complete_CP_stratum_lost:"+label)
        if z[key+"eligible"]>z[key+"total"] if label=="strict" else z[key+"eligible"]>z["strict_strata_total"]:
            raise ValueError("original_CP_stratum_count_impossible")
        lo=z[label+"_standardized_lower_pp"]
        hi=z[label+"_standardized_upper_pp"]
        if not -100<=lo<=hi<=100 or hi>=0:
            raise ValueError("signed_fixed_overlap_bounds_changed:"+label)
        if z[label+"_standardized_missingness_sign"]!="negative_for_all_unknown_outcomes":
            raise ValueError("source_missingness_partial_status_changed:"+label)
    if z["primary_parent_fold_count"]!=5 or z["primary_parent_fold_train_test_overlap"]!=0:
        raise ValueError("original_parent_groupfold_reassignment")
    if not isclose(
        z["primary_equal_parent_logloss_baseline"]-z["primary_equal_parent_logloss_plus_CP"],
        z["primary_logloss_gain_baseline_minus_plus_CP"],abs_tol=5e-10):
        raise ValueError("original_parent_CV_log_loss_arithmetic_inconsistent")
    if not isclose(
        z["secondary_equal_parent_brier_baseline"]-z["secondary_equal_parent_brier_plus_CP"],
        z["secondary_brier_gain_baseline_minus_plus_CP"],abs_tol=6e-10):
        raise ValueError("original_parent_CV_brier_arithmetic_inconsistent")
    for key in (
        "original_raw_stem_tree_ID_exported",
        "no_causal_competition_or_canopy_effect_identified",
        "no_independent_forest_validation",
        "no_cross_biome_transfer_claim",
        "no_sampling_CI_or_p_value",
        "product_A_not_promoted_unchanged",
        "product_B_blocked",
    ):
        expected=key!="original_raw_stem_tree_ID_exported"
        if z.get(key) is not expected:
            raise ValueError("source_causal_nonpromotion_boundary_changed:"+key)
    return {
        "schema":"sdmr.hf453_postoutcome_saved_arithmetic_audit.v1",
        "status":"first_original_aggregate_metric_denominators_reconciled",
        "first_source_run":z["source_run_id"],
        "n_original_CP_known":21842,
        "n_prior_covariates_complete":z["n_complete_sp_dbh_CP"],
        "n_parent_cv_scored_stems":z["n_complete_next_known_for_CV"],
        "n_parent_cv_test_parents":z["n_complete_parent_trees_for_CV"],
        "parent_grouped_logloss_gain":z["primary_logloss_gain_baseline_minus_plus_CP"],
        "strict_strata_eligible_n":z["strict_strata_eligible_n"],
        "strict_associational_bound_pp":[z["strict_standardized_lower_pp"],z["strict_standardized_upper_pp"]],
        "new_original_source_fetches":0,
        "new_model_fits":0,
        "new_independent_ecological_replications":0,
        "causal_process_identified":False,
        "Product_B_unblocked":False,
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint",type=Path,default=RECEIPT)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    data=audit_saved_results(json.loads(a.checkpoint.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("Frozen HF453 postoutcome source aggregate reconciled, no source or model reopening")
