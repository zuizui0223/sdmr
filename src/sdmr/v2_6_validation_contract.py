"""Immutable fresh-validation decision contract for Product-A v2.6."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PANELS = ("panel_D1", "panel_D2", "panel_D3")
VALIDATION_SPECS = {
    "panel_D1": (("soft_threshold", 501), ("omitted_driver", 511), ("observation_confounded", 521)),
    "panel_D2": (("soft_threshold", 502), ("omitted_driver", 512), ("observation_confounded", 522)),
    "panel_D3": (("soft_threshold", 503), ("omitted_driver", 513), ("observation_confounded", 523)),
}
SOURCE_CALIBRATION_RUN_ID = "32249349433"
SOURCE_CALIBRATION_HEAD_SHA = "6dde7706eabd1a4279d2c9f142922f8a67ca2b8f"
SOURCE_CALIBRATION_ARTIFACT_NAME = "product-a-v2-6-frozen-calibration"
PRODUCTS = (
    "canonical_auc_point",
    "complete_adequate_certificate",
    "v2_3_mean_pareto_certificate",
    "v2_6_exclusion_calibrated_certificate",
)
PROCESS_UNIVERSE = ("temperature", "water", "soil", "seasonality", "noise")
DECISION_STATES = (
    "v2_6_supported",
    "v2_6_process_only",
    "v2_6_boundary_only",
    "v2_6_not_supported",
    "v2_6_unavailable",
)


def load_v2_6_validation_contract(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_6_predeclared_fresh_validation_decision_contract":
        raise ValueError("v2.6 validation purpose changed")
    for key in (
        "scientific_promotion_run",
        "scientific_promotion_allowed",
        "real_empirical_data_read",
        "old_external_sealed_outcomes_read",
        "validation_truth_read_before_all_products_frozen",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"v2.6 validation requires {key}=false")

    source = payload.get("source_calibration", {})
    if str(source.get("run_id")) != SOURCE_CALIBRATION_RUN_ID:
        raise ValueError("v2.6 source calibration run changed")
    if str(source.get("head_sha")) != SOURCE_CALIBRATION_HEAD_SHA:
        raise ValueError("v2.6 source calibration head changed")
    if source.get("artifact_name") != SOURCE_CALIBRATION_ARTIFACT_NAME:
        raise ValueError("v2.6 source calibration artifact name changed")
    if source.get("must_be_completed_success_before_validation_workers") is not True:
        raise ValueError("v2.6 validation cannot start before successful calibration")
    if source.get("artifact_digest_recorded_before_validation_workers") is not True:
        raise ValueError("v2.6 validation must record calibration digest pretruth")

    raw = payload.get("validation", {})
    if tuple(raw) != PANELS:
        raise ValueError("v2.6 validation panel order changed")
    for panel in PANELS:
        observed = tuple((str(row["family"]), int(row["seed"])) for row in raw[panel])
        if observed != VALIDATION_SPECS[panel]:
            raise ValueError(f"v2.6 validation taxa changed for {panel}")
    seeds = [seed for panel in PANELS for _, seed in VALIDATION_SPECS[panel]]
    if len(seeds) != len(set(seeds)) or min(seeds) <= 472:
        raise ValueError("v2.6 validation seeds are not unique and unseen after calibration")

    worker = payload.get("worker_contract", {})
    expected_worker = {
        "role": "validation",
        "n_worker_cells": 54,
        "groups": ["base", "noise", "seasonality", "soil", "temperature", "water"],
        "M_specs": ["m_core", "m_mid", "m_wide"],
        "full_fit_code": 9,
        "spatial_refit_codes": [0, 1, 2, 3, 4],
        "validation_role_offset": 10000000,
        "candidate_selection_allowed": False,
        "scientific_threshold_tuning_allowed": False,
        "generating_truth_read_by_worker": False,
    }
    if worker != expected_worker:
        raise ValueError("v2.6 validation worker contract changed")
    if tuple(payload.get("products", ())) != PRODUCTS:
        raise ValueError("v2.6 validation products changed")

    process = payload.get("process_certificate", {})
    if tuple(process.get("process_universe", ())) != PROCESS_UNIVERSE:
        raise ValueError("v2.6 process universe changed")
    if process.get("missing_or_failed_transfer_means_required") is not False:
        raise ValueError("missing transfer cannot imply process requirement")
    if process.get("support_requires_zero_false_required_processes_in_every_panel") is not True:
        raise ValueError("v2.6 false-required criterion changed")
    if float(process.get("support_requires_minimum_possible_process_recall", -1)) != 1.0:
        raise ValueError("v2.6 process recall criterion changed")

    boundary = payload.get("boundary_certificate", {})
    for key in ("all_expected_members_required", "missing_member_makes_interval_unavailable", "all_required_calibration_keys_required", "calibration_applied_before_validation_truth_read", "support_requires_v2_6_coverage_no_worse_in_every_panel"):
        if boundary.get(key) is not True:
            raise ValueError(f"v2.6 boundary contract changed: {key}")
    if int(boundary.get("minimum_complete_calibration_taxa_per_key", -1)) != 2:
        raise ValueError("v2.6 cannot relax two-complete-calibration-taxa minimum")
    if boundary.get("validation_truth_used_for_calibration") is not False:
        raise ValueError("v2.6 validation truth cannot calibrate")
    if boundary.get("support_comparator") != "complete_adequate_certificate":
        raise ValueError("v2.6 boundary comparator changed")

    if tuple(payload.get("decision_states", ())) != DECISION_STATES:
        raise ValueError("v2.6 decision states changed")
    if payload.get("product_b_remains_blocked_until_empirical_confirmation") is not True:
        raise ValueError("v2.6 Product-B boundary changed")
    return payload


def v2_6_decision(panel_summary: pd.DataFrame) -> pd.DataFrame:
    """Apply the unchanged cross-panel support rule under the v2.6 calibration."""
    required = {
        "panel", "n_validation_taxa", "n_complete_process_certificates",
        "n_complete_boundary_certificates", "n_calibrated_response_keys",
        "n_complete_calibrated_intervals", "total_false_required_processes",
        "minimum_possible_process_recall", "complete_adequate_boundary_coverage",
        "v2_6_calibrated_boundary_coverage",
    }
    missing = sorted(required - set(panel_summary.columns))
    if missing:
        raise KeyError(f"v2.6 panel summary missing columns: {missing}")
    data = panel_summary.copy()
    data["panel"] = data["panel"].astype(str)
    if set(data["panel"]) != set(PANELS) or len(data) != len(PANELS):
        return pd.DataFrame([{
            "decision": "v2_6_unavailable", "scientific_promotion_allowed": False,
            "all_panels_available": False, "process_support": False,
            "boundary_support": False, "n_panels": int(data["panel"].nunique()),
            "next_action": "diagnose missing panel summaries without changing the frozen contract",
        }])
    numeric = tuple(required - {"panel"})
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    finite = np.ones(len(data), dtype=bool)
    for column in numeric:
        finite &= np.isfinite(data[column].to_numpy(float))
    available = bool(
        finite.all()
        and data["n_validation_taxa"].eq(3).all()
        and data["n_complete_process_certificates"].eq(3).all()
        and data["n_complete_boundary_certificates"].eq(3).all()
        and data["n_calibrated_response_keys"].gt(0).all()
        and data["n_complete_calibrated_intervals"].eq(data["n_calibrated_response_keys"]).all()
    )
    process_support = bool(available and data["total_false_required_processes"].eq(0).all() and (data["minimum_possible_process_recall"] >= 1.0 - 1e-12).all())
    boundary_support = bool(available and (data["v2_6_calibrated_boundary_coverage"] >= data["complete_adequate_boundary_coverage"] - 1e-12).all())
    if not available:
        decision = "v2_6_unavailable"
        next_action = "retain abstention and diagnose incomplete process/boundary evidence"
    elif process_support and boundary_support:
        decision = "v2_6_supported"
        next_action = "freeze v2.6 and rebuild an independent real-data sealed-before-M confirmation"
    elif process_support:
        decision = "v2_6_process_only"
        next_action = "retain process support but do not proceed to empirical promotion"
    elif boundary_support:
        decision = "v2_6_boundary_only"
        next_action = "retain boundary support but do not proceed to empirical promotion"
    else:
        decision = "v2_6_not_supported"
        next_action = "retain negative evidence; do not tune against opened fresh validation truth"
    return pd.DataFrame([{
        "decision": decision, "scientific_promotion_allowed": False,
        "all_panels_available": available, "process_support": process_support,
        "boundary_support": boundary_support, "n_panels": len(data),
        "next_action": next_action,
    }])
