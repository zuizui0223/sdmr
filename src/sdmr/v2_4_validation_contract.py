"""Immutable validation-stage contract for Product-A v2.4.

The contract binds the reserved validation taxa to the frozen discovery candidate
artifacts and discovery-only calibration artifact.  It also provides the exact
five-state decision rule used only after all model-only fits, process certificates
and boundary intervals have been frozen and validation truth is opened once.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PANELS = ("panel_D1", "panel_D2", "panel_D3")
VALIDATION_SPECS = {
    "panel_D1": (
        ("soft_threshold", 401),
        ("omitted_driver", 411),
        ("observation_confounded", 421),
    ),
    "panel_D2": (
        ("soft_threshold", 402),
        ("omitted_driver", 412),
        ("observation_confounded", 422),
    ),
    "panel_D3": (
        ("soft_threshold", 403),
        ("omitted_driver", 413),
        ("observation_confounded", 423),
    ),
}
PRODUCTS = (
    "canonical_auc_point",
    "complete_adequate_certificate",
    "v2_3_mean_pareto_certificate",
    "v2_4_exclusion_calibrated_certificate",
)
DECISION_STATES = (
    "exclusion_certificate_supported",
    "exclusion_certificate_process_only",
    "exclusion_certificate_boundary_only",
    "exclusion_certificate_not_supported",
    "exclusion_certificate_unavailable",
)
PROCESS_UNIVERSE = ("temperature", "water", "soil", "seasonality", "noise")
DISCOVERY_RUN_ID = "32096477308"
DISCOVERY_HEAD_SHA = "3c222249109ac2c15f6258ebc79bb1c957dd42a4"
CALIBRATION_RUN_ID = "32099494627"
CALIBRATION_HEAD_SHA = "54ced575b0751fa7c2ca18fb2544badc6643f37c"
CALIBRATION_ARTIFACT_ID = "9311087568"
CALIBRATION_ARTIFACT_NAME = (
    "product-a-v2-4-discovery-refit-calibration-frozen"
)
CALIBRATION_ARTIFACT_DIGEST = (
    "sha256:2fad05bc40af18292ff1fb24c2580ef5c603338da302f168cb130299a126363b"
)
DISCOVERY_ARTIFACTS = {
    "panel_D1": {
        "artifact_id": "9310256239",
        "artifact_digest": "sha256:aace53635728c8a2edf4a92de8136e127a21d9552679cad0f30048195e25e7db",
    },
    "panel_D2": {
        "artifact_id": "9310224903",
        "artifact_digest": "sha256:b47f660cab44e2c8e7a29131c163447a39d7aa6332a4c83a3ea0f7aebdd0936b",
    },
    "panel_D3": {
        "artifact_id": "9310181352",
        "artifact_digest": "sha256:5f325c22cffd3048ba99aecf24bf94dc6e95c9264aae6953e7ae0a9b473dc85e",
    },
}


def load_validation_contract(path: str | Path) -> dict[str, Any]:
    """Fail closed if any validation source, order or decision rule changed."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != (
        "product_a_v2_4_predeclared_validation_transfer_and_decision_contract"
    ):
        raise ValueError("v2.4 validation purpose changed")
    for key in (
        "scientific_promotion_run",
        "scientific_promotion_allowed",
        "real_empirical_data_read",
        "old_external_sealed_outcomes_read",
        "validation_truth_read_before_all_fits_and_certificates_frozen",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"v2.4 validation requires {key}=false")

    source = payload.get("source_discovery", {})
    if str(source.get("run_id")) != DISCOVERY_RUN_ID:
        raise ValueError("v2.4 validation discovery run changed")
    if str(source.get("head_sha")) != DISCOVERY_HEAD_SHA:
        raise ValueError("v2.4 validation discovery head changed")
    if source.get("artifacts") != DISCOVERY_ARTIFACTS:
        raise ValueError("v2.4 validation discovery artifacts changed")

    calibration = payload.get("source_discovery_calibration", {})
    expected_calibration = {
        "run_id": CALIBRATION_RUN_ID,
        "head_sha": CALIBRATION_HEAD_SHA,
        "artifact_id": CALIBRATION_ARTIFACT_ID,
        "artifact_name": CALIBRATION_ARTIFACT_NAME,
        "artifact_digest": CALIBRATION_ARTIFACT_DIGEST,
        "n_complete_calibration_keys": 18,
        "validation_stage_allowed": True,
        "calibration_uses_validation_truth": False,
    }
    if calibration != expected_calibration:
        raise ValueError("v2.4 validation calibration source changed")

    raw_panels = payload.get("panels", {})
    if tuple(raw_panels) != PANELS:
        raise ValueError("v2.4 validation panel order changed")
    for panel in PANELS:
        observed = tuple(
            (str(row["family"]), int(row["seed"]))
            for row in raw_panels.get(panel, {}).get("validation", ())
        )
        if observed != VALIDATION_SPECS[panel]:
            raise ValueError(f"v2.4 validation taxa changed for {panel}")
    seeds = [seed for panel in PANELS for _, seed in VALIDATION_SPECS[panel]]
    if len(seeds) != len(set(seeds)) or min(seeds) <= 323:
        raise ValueError("v2.4 validation seeds are not unique unseen seeds")

    fit = payload.get("fit_contract", {})
    if fit.get("source") != "configs/product_a_v2_4_refit_contract.json":
        raise ValueError("v2.4 validation refit source changed")
    if fit.get("role") != "validation":
        raise ValueError("v2.4 validation refit role changed")
    if int(fit.get("n_worker_cells", -1)) != 54:
        raise ValueError("v2.4 validation worker denominator changed")
    if tuple(fit.get("groups", ())) != (
        "base",
        "noise",
        "seasonality",
        "soil",
        "temperature",
        "water",
    ):
        raise ValueError("v2.4 validation group order changed")
    if tuple(fit.get("M_specs", ())) != ("m_core", "m_mid", "m_wide"):
        raise ValueError("v2.4 validation M grid changed")
    if int(fit.get("full_fit_code", -1)) != 9:
        raise ValueError("v2.4 validation full-fit code changed")
    if tuple(fit.get("spatial_refit_codes", ())) != (0, 1, 2, 3, 4):
        raise ValueError("v2.4 validation spatial-refit codes changed")
    if int(fit.get("validation_role_offset", -1)) != 50000:
        raise ValueError("v2.4 validation role offset changed")
    if fit.get("generating_truth_read_by_worker") is not False:
        raise ValueError("v2.4 validation workers cannot read generating truth")

    if tuple(payload.get("products", ())) != PRODUCTS:
        raise ValueError("v2.4 validation products changed")
    process = payload.get("process_certificate", {})
    if tuple(process.get("process_universe", ())) != PROCESS_UNIVERSE:
        raise ValueError("v2.4 validation process universe changed")
    if process.get("missing_or_failed_transfer_means_required") is not False:
        raise ValueError("missing validation transfer cannot imply requirement")
    if process.get("possible_process_recall_audited_only_after_truth_freeze") is not True:
        raise ValueError("possible-process recall truth barrier changed")

    boundary = payload.get("boundary_certificate", {})
    if boundary.get("all_expected_members_required") is not True:
        raise ValueError("v2.4 validation must require all expected members")
    if boundary.get("missing_member_makes_interval_unavailable") is not True:
        raise ValueError("v2.4 validation cannot drop missing members")
    if boundary.get("validation_truth_used_for_calibration") is not False:
        raise ValueError("v2.4 validation truth cannot calibrate intervals")
    if boundary.get("calibration_applied_before_validation_truth_read") is not True:
        raise ValueError("v2.4 validation calibration order changed")

    expected_order = (
        "verify_54_model_only_worker_artifacts",
        "freeze_process_transfer_statuses",
        "freeze_possible_and_unsupported_process_sets",
        "freeze_four_raw_product_envelopes",
        "apply_frozen_discovery_calibration_to_v2_4_envelopes",
        "freeze_all_pretruth_products_and_fingerprints",
        "open_validation_generating_truth_once",
        "audit_process_and_boundary_products",
        "apply_predeclared_decision",
    )
    if tuple(payload.get("truth_opening_order", ())) != expected_order:
        raise ValueError("v2.4 validation truth-opening order changed")
    if tuple(payload.get("decision_states", ())) != DECISION_STATES:
        raise ValueError("v2.4 validation decision states changed")
    return payload


