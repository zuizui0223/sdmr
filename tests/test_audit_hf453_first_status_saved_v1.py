"""No-source, no-refit regression tests for HF453 archived original first-opening."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SRC=Path("scripts/audit_hf453_first_status_saved_v1.py")
spec=importlib.util.spec_from_file_location("saved_hf453_audit_v1",SRC)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def receipt():
    return json.loads(Path("evidence/hf453_first_observed_status_transition_v1.json").read_text())


def test_full_three_intervals_reconcile_without_fitting(receipt):
    r=mod.audit_saved_field_counts(receipt)
    assert r["status"]=="original_saved_aggregate_arithmetic_reconciled"
    assert r["n_source_tags"]==30808 and r["n_tag_year_records"]==123232
    assert r["first_source_run"]==44540469560
    assert r["original_raw_HF453_source_accessed"] is False
    assert r["new_field_response_opened"] is False
    assert r["models_refit"]==0
    assert r["independent_forest_replication"] is False
    assert len(r["intervals"])==3
    assert r["intervals"][0]["main_predeclared"] is True
    assert [x["direction"] for x in r["intervals"]]==[
        "negative_for_all_missing_outcomes"]*3
    assert r["intervals"][0]["lower_fraction"]=="-5677/296140"
    assert r["intervals"][0]["upper_fraction"]=="-16613/888420"


@pytest.mark.parametrize("mutation,expect",[
    (lambda x: x.update(source_tags=30807),
        "frozen_original_source_or_denominator"),
    (lambda x: x["source_status_counts"]["2021"].update(A=12846),
        "annual_source_status_denominator"),
    (lambda x: x["intervals"][0].update(start_alive=21845),
        "start_source_status_partition"),
    (lambda x: x["intervals"][0]["cp_low"].update(p=324),
        "CP_vs_original_event_partition"),
    (lambda x: x["intervals"][0].update(sharp_delta_low="-1/999"),
        "partial_identification_does_not_reconcile"),
    (lambda x: x["intervals"][0].update(sign="unresolved_including_zero"),
        "CP_sign_does_not_reconcile"),
])
def test_source_count_or_result_mutations_fail_closed(receipt,mutation,expect):
    altered=deepcopy(receipt)
    mutation(altered)
    with pytest.raises(ValueError,match=expect):
        mod.audit_saved_field_counts(altered)


def test_original_m5_product_a_and_b_are_not_unblocked(receipt):
    r=mod.audit_saved_field_counts(receipt)
    assert r["causal_process_identified"] is False
    assert r["original_product_A_M5_untouched"] is True
    assert r["Product_B_unblocked"] is False
