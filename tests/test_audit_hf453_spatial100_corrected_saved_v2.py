"""Immutable HF453 source-corrected spatial aggregate only, no source/model."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

p=Path("scripts/audit_hf453_spatial100_corrected_saved_v2.py")
spec=importlib.util.spec_from_file_location("saved_hf453_spatial",p)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

@pytest.fixture
def saved():
    return json.loads(Path("evidence/hf453_spatial100_axis_corrected_v2_first_result.json").read_text())

def test_immutable_first_spatial_metric_signs_and_full_35_cells(saved):
    x=mod.audit_saved_spatial_result(saved)
    assert x["status"]=="original_saved_source_spatial_metrics_reconciled"
    assert x["original_first_run"]==44752128595
    assert x["n_original_scored_stem_events"]==21769
    assert x["n_original_scored_parent_tree_IDs"]==19872
    assert x["n_original_source_100m_cells"]==35
    assert x["logloss_CP_increment_parent"]==0.000695237
    assert x["logloss_CP_increment_spatial"]==0.0005472246
    assert x["brier_CP_increment_spatial"]==-0.0000267881
    assert x["new_field_source_gets"]==0
    assert x["new_model_fits"]==0
    assert x["independent_forest_replicates_added"]==0
    assert x["Product_B_unblocked"] is False

@pytest.mark.parametrize("change,error",[
    (lambda x:x.update(n_geo_scored_stems=21768),"frozen_first_source_spatial_result_changed"),
    (lambda x:x.update(source_outside_correct_x700_y500=1),"frozen_source_spatial_denominator"),
    (lambda x:x["parent_grouped"].update(n_test_parent_overlap=1),"parent_independence"),
    (lambda x:x["spatial100_grouped"].update(delta_logloss_baseline_minus_CP=0),"saved_score_arithmetic"),
    (lambda x:x["spatial100_grouped"].update(delta_brier_baseline_minus_CP=0.1),"saved_score_arithmetic"),
    (lambda x:x["spatial100_grouped"]["folds"][0].update(n_source_blocks=6),"geographic_fold_totals"),
    (lambda x:x.update(not_causal_process_identification=False),"source_nonpromotion_semantics"),
    (lambda x:x.update(Product_B_unblocked=True),"source_nonpromotion_semantics"),
])
def test_mutation_cannot_falsely_claim_original_spatial_or_causal_result(saved,change,error):
    x=deepcopy(saved)
    change(x)
    with pytest.raises(ValueError,match=error):
        mod.audit_saved_spatial_result(x)