def exclusion_certificate_decision(panel_summary: pd.DataFrame) -> pd.DataFrame:
    """Apply the frozen cross-panel process/boundary decision rule.

    Availability follows the predeclared contract literally: every validation
    taxon must have a complete process certificate, all four raw boundary
    products must be complete, and every discovery-calibrated v2.4 response key
    must also have a complete calibrated interval. A calibrated key that is
    missing because discovery supplied no calibration radius is evidence
    unavailability, not something that can be silently omitted from coverage.
    """

    required = {
        "panel",
        "n_validation_taxa",
        "n_complete_process_certificates",
        "n_complete_boundary_certificates",
        "n_calibrated_response_keys",
        "n_complete_calibrated_intervals",
        "total_false_required_processes",
        "minimum_possible_process_recall",
        "complete_adequate_boundary_coverage",
        "v2_4_calibrated_boundary_coverage",
    }
    missing = sorted(required - set(panel_summary.columns))
    if missing:
        raise KeyError(f"v2.4 panel summary missing columns: {missing}")
    data = panel_summary.copy()
    data["panel"] = data["panel"].astype(str)
    if set(data["panel"]) != set(PANELS) or len(data) != len(PANELS):
        return pd.DataFrame(
            [
                {
                    "decision": "exclusion_certificate_unavailable",
                    "scientific_promotion_allowed": False,
                    "all_panels_available": False,
                    "process_support": False,
                    "boundary_support": False,
                    "n_panels": int(data["panel"].nunique()),
                    "next_action": (
                        "diagnose missing panel summaries without relaxing the "
                        "frozen validation contract"
                    ),
                }
            ]
        )

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
        and data["n_complete_calibrated_intervals"].eq(
            data["n_calibrated_response_keys"]
        ).all()
    )
    process_support = bool(
        available
        and data["total_false_required_processes"].eq(0).all()
        and (data["minimum_possible_process_recall"] >= 1.0 - 1e-12).all()
    )
    boundary_support = bool(
        available
        and (
            data["v2_4_calibrated_boundary_coverage"]
            >= data["complete_adequate_boundary_coverage"] - 1e-12
        ).all()
    )

    if not available:
        decision = "exclusion_certificate_unavailable"
        next_action = (
            "diagnose incomplete validation workers, process cells or boundary "
            "intervals without relaxing frozen gates"
        )
    elif process_support and boundary_support:
        decision = "exclusion_certificate_supported"
        next_action = (
            "freeze v2.4 before a newly rebuilt real-data sealed-before-M "
            "confirmation; do not promote from known truth alone"
        )
    elif process_support:
        decision = "exclusion_certificate_process_only"
        next_action = (
            "retain process-exclusion support but redesign boundary calibration "
            "before empirical confirmation"
        )
    elif boundary_support:
        decision = "exclusion_certificate_boundary_only"
        next_action = (
            "retain boundary-transfer support but redesign process certification "
            "before empirical confirmation"
        )
    else:
        decision = "exclusion_certificate_not_supported"
        next_action = (
            "retain negative evidence and diagnose both process and boundary failures"
        )
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "scientific_promotion_allowed": False,
                "all_panels_available": available,
                "process_support": process_support,
                "boundary_support": boundary_support,
                "n_panels": len(data),
                "next_action": next_action,
            }
        ]
    )
