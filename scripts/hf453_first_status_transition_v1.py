#!/usr/bin/env python3
"""One prespecified HF453 observed-status transition opening, one forest only.

Reads four original columns from a SHA/MD5/byte-identical publisher source:
StemTag, year, status, CP. Other columns pass through a transient CSV tokenizer
but are never interpreted, logged, or retained. This is a first NEW descriptive
biological endpoint, explicitly NOT causal ecology or independent biome transfer.

Primary interval 2021→2022; 2022→2023 and 2023→2024 secondary descriptions.
Observed death: DC/DS; observed alive: A/AU; DN/NA/blank unresolved.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from hf453_tag_year_identity_source_only_v2 import (
    _download_and_hash_original, EXPECTED_ORIGINAL_SHA256,
    EXPECTED_ORIGINAL_NBYTES, PUBLISHER_MD5,
)
from sdmr.observation_partial_identification_v1 import (
    BinaryOpportunity, sharp_binary_contrast_bounds,
)

SOURCE = "harvard_forest_hf453_2026_v1"
PROGRAM = "sdmr_hf453_2021_2024_transitions_first_open_v1"
CONFIG = "configs/hf453_demographic_transition_first_open_v1.json"
YEAR_ORDER = (2021, 2022, 2023, 2024)
ALIVE = frozenset({"A", "AU"})
DEAD_DIRECT = frozenset({"DC", "DS"})
MISSING_END = frozenset({"DN", "", "NA"})
VALID_STATUSES = frozenset(ALIVE | DEAD_DIRECT | MISSING_END)
CANOPY_GROUPS = {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1}
MISSING_CP = frozenset({"", "NA"})
LOCK_CONTENT = "\n".join([
    f"program={PROGRAM}",
    "first_biological_response_opening=true",
    "scope=within_one_HF453_published_tagged_cohort_only",
    f"source={SOURCE}",
    f"fixed_source_sha256={EXPECTED_ORIGINAL_SHA256}",
    f"fixed_source_bytes={EXPECTED_ORIGINAL_NBYTES}",
    f"fixed_source_md5={PUBLISHER_MD5}",
    "primary=2021_to_2022",
    "secondary=2022_to_2023,2023_to_2024",
    "endpoint=observed_DC_or_DS_after_start_A_or_AU",
    "DN_missing_or_unfound=unknown_never_observed_death",
    "canopy_context=start_year_CP_1_2_vs_3_4_5",
    "strict_source_counts=30808_tags_x_4_years",
    "no_row_or_individual_identifiers_archived=true",
    "no_causal_or_multi_biome_promotion=true",
    "M5_ProductA_unchanged_ProductB_blocked=true",
]) + "\n"


def validate_contract(config: dict) -> None:
    checks = {
        "schema": "sdmr.hf453.single_forest_demographic_transition_preregistered.v1",
        "status": "pre_outcome_freeze",
        "program": "hf453_2021_2024_tagged_cohort_health_transitions_v1",
        "parse_fields": ["StemTag", "year", "status", "CP"],
        "allowed_status_codes": ["A", "AU", "DC", "DN", "DS"],
        "missing_status_codes": ["", "NA"],
        "allowed_canopy_codes": ["1", "2", "3", "4", "5"],
        "missing_canopy_codes": ["", "NA"],
        "primary_interval": [2021, 2022],
        "secondary_intervals": [[2022, 2023], [2023, 2024]],
    }
    for k, v in checks.items():
        if config.get(k) != v:
            raise ValueError(f"preregistered_{k}_mismatch")
    src = config["source"]
    frame = config["source_frame"]
    if (src["source_sha256"] != EXPECTED_ORIGINAL_SHA256
            or src["publisher_md5"] != PUBLISHER_MD5
            or src["n_bytes"] != EXPECTED_ORIGINAL_NBYTES
            or frame["tag_count"] != 30808 or frame["n_tag_year"] != 123232
            or frame["years"] != list(YEAR_ORDER)
            or frame["expected_per_year"] != 30808):
        raise ValueError("original_source_or_identity_frame_contract_changed")
    if config["end_visually_observed_dead"] != ["DC", "DS"]:
        raise ValueError("dead_status_ontology_changed")
    if config["end_unknown_or_unfound"] != ["DN", "", "NA"]:
        raise ValueError("unknown_status_ontology_changed")
    if config["canopy_context"]["lower_light"] != ["1", "2"]:
        raise ValueError("canopy_lower_threshold_changed")
    if config["canopy_context"]["greater_light"] != ["3", "4", "5"]:
        raise ValueError("canopy_greater_threshold_changed")


def parse_four_published_fields(stream, *, expected_tags: int,
                                expected_per_year: int) -> tuple[dict, dict]:
    """Read exactly four field values; reject source alteration or invalid codes."""
    reader = csv.reader(stream)
    header = next(reader, None)
    if header and header[0].startswith("\xef\xbb\xbf"):
        header[0] = header[0][3:]
    if header is None or len(header) != len(set(header)):
        raise ValueError("source_header_invalid_or_duplicated")
    required = ("StemTag", "year", "status", "CP")
    if any(col not in header for col in required):
        raise ValueError("missing_expected_original_columns")
    tag_ix, yr_ix, status_ix, cp_ix = [header.index(x) for x in required]
    panel: dict[str, dict[int, tuple[str, str]]] = {}
    year_counts = Counter()
    status_counts: dict[int, Counter[str]] = {y: Counter() for y in YEAR_ORDER}
    n_rows = 0
    for row in reader:
        n_rows += 1
        if len(row) != len(header):
            raise ValueError("source_row_width_mismatch")
        tag, yearstr, status, cp = (
            row[tag_ix], row[yr_ix], row[status_ix], row[cp_ix]
        )
        if (not tag or not tag.isascii() or tag != tag.strip()
                or not yearstr.isascii() or yearstr not in ("2021", "2022", "2023", "2024")):
            raise ValueError("tag_or_census_year_invalid")
        if not status.isascii() or status not in VALID_STATUSES:
            raise ValueError("unregistered_original_status_code")
        # CP is a biological context measured only on some occasions.
        # Unrecognized CP values, when nonmissing, are an ontology STOP.
        if not cp.isascii() or cp not in CANOPY_GROUPS and cp not in MISSING_CP:
            raise ValueError("unregistered_original_canopy_code")
        yr = int(yearstr)
        annual = panel.setdefault(tag, {})
        if yr in annual:
            raise ValueError("duplicate_original_tag_year")
        annual[yr] = (status, cp)
        status_counts[yr][status if status else "BLANK"] += 1
        year_counts[yr] += 1
    if n_rows != expected_tags * len(YEAR_ORDER) or len(panel) != expected_tags:
        raise ValueError("source_tag_or_total_frame_changed")
    if any(year_counts[y] != expected_per_year for y in YEAR_ORDER):
        raise ValueError("source_year_denominator_changed")
    if any(set(annual) != set(YEAR_ORDER) for annual in panel.values()):
        raise ValueError("missing_published_tag_year_record")
    return panel, {
        "n_source_rows": n_rows,
        "n_distinct_tags": len(panel),
        "per_year_record_counts": {str(y): year_counts[y] for y in YEAR_ORDER},
        "status_code_counts_by_year": {
            str(y): {k: status_counts[y][k] for k in sorted(status_counts[y])}
            for y in YEAR_ORDER
        },
        "all_tag_year_records_present": True,
        "source_status_codes_measured_not_directly_verified_death": True,
    }


def classify_interval(panel: dict, first: int, second: int) -> dict:
    counts = {
        "n_published_tags": len(panel),
        "n_start_observed_alive": 0,
        "n_start_not_at_risk_dead": 0,
        "n_start_not_at_risk_DN_or_missing": 0,
        "n_end_observed_dead_DC_DS": 0,
        "n_end_observed_alive_A_AU": 0,
        "n_end_unknown_DN_or_missing": 0,
        "n_baseline_CP_unknown": 0,
    }
    by_cp = {0: Counter(), 1: Counter()}
    unknown_context = Counter()
    for years in panel.values():
        start, cp = years[first]
        end, _ = years[second]
        if start not in ALIVE:
            k = ("n_start_not_at_risk_dead" if start in DEAD_DIRECT
                 else "n_start_not_at_risk_DN_or_missing")
            counts[k] += 1
            continue
        counts["n_start_observed_alive"] += 1
        state = "p" if end in DEAD_DIRECT else "z" if end in ALIVE else "m"
        counts[{
            "p": "n_end_observed_dead_DC_DS",
            "z": "n_end_observed_alive_A_AU",
            "m": "n_end_unknown_DN_or_missing",
        }[state]] += 1
        if cp in CANOPY_GROUPS:
            by_cp[CANOPY_GROUPS[cp]][state] += 1
        else:
            unknown_context[state] += 1
            counts["n_baseline_CP_unknown"] += 1

    n = counts["n_start_observed_alive"]
    assert n == sum(counts[k] for k in (
        "n_end_observed_dead_DC_DS", "n_end_observed_alive_A_AU",
        "n_end_unknown_DN_or_missing",
    ))
    out: dict[str, object] = {
        "interval": f"{first}_to_{second}",
        **counts,
        "canopy_low_light": {
            k: int(by_cp[0][k]) for k in ("p", "z", "m")
        },
        "canopy_greater_light": {
            k: int(by_cp[1][k]) for k in ("p", "z", "m")
        },
        "canopy_not_measured": {
            k: int(unknown_context[k]) for k in ("p", "z", "m")
        },
        "status_claim_scope": "observed_original_source_coded_transition_only",
        "independent_forest_replication": False,
    }
    n0 = sum(by_cp[0].values())
    n1 = sum(by_cp[1].values())
    if n0 == 0 or n1 == 0:
        out["identified_CP_contrast"] = {
            "status": "unavailable_zero_measured_canopy_group",
            "sign": "unavailable",
            "lower": None, "upper": None,
        }
    else:
        b = sharp_binary_contrast_bounds(
            BinaryOpportunity("lower_light",by_cp[0]["p"],by_cp[0]["z"],by_cp[0]["m"],n0),
            BinaryOpportunity("greater_light",by_cp[1]["p"],by_cp[1]["z"],by_cp[1]["m"],n1),
            complete_source_frame_verified=True,
            actual_recorded_negatives_verified=True,
        )
        out["identified_CP_contrast"] = {
            "status": "within_single_forest_associational_partial_bounds",
            "lower": str(b.lower),
            "upper": str(b.upper),
            "sign": b.sign,
            "underlying_associational_estimand": b.target,
            "field_biological_status_opened": True,
            "causal_process_identified": False,
            "not_a_confidence_interval": True,
            "unrestricted_outcome_dependent_missingness": True,
        }
    out["CP_contrast_population_scope"] = (
        "source_published_tagged_cohort_alive_at_start_and_CP_observed"
    )
    out["source_frame_assumed_complete_only_within_original_published_tags"] = True
    out["no_claim_of_unobserved_tree_or_sampling_opportunity_completeness"] = True
    return out


def run_first_response_opening(config: dict) -> dict:
    validate_contract(config)
    with tempfile.TemporaryDirectory(prefix="hf453_first_status_source_") as temp:
        path = Path(temp) / "raw_original_not_archived.csv"
        checked = _download_and_hash_original(path)
        if (checked["sha256"] != EXPECTED_ORIGINAL_SHA256 or
                checked["md5"] != PUBLISHER_MD5 or
                checked["n_bytes"] != EXPECTED_ORIGINAL_NBYTES):
            raise ValueError("original_HF453_source_digest_or_byte_count_changed")
        with path.open("r", encoding="latin-1", newline="") as f:
            panel, frame = parse_four_published_fields(
                f, expected_tags=30808, expected_per_year=30808,
            )
        primary = classify_interval(panel, 2021, 2022)
        secondary = [
            classify_interval(panel, 2022, 2023),
            classify_interval(panel, 2023, 2024),
        ]
        return {
            "status": "within_single_forest_descriptive_status_opened",
            "original_source_hash_verified_before_response": True,
            "original_source_sha256": checked["sha256"],
            "source_frame": frame,
            "primary": primary,
            "secondary_descriptive": secondary,
            "no_individual_or_raw_row_saved": True,
            "no_species_specific_causal_estimate": True,
            "no_independent_forest_replication": True,
            "no_product_A_or_M5_reopening": True,
            "Product_B_unblocked": False,
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=Path(CONFIG))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--execute-lock", type=Path)
    args = ap.parse_args()
    if args.preflight_only == (args.execute_lock is not None):
        ap.error("exactly one of --preflight-only or --execute-lock required")
    config = json.loads(args.config.read_text())
    validate_contract(config)
    if args.execute_lock and args.execute_lock.read_text() != LOCK_CONTENT:
        raise ValueError("new_single_forest_response_opening_lock_mismatch")
    if args.preflight_only:
        r = {"status": "preflight_only_no_response_opened"}
    else:
        r = run_first_response_opening(config)
    output = {
        "schema": "sdmr.hf453_first_within_forest_status_transition.v1",
        "program": PROGRAM,
        "preflight": args.preflight_only,
        "response_original_HF453": not args.preflight_only,
        "target_source": SOURCE,
        "single_forest": True,
        "causal_effect_estimated": False,
        "multi_biome_generalization_tested": False,
        "no_p_values_or_confidence_intervals": True,
        "no_raw_source_rows_retained": True,
        "M5_ProductA_unchanged": True,
        "Product_B_unblocked": False,
        "result": r,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print("HF453 first single-forest status opening:",r["status"])
    print("No raw individuals, model-selection inference or causal effect released")


if __name__ == "__main__":
    main()
