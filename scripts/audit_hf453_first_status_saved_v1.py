"""Independent archive-only HF453 status arithmetic audit: NO refit / source GET.

Compares aggregate original status counts, frozen source-frame identity,
risk-event partition, CP group partition, and exact missingness bounds.
This is a no-new-data integrity check, NOT a second biological replication.
"""
from __future__ import annotations

from fractions import Fraction as F
import json
from pathlib import Path

SAMPLE_FILE = Path("evidence/hf453_first_observed_status_transition_v1.json")


def audit_saved_field_counts(record: dict) -> dict:
    if record.get("schema") != "sdmr.hf453_single_forest_status_first_open_checkpoint.v1":
        raise ValueError("unknown_or_mutated_HF453_checkpoint_schema")
    if (record.get("source_tags") != 30808 or record.get("source_tag_year_rows") != 123232
            or record.get("original_sha256")
            != "0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74"):
        raise ValueError("frozen_original_source_or_denominator_mismatch")
    years = record.get("source_status_counts", {})
    intervals = record.get("intervals", [])
    if len(intervals) != 3 or [e.get("interval") for e in intervals] != [
        "2021_to_2022", "2022_to_2023", "2023_to_2024"
    ] or [e.get("primary") for e in intervals] != [True, False, False]:
        raise ValueError("primary_secondary_interval_contract_mismatch")
    for yr in (2021, 2022, 2023, 2024):
        raw = years.get(str(yr), years.get(yr))
        if not isinstance(raw, dict) or any(type(x) is not int or x < 0 for x in raw.values()):
            raise ValueError("invalid_annual_original_status_partition")
        if sum(raw.values()) != 30808 or any(
            k not in {"A", "AU", "DC", "DS", "DN", "BLANK", "NA"} for k in raw
        ):
            raise ValueError("annual_source_status_denominator_or_ontology_invalid")
    out = []
    for i, event in enumerate(intervals):
        first, later = 2021+i, 2022+i
        status = years.get(str(first), years.get(first))
        def n(*names: str) -> int:
            return sum(status.get(k,0) for k in names)
        if (event["start_alive"] != n("A","AU")
                or event["start_dead_excluded"] != n("DC","DS")
                or event["start_unknown_excluded"] != n("DN","BLANK","NA")):
            raise ValueError("start_source_status_partition_vs_event_mismatch")
        if event["start_alive"] != sum(event[k] for k in (
            "end_known_dead", "end_known_alive", "end_unknown"
        )):
            raise ValueError("prospective_start_risk_event_lost")
        for nkey, groups in (
            ("end_known_dead","p"),("end_known_alive","z"),("end_unknown","m")
        ):
            if event[nkey] != sum(event[k][groups] for k in (
                "cp_low","cp_high","cp_unknown"
            )):
                raise ValueError("CP_vs_original_event_partition_mismatch")
        if event["cp_unknown_start"] != sum(event["cp_unknown"].values()):
            raise ValueError("unobserved_CP_omitted_from_source_cohort")
        low, high = event["cp_low"], event["cp_high"]
        n0, n1 = sum(low.values()), sum(high.values())
        if n0 < 1 or n1 < 1:
            raise ValueError("cannot_reproduce_CP_comparison_denominator")
        lower = F(high["p"],n1) - F(low["p"]+low["m"],n0)
        upper = F(high["p"]+high["m"],n1) - F(low["p"],n0)
        if str(lower) != event["sharp_delta_low"] or str(upper) != event["sharp_delta_high"]:
            raise ValueError("stored_CP_partial_identification_does_not_reconcile")
        sign = ("negative_for_all_missing_outcomes" if upper < 0 else
                "positive_for_all_missing_outcomes" if lower > 0 else
                "unresolved_including_zero")
        if sign != event["sign"]:
            raise ValueError("source_status_CP_sign_does_not_reconcile")
        out.append({
            "interval":event["interval"],
            "main_predeclared": i == 0,
            "n_source_tagged":30808,
            "n_at_risk_start_alive":event["start_alive"],
            "n_cp_low":n0, "n_cp_high":n1,
            "known_death_low":low["p"], "known_death_high":high["p"],
            "unknown_status_low":low["m"], "unknown_status_high":high["m"],
            "lower_fraction":str(lower), "upper_fraction":str(upper),
            "direction":sign,
        })
    return {
        "schema":"sdmr.hf453_archive_only_independent_arithmetic_audit.v1",
        "status":"original_saved_aggregate_arithmetic_reconciled",
        "n_source_tags":30808,
        "n_tag_year_records":123232,
        "first_source_run":record["first_source_response_run"],
        "first_source_zip_sha256":record["artifact_zip_sha256"],
        "original_raw_HF453_source_accessed":False,
        "new_field_response_opened":False,
        "models_refit":0,
        "independent_forest_replication":False,
        "causal_process_identified":False,
        "original_product_A_M5_untouched":True,
        "Product_B_unblocked":False,
        "intervals":out,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--saved-checkpoint",type=Path,default=SAMPLE_FILE)
    parser.add_argument("--out",type=Path,required=True)
    opts=parser.parse_args()
    result=audit_saved_field_counts(json.loads(opts.saved_checkpoint.read_text()))
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("HF453 saved first-open aggregate 3/3 intervals reconciled, 0 refits")
