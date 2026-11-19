"""Exact theoretical parent leakage under independently allocated stem folds.

No original-source or demographic rows are opened and no actual SDM split is
inspected. This is a *hypothetical assignment-design diagnostic*, conditional
on assigning each source stem independently and uniformly to K folds.

For m stems under one original parent ID, P(parent spans >=2 folds)
= 1 - K**(1-m). These are expected parent-split counts, NOT observed leakage
events, effective N, design effects, effect estimates, or causal conclusions.
"""
from __future__ import annotations

from fractions import Fraction as F
import json
from pathlib import Path


def prob_split_parent(stems:int, folds:int)->F:
    if type(stems) is not int or stems < 1:
        raise ValueError("stems per parent must be positive integer")
    if type(folds) is not int or folds < 2:
        raise ValueError("at least two folds needed")
    return F(1)-F(1,folds**(stems-1))


def bound_fiveplus_bucket(n_groups:int,total_stems:int,
                          *, min_stems:int,max_stems:int,folds:int)->tuple[F,F]:
    """Exact extrema of sum split probabilities under known count/sum/range.

    g(m)=1-K**(1-m) has decreasing integer increments. Therefore the
    minimum concentrates excess stems at the max and the maximum balances
    excess stems as evenly as possible. No unknown original parent IDs needed.
    """
    if any(type(v) is not int for v in (
            n_groups,total_stems,min_stems,max_stems,folds)):
        raise ValueError("integer counts required")
    if n_groups<0 or min_stems<1 or max_stems<min_stems or folds<2:
        raise ValueError("invalid unknown multiplicity range")
    if n_groups==0:
        if total_stems!=0:
            raise ValueError("no groups but positive stem count")
        return F(0),F(0)
    if not n_groups*min_stems <= total_stems <= n_groups*max_stems:
        raise ValueError("original fiveplus bucket impossible")
    extra=total_stems-n_groups*min_stems
    width=max_stems-min_stems
    if width==0:
        answer=n_groups*prob_split_parent(min_stems,folds)
        return answer,answer
    # Extreme source multiplicities: min rows + some max rows and one partial.
    full,rem=divmod(extra,width)
    lower=(full*prob_split_parent(max_stems,folds)
           +(n_groups-full-(1 if rem else 0))
           *prob_split_parent(min_stems,folds))
    if rem:
        lower+=prob_split_parent(min_stems+rem,folds)
    # Balanced multiplicities maximize the sum for concave g.
    q,r=divmod(extra,n_groups)
    upper=((n_groups-r)*prob_split_parent(min_stems+q,folds)
           +r*prob_split_parent(min_stems+q+1,folds))
    if lower>upper:
        raise AssertionError("mathematical extrema reversed")
    return lower,upper


def source_hypothetical_fold_split(parent:dict,*,folds:int=5)->dict:
    if parent.get("schema")!="sdmr.hf253_hf453_parent_tree_first_source_checkpoint.v1":
        raise ValueError("unrecognized immutable source-only parent receipt")
    required={
        "n_HF453_source_StemTag":30808,
        "n_distinct_original_parent_tree_ID_candidates":27688,
        "n_parent_tree_IDs_with_2plus_matched_stems":2331,
        "n_matched_stems_in_multi_stem_trees":5451,
        "max_matched_stems_per_parent_tree_ID":8,
    }
    for key,value in required.items():
        if parent.get(key)!=value:
            raise ValueError("frozen original source unit denominator drift")
    histogram={
        1:parent["n_single_stem_parent_tree_IDs"],
        2:parent["n_parent_tree_IDs_with_two_matched_stems"],
        3:parent["n_parent_tree_IDs_with_three_matched_stems"],
        4:parent["n_parent_tree_IDs_with_four_matched_stems"],
    }
    n5=parent["n_parent_tree_IDs_with_five_or_more_matched_stems"]
    if any(type(n) is not int or n<0 for n in (*histogram.values(),n5)):
        raise ValueError("invalid original source parent histogram")
    if sum(histogram.values())+n5!=27688:
        raise ValueError("original parent unit number inconsistent")
    fiveplus_stems=30808-sum(m*count for m,count in histogram.items())
    if fiveplus_stems!=285 or n5!=51:
        raise ValueError("unknown multiplicity bucket cannot be reused")
    lo,hi=bound_fiveplus_bucket(
        n5,fiveplus_stems,min_stems=5,max_stems=8,folds=folds
    )
    fixed=sum((count*prob_split_parent(m,folds)
               for m,count in histogram.items()),F(0))
    total_lo,total_hi=fixed+lo,fixed+hi
    if not F(0)<=total_lo<=total_hi<=F(27688):
        raise AssertionError("split expectation outside possible parent range")
    return {
        "schema":"sdmr.hf253_parent_fold_split_hypothetical_v1",
        "status":"exact_theoretical_source_unit_split_range",
        "source":"HF253_original_parent_ID_histogram_for_HF453_30808_StemTags",
        "folds":folds,
        "assumption":"independent_uniform_per_STEM_fold_assignment",
        "expected_parent_IDs_appearing_in_multiple_folds_lower":str(total_lo),
        "expected_parent_IDs_appearing_in_multiple_folds_upper":str(total_hi),
        "expected_parent_IDs_appearing_in_multiple_folds_lower_decimal":round(float(total_lo),6),
        "expected_parent_IDs_appearing_in_multiple_folds_upper_decimal":round(float(total_hi),6),
        "multi_stem_parent_ID_denominator":2331,
        "parent_ID_denominator":27688,
        "source_stem_tag_denominator":30808,
        "source_stem_to_parent_count_ratio":round(30808/27688,6),
        "not_actual_fold_assignments":True,
        "not_observed_information_leakage_or_model_bias":True,
        "not_effective_independent_sample_size":True,
        "no_original_biological_or_source_rows_read":True,
        "no_model_fits":True,
        "no_ecological_process_identification":True,
        "single_forest_nontransfer":True,
        "product_A_M5_unchanged":True,
        "product_B_blocked":True,
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("evidence/hf253_hf453_parent_tree_grain_v1.json"))
    p.add_argument("--folds",type=int,default=5)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=source_hypothetical_fold_split(
        json.loads(args.source.read_text()),folds=args.folds
    )
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("POTENTIAL cross-fold parent split expectation; no actual CV result",
          result["expected_parent_IDs_appearing_in_multiple_folds_lower_decimal"],
          result["expected_parent_IDs_appearing_in_multiple_folds_upper_decimal"])
