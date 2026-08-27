"""Fail-closed runtime loader for the merged Product-A v2.8.3 design freeze.

The repository design contract is authoritative. This module validates it and
returns an in-memory compatibility view for the frozen deterministic v2.7.2
scientific core and the coordinate-only v2.7.3 structural core. It never
rewrites the merged design contract.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_DESIGN_BLOB = "1928de6d8f1289117415047c7a8d1ee894ca6bbe"
EXPECTED_SOURCE_RECEIPT_BLOB = "ed4d90a84db354e06a4a214f6a3a184c7e36ea7f"
EXPECTED_SOURCE_RECEIPT_MERGE = "641b0cce93f5349fc00577bdd12312f327f854c5"
EXPECTED_SOURCE_RUN = 33006988136
EXPECTED_PANEL_BLOB = "5c00886724405edeb13dae4f029ec19573ad180f"
EXPECTED_PANEL_SHA256 = "835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1"
EXPECTED_FOCAL_SHA256 = "4366258f2495604a0c9a5058aeb0111a751493b538ba436760f8555182d32fc5"
EXPECTED_TARGET_SHA256 = "9e8fb2827919e86d450cb5870093cef2adc752bee22a15540406265747d20bf6"
EXPECTED_FOCAL_QUERY_SHA256 = "40f25b5bafff11f5471b389778e29d29f7be02a4e76cd335cfdcee637517dc7e"
EXPECTED_TARGET_QUERY_SHA256 = "b2261d66b156189bf9fd949046ad4f5b0a10697c584efe2ba009ca2d5dc8fdf7"
EXPECTED_PROCESS_REGISTRY_BLOB = "469a1ced27ff47fe6b731c26cc3b9b0f4a56d58a"
EXPECTED_PROCESS_REGISTRY_SHA256 = "08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d"
EXPECTED_PARTITION_BLOB = "2109221ee796bee39093c0f9388d63761a62f4af"
EXPECTED_SEEDS = (2026082201, 2026082202, 2026082203)
EXPECTED_FRACTIONS = (0.25,)
EXPECTED_M = (150, 300, 500)
EXPECTED_DOMAINS = (
    "thermal", "water", "seasonality_phenology", "energy_productivity", "snow", "wind"
)
EXPECTED_STRATEGIES = ("all", "vif", "predictive_forward", "niche_forward")
EXPECTED_MODEL_SPECS = (
    {"C": 0.1, "degree": 1, "penalty": "l2"},
    {"C": 1.0, "degree": 2, "penalty": "l2"},
)


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _repo_root(path: Path) -> Path:
    return path.parent.parent


def _compatibility_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Add only transport aliases needed by frozen predecessor implementations."""
    view = deepcopy(payload)
    fixed = view["fixed_design"]
    inherited = view["inherited_scientific_semantics"]
    library = fixed["procedure_library"]
    library["model_random_state"] = int(inherited["model_random_state"])
    library["selection_process_numpy_seed"] = int(inherited["selection_process_numpy_seed"])

    view["evidence_balanced_partition"] = {
        "outer_folds": int(fixed["outer_folds"]),
        "spatial_microblocks": int(fixed["spatial_microblocks"]),
        "assignment_attempts": int(fixed["assignment_attempts"]),
        "assignment_seed_formula": str(fixed["assignment_seed_formula"]),
        "microblock_constructor": "KMeans_on_model_pool_occurrence_unit_sphere_coordinates",
        "fold_assignment": "StratifiedGroupKFold_over_presence_and_all_M_background_resource_types",
        "shared_occurrence_fold_assignment_across_all_M": True,
        "microblock_atomicity_preserved": True,
        "minimum_evaluation_occurrences_per_fold": int(fixed["minimum_evaluation_occurrences_per_fold"]),
        "minimum_evaluation_background_rows_per_M_fold": int(fixed["minimum_evaluation_background_rows_per_M_fold"]),
        "minimum_training_background_rows_per_M_fold": int(fixed["minimum_training_background_rows_per_M_fold"]),
        "choose_feasible_assignment_by": "minimum_max_then_mean_normalized_row_count_imbalance",
        "abstain_if_no_feasible_assignment": True,
        "sealed_rows_used_for_partition_assignment": False,
        "environmental_values_used_for_partition_assignment": False,
        "candidate_scores_used_for_partition_assignment": False,
        "process_knockout_outcomes_used_for_partition_assignment": False,
    }
    view["partition_aware_audit_space"] = deepcopy(fixed["partition_aware_audit_space"])

    # Compatibility aliases are in-memory only; the merged #159 contract stays byte-identical.
    view["source_receipt"] = {
        "blob_sha": payload["upstream_fresh_source"]["receipt_blob_sha"],
        "path": payload["upstream_fresh_source"]["receipt_path"],
        "workflow_run_id": int(payload["upstream_fresh_source"]["workflow_run_id"]),
    }
    view["structural_transportability"]["n_expected_taxon_M_part_cells"] = int(
        payload["structural_transportability"]["n_taxon_M_part_cells"]
    )
    view["scientific_promotion_run"] = False
    view["product_b_unblocked"] = False
    return view


