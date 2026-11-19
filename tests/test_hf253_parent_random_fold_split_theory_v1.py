"""Exact hypothetical fold parent-split arithmetic; never opens actual SDM data."""
from copy import deepcopy
from fractions import Fraction as F
import importlib.util
from itertools import product
import json
from pathlib import Path
import sys

import pytest

script=Path("scripts/hf253_parent_random_fold_split_theory_v1.py")
spec=importlib.util.spec_from_file_location("parent_fold_split_theory_v1",script)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def test_parent_split_exact_random_assignment_formula():
    assert mod.prob_split_parent(1,5)==F(0)
    assert mod.prob_split_parent(2,5)==F(4,5)
    assert mod.prob_split_parent(3,5)==F(24,25)
    assert mod.prob_split_parent(4,5)==F(124,125)
    with pytest.raises(ValueError):
        mod.prob_split_parent(1,1)
    with pytest.raises(ValueError):
        mod.prob_split_parent(0,5)


def test_unknown_original_fiveplus_bucket_exact_extrema():
    lo,hi=mod.bound_fiveplus_bucket(
        51,285,min_stems=5,max_stems=8,folds=5
    )
    g=lambda m:mod.prob_split_parent(m,5)
    assert lo==10*g(8)+41*g(5)
    assert hi==30*g(6)+21*g(5)
    assert lo<=hi
    assert 50 < float(lo) < float(hi) < 51


def test_extrema_match_brute_force_for_small_integer_buckets():
    for n in (1,2,3):
        for total in range(2*n,4*n+1):
            feasible=[
                sum((mod.prob_split_parent(m,3) for m in values),F(0))
                for values in product((2,3,4),repeat=n)
                if sum(values)==total
            ]
            if not feasible:
                continue
            lo,hi=mod.bound_fiveplus_bucket(
                n,total,min_stems=2,max_stems=4,folds=3
            )
            assert lo==min(feasible)
            assert hi==max(feasible)


def test_actual_aggregate_yields_tight_conditional_fivefold_bound():
    evidence=json.loads(Path("evidence/hf253_hf453_parent_tree_grain_v1.json").read_text())
    x=mod.source_hypothetical_fold_split(evidence,folds=5)
    assert x["source_stem_to_parent_count_ratio"]==round(30808/27688,6)
    assert x["multi_stem_parent_ID_denominator"]==2331
    assert x["parent_ID_denominator"]==27688
    assert x["expected_parent_IDs_appearing_in_multiple_folds_lower_decimal"]==1958.966272
    assert x["expected_parent_IDs_appearing_in_multiple_folds_upper_decimal"]==1958.9888
    assert x["assumption"]=="independent_uniform_per_STEM_fold_assignment"
    assert x["not_actual_fold_assignments"]
    assert x["not_observed_information_leakage_or_model_bias"]
    assert x["not_effective_independent_sample_size"]
    assert x["no_original_biological_or_source_rows_read"]
    assert x["no_model_fits"]


def test_no_silent_source_denominator_mutation():
    evidence=json.loads(Path("evidence/hf253_hf453_parent_tree_grain_v1.json").read_text())
    for key,value in (
        ("n_HF453_source_StemTag",30807),
        ("n_distinct_original_parent_tree_ID_candidates",27689),
        ("max_matched_stems_per_parent_tree_ID",9),
        ("n_parent_tree_IDs_with_five_or_more_matched_stems",52),
    ):
        broken=deepcopy(evidence)
        broken[key]=value
        with pytest.raises(ValueError):
            mod.source_hypothetical_fold_split(broken,folds=5)


def test_bucket_invalid_counts_refuse_instead_of_extrapolating():
    with pytest.raises(ValueError):
        mod.bound_fiveplus_bucket(2,100,min_stems=5,max_stems=8,folds=5)
    with pytest.raises(ValueError):
        mod.bound_fiveplus_bucket(-1,0,min_stems=5,max_stems=8,folds=5)
