"""Frozen aggregate-only HF453 confounding audit: zero new source or refits."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

p=Path("scripts/audit_hf453_postoutcome_saved_v1.py")
spec=importlib.util.spec_from_file_location("hf453_saved_prior_audit",p)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def checkpoint():
    return json.loads(Path("evidence/hf453_postoutcome_prior_species_size_first_result_v1.json").read_text())


def test_first_postoutcome_aggregate_and_nonpromotion_reconcile(checkpoint):
    r=mod.audit_saved_results(checkpoint)
    assert r["status"]=="first_original_aggregate_metric_denominators_reconciled"
    assert r["first_source_run"]==44747246917
    assert r["n_original_CP_known"]==21842
    assert r["n_prior_covariates_complete"]==21774
    assert r["n_parent_cv_scored_stems"]==21769
    assert r["n_parent_cv_test_parents"]==19872
    assert r["parent_grouped_logloss_gain"]==0.000695237
    assert r["strict_strata_eligible_n"]==19063
    assert r["strict_associational_bound_pp"]==[-1.789087,-1.767032]
    assert r["new_original_source_fetches"]==0
    assert r["new_model_fits"]==0
    assert not r["causal_process_identified"]
    assert not r["Product_B_unblocked"]


@pytest.mark.parametrize("mutate,reason",[
    (lambda z:z.update(source_run_id=44747246918),"frozen_source_or_historical_outcome"),
    (lambda z:z.update(n_original_CP_known=21843),"frozen_source_or_historical_outcome"),
    (lambda z:z.update(n_complete_sp_dbh_CP=21775),"frozen_source_covariate_complete_denominator"),
    (lambda z:z.update(n_complete_next_known_for_CV=21770),"frozen_source_covariate_complete_denominator"),
    (lambda z:z.update(strict_strata_eligible_n=19064),"original_covariate_complete_CP_stratum_lost"),
    (lambda z:z.update(loose_standardized_upper_pp=0.001),"signed_fixed_overlap_bounds_changed"),
    (lambda z:z.update(primary_parent_fold_train_test_overlap=1),"original_parent_groupfold_reassignment"),
    (lambda z:z.update(primary_logloss_gain_baseline_minus_plus_CP=0.2),"original_parent_CV_log_loss_arithmetic"),
    (lambda z:z.update(no_causal_competition_or_canopy_effect_identified=False),"source_causal_nonpromotion_boundary"),
])
def test_mutations_cannot_reclassify_original_result(checkpoint,mutate,reason):
    z=deepcopy(checkpoint)
    mutate(z)
    with pytest.raises(ValueError,match=reason):
        mod.audit_saved_results(z)