def load_v2_8_3_fresh_confirmation_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_3_single_fraction_fresh_confirmation_contract":
        raise ValueError("wrong merged v2.8.3 design contract")
    if payload.get("tracks_issue") != 158:
        raise ValueError("v2.8.3 design provenance changed")
    if payload.get("predeclared_before_any_v2_8_3_structural_or_environmental_outcome") is not True:
        raise ValueError("v2.8.3 design was not predeclared")

    geometry = payload.get("upstream_geometry_calibration", {})
    if float(geometry.get("selected_global_sealed_fraction", -1)) != 0.25:
        raise ValueError("v2.8.3 calibrated fraction changed")
    if geometry.get("fraction_retuning_allowed") is not False:
        raise ValueError("v2.8.3 fraction retuning opened")
    if geometry.get("geometry_result_is_ecological_support") is not False:
        raise ValueError("v2.8.3 geometry result became ecological support")

    upstream = payload.get("upstream_fresh_source", {})
    if upstream.get("receipt_blob_sha") != EXPECTED_SOURCE_RECEIPT_BLOB:
        raise ValueError("v2.8.3 source receipt blob changed")
    if upstream.get("receipt_merge_sha") != EXPECTED_SOURCE_RECEIPT_MERGE:
        raise ValueError("v2.8.3 source receipt merge changed")
    if int(upstream.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN:
        raise ValueError("v2.8.3 source run changed")
    if upstream.get("workflow_conclusion") != "success":
        raise ValueError("v2.8.3 source run is not successful")
    for key, expected in (
        ("focal_file_sha256", EXPECTED_FOCAL_SHA256),
        ("target_file_sha256", EXPECTED_TARGET_SHA256),
        ("focal_query_sha256", EXPECTED_FOCAL_QUERY_SHA256),
        ("target_query_sha256", EXPECTED_TARGET_QUERY_SHA256),
    ):
        if upstream.get(key) != expected:
            raise ValueError(f"v2.8.3 source fingerprint changed: {key}")

    repo = _repo_root(source)
    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("blob_sha") != EXPECTED_PANEL_BLOB:
        raise ValueError("v2.8.3 panel blob changed")
    if panel.get("sha256") != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 panel SHA changed")
    panel_path = repo / str(panel.get("path", ""))
    if not panel_path.exists() or sha256_file(panel_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 panel bytes changed")
    frame = pd.read_csv(panel_path)
    if len(frame) != 12 or frame["scientific_name"].astype(str).nunique() != 12:
        raise ValueError("v2.8.3 taxon denominator changed")
    if frame["validation_stratum"].astype(str).nunique() != 12:
        raise ValueError("v2.8.3 validation-stratum denominator changed")
    if set(pd.to_numeric(frame["candidate_rank"]).astype(int)) != {1}:
        raise ValueError("v2.8.3 selected rank changed")
    if panel.get("post_selection_replacement_allowed") is not False:
        raise ValueError("v2.8.3 post-selection replacement opened")

    inherited = payload.get("inherited_scientific_semantics", {})
    if int(inherited.get("model_random_state", -1)) != 0:
        raise ValueError("v2.8.3 model RNG changed")
    if int(inherited.get("selection_process_numpy_seed", -1)) != 0:
        raise ValueError("v2.8.3 selection RNG changed")
    if inherited.get("solver") != "liblinear":
        raise ValueError("v2.8.3 estimator changed")
    for key in (
        "all_other_model_hyperparameters_changed",
        "procedure_strategies_changed",
        "candidate_predictor_universe_changed",
        "prediction_adequacy_changed",
        "ecological_recovery_metrics_changed",
        "weighted_super_score_allowed",
    ):
        if inherited.get(key) is not False:
            raise ValueError(f"v2.8.3 inherited science changed: {key}")

    fixed = payload.get("fixed_design", {})
    if tuple(int(x) for x in fixed.get("M_km", ())) != EXPECTED_M:
        raise ValueError("v2.8.3 M grid changed")
    if fixed.get("M_is_sensitivity_not_optimization") is not True:
        raise ValueError("v2.8.3 M became an optimization target")
    if tuple(int(x) for x in fixed.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.8.3 split seeds changed")
    if tuple(float(x) for x in fixed.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.8.3 sealed fraction changed")
    if int(fixed.get("n_confirmation_parts", -1)) != 3:
        raise ValueError("v2.8.3 must have exactly three parts")
    if (
        int(fixed.get("outer_folds", -1)),
        int(fixed.get("spatial_microblocks", -1)),
        int(fixed.get("assignment_attempts", -1)),
    ) != (4, 12, 32):
        raise ValueError("v2.8.3 partition dimensions changed")
    if fixed.get("assignment_seed_formula") != "part_seed + taxon_index*100 + 271":
        raise ValueError("v2.8.3 assignment seed changed")
    if tuple(str(x) for x in fixed.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("v2.8.3 process domains changed")
    if fixed.get("process_registry_blob_sha") != EXPECTED_PROCESS_REGISTRY_BLOB:
        raise ValueError("v2.8.3 process registry blob changed")
    if fixed.get("process_registry_sha256") != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry SHA changed")
    registry_path = repo / str(fixed.get("process_registry_path", ""))
    if not registry_path.exists() or sha256_file(registry_path) != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry bytes changed")

    library = fixed.get("procedure_library", {})
    if tuple(str(x) for x in library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("v2.8.3 procedure strategies changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("v2.8.3 model specs changed")
    if (
        int(library.get("inner_folds", -1)),
        int(library.get("outer_folds", -1)),
        int(library.get("max_predictors", -1)),
    ) != (3, 4, 8):
        raise ValueError("v2.8.3 procedure dimensions changed")
    if float(library.get("vif_threshold", -1)) != 5.0:
        raise ValueError("v2.8.3 VIF threshold changed")
    if float(library.get("predictive_min_gain", -1)) != 0.0:
        raise ValueError("v2.8.3 predictive threshold changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("v2.8.3 observation predictors changed")
    if fixed.get("prediction_adequacy", {}) != {
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "complete_outer_fold_evidence_required": True,
    }:
        raise ValueError("v2.8.3 prediction adequacy changed")

    audit = fixed.get("partition_aware_audit_space", {})
    expected_audit = {
        "minimum_predictor_coverage": 0.95,
        "minimum_joint_coverage": 0.8,
        "minimum_processes": 4,
        "minimum_complete_fit_background_rows_per_M_fold": 5,
        "minimum_complete_evaluation_background_rows_per_M_fold": 5,
        "minimum_complete_heldout_occurrence_rows_per_M_fold": 2,
    }
    for key, expected in expected_audit.items():
        if float(audit.get(key, -1)) != float(expected):
            raise ValueError(f"v2.8.3 audit threshold changed: {key}")
    if audit.get("candidate_scores_used") is not False or audit.get("sealed_rows_used") is not False:
        raise ValueError("v2.8.3 audit information barrier changed")

    structural = payload.get("structural_transportability", {})
    if structural.get("partition_module_blob_sha") != EXPECTED_PARTITION_BLOB:
        raise ValueError("v2.8.3 partition implementation changed")
    if int(structural.get("n_taxon_M_part_cells", -1)) != 108:
        raise ValueError("v2.8.3 structural denominator changed")
    if int(structural.get("n_cells_per_part", -1)) != 36:
        raise ValueError("v2.8.3 per-part structural denominator changed")
    if structural.get("evaluated_before_any_CHELSA_or_environmental_value_for_v2_8_3") is not True:
        raise ValueError("v2.8.3 structural gate order changed")
    if structural.get("environmental_extraction_allowed_only_for_structurally_auditable_complete_parts") is not True:
        raise ValueError("v2.8.3 structural admission boundary changed")
    if structural.get("taxon_M_or_seed_replacement_after_structural_result_allowed") is not False:
        raise ValueError("v2.8.3 structural reselection opened")
    if structural.get("incomplete_part_partial_repair_allowed") is not False:
        raise ValueError("v2.8.3 partial structural repair opened")

    translation = payload.get("single_fraction_denominator_translation", {})
    if int(translation.get("successor_parts", -1)) != 3:
        raise ValueError("v2.8.3 part translation changed")
    if int(translation.get("ecological_nondomination_successor_minimum_parts", -1)) != 2:
        raise ValueError("v2.8.3 nondomination threshold changed")
    if int(translation.get("strict_improvement_successor_minimum_parts", -1)) != 2:
        raise ValueError("v2.8.3 strict-improvement threshold changed")
    if translation.get("duplicate_0_25_parts_allowed") is not False:
        raise ValueError("v2.8.3 duplicate parts opened")
    if translation.get("new_post_calibration_split_seeds_allowed") is not False:
        raise ValueError("v2.8.3 new seeds opened")

    decision = payload.get("decision_rule", {})
    if decision.get("all_3_parts_required_for_primary_full_denominator_decision") is not True:
        raise ValueError("v2.8.3 primary denominator changed")
    if decision.get("fewer_than_3_structurally_auditable_parts_primary_state") != "empirical_confirmation_unavailable":
        raise ValueError("v2.8.3 structural fail-closed state changed")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("v2.8.3 prediction guardrail changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 2 or int(eco.get("strict_improvement_minimum_parts", -1)) != 2:
        raise ValueError("v2.8.3 ecological decision threshold changed")
    process = decision.get("process_reproducibility", {})
    if abs(float(process.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("v2.8.3 process reproducibility changed")
    for key in (
        "post_outcome_candidate_reselection_allowed",
        "post_outcome_threshold_tuning_allowed",
        "random_seed_changes_after_outcome_allowed",
        "scientific_promotion_allowed_by_this_decision",
    ):
        if decision.get(key) is not False:
            raise ValueError(f"v2.8.3 post-outcome boundary changed: {key}")
    if decision.get("product_b_remains_blocked_until_separate_promotion_decision") is not True:
        raise ValueError("v2.8.3 Product-B boundary changed")

    boundary = payload.get("execution_boundary", {})
    if boundary.get("execution_allowed") is not False:
        raise ValueError("v2.8.3 design contract must remain non-executing")
    if boundary.get("separate_external_one_shot_authorization_required") is not True:
        raise ValueError("v2.8.3 external authorization requirement changed")
    if boundary.get("scientific_promotion_allowed") is not False:
        raise ValueError("v2.8.3 design permits promotion")
    if boundary.get("product_b_unblocked") is not False:
        raise ValueError("v2.8.3 design unblocks Product B")
    return _compatibility_view(payload)


def load_v2_8_3_source_receipt(
    path: str | Path, *, source_gate_path: str | Path | None = None
) -> dict[str, Any]:
    del source_gate_path
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_2_fresh_raw_source_receipt":
        raise ValueError("wrong v2.8.2 source receipt for v2.8.3")
    if int(payload.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN:
        raise ValueError("v2.8.3 source run changed")
    if payload.get("workflow_conclusion") != "success":
        raise ValueError("v2.8.3 source run is not successful")
    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("sha256") != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 source panel changed")
    if float(panel.get("selected_global_sealed_fraction", -1)) != 0.25:
        raise ValueError("v2.8.3 source fraction changed")
    focal = payload.get("focal", {})
    target = payload.get("target_group", {})
    if focal.get("file_sha256") != EXPECTED_FOCAL_SHA256:
        raise ValueError("v2.8.3 focal bytes changed")
    if focal.get("query_sha256") != EXPECTED_FOCAL_QUERY_SHA256:
        raise ValueError("v2.8.3 focal query changed")
    if target.get("file_sha256") != EXPECTED_TARGET_SHA256:
        raise ValueError("v2.8.3 target bytes changed")
    if target.get("query_sha256") != EXPECTED_TARGET_QUERY_SHA256:
        raise ValueError("v2.8.3 target query changed")
    if target.get("excluded_taxa_sha256") != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 target exclusion changed")
    if float(target.get("one_per_grid_cell_degrees", -1)) != 0.05:
        raise ValueError("v2.8.3 target grid sampling changed")
    if any(value is not False for value in payload.get("information_barrier", {}).values()):
        raise ValueError("v2.8.2 source receipt crossed information barrier")
    return payload


def v2_7_3_structural_core_view(contract: dict[str, Any]) -> dict[str, Any]:
    view = deepcopy(contract)
    view["rank3_panel"] = {
        "path": contract["fresh_taxon_panel"]["path"],
        "sha256": contract["fresh_taxon_panel"]["sha256"],
    }
    view["inherited_evidence_balanced_partition"] = deepcopy(
        contract["evidence_balanced_partition"]
    )
    return view
