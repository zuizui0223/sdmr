"""Fail-closed loaders and compatibility views for Product-A v2.8.3.

The repository-level scientific design is the already merged
``product_a_v2_8_3_fresh_confirmation_contract.json`` from PR #159.  This module
never rewrites that design.  It validates the frozen design and constructs only
an in-memory compatibility view for the deterministic v2.7.2 scientific core and
the coordinate-only v2.7.3 structural gate.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_DESIGN_PURPOSE = "product_a_v2_8_3_single_fraction_fresh_confirmation_contract"
EXPECTED_DESIGN_BLOB = "1928de6d8f1289117415047c7a8d1ee894ca6bbe"
EXPECTED_DESIGN_MERGE = "1f0ab72c3ef868b28aac8257e53ba066a9c483bd"
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
EXPECTED_V271_CONTRACT_BLOB = "8b7c2680d2999e61c8672934724988bf0e217fe1"
EXPECTED_V272_DETERMINISTIC_BLOB = "c251b19c21e199894be3c93d8b36e3d2329a9777"
EXPECTED_PARTITION_MODULE_BLOB = "2109221ee796bee39093c0f9388d63761a62f4af"
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


def _validate_frozen_design(source: Path, payload: dict[str, Any]) -> None:
    if payload.get("purpose") != EXPECTED_DESIGN_PURPOSE:
        raise ValueError("wrong frozen v2.8.3 design purpose")
    if payload.get("tracks_issue") != 158:
        raise ValueError("v2.8.3 design issue provenance changed")
    if payload.get("predeclared_before_any_v2_8_3_structural_or_environmental_outcome") is not True:
        raise ValueError("v2.8.3 design was not frozen before structural/environmental outcomes")

    geometry = payload.get("upstream_geometry_calibration", {})
    if (
        int(geometry.get("workflow_run_id", -1)) != 32943026025
        or geometry.get("implementation_sha") != "32d5b67f7b18634830191df52ef56128589f5d82"
        or int(geometry.get("decision_artifact_id", -1)) != 9609352973
        or geometry.get("decision_artifact_digest")
        != "sha256:a08c9f40d89b65ccf7357289b7e89bda7e6844cc6c2014edaeafb14c368c63d6"
        or geometry.get("decision") != "geometry_calibration_fraction_selected"
        or float(geometry.get("selected_global_sealed_fraction", -1)) != 0.25
        or geometry.get("fraction_retuning_allowed") is not False
        or geometry.get("geometry_result_is_ecological_support") is not False
    ):
        raise ValueError("v2.8.3 geometry-calibration freeze changed")

    upstream = payload.get("upstream_fresh_source", {})
    if (
        upstream.get("receipt_blob_sha") != EXPECTED_SOURCE_RECEIPT_BLOB
        or upstream.get("receipt_merge_sha") != EXPECTED_SOURCE_RECEIPT_MERGE
        or int(upstream.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN
        or upstream.get("workflow_conclusion") != "success"
        or upstream.get("focal_file_sha256") != EXPECTED_FOCAL_SHA256
        or upstream.get("focal_query_sha256") != EXPECTED_FOCAL_QUERY_SHA256
        or upstream.get("target_file_sha256") != EXPECTED_TARGET_SHA256
        or upstream.get("target_query_sha256") != EXPECTED_TARGET_QUERY_SHA256
    ):
        raise ValueError("v2.8.3 frozen source identity changed")

    panel = payload.get("fresh_taxon_panel", {})
    if (
        panel.get("blob_sha") != EXPECTED_PANEL_BLOB
        or panel.get("sha256") != EXPECTED_PANEL_SHA256
        or int(panel.get("n_taxa", -1)) != 12
        or int(panel.get("n_validation_strata", -1)) != 12
        or int(panel.get("selected_candidate_rank", -1)) != 1
        or panel.get("post_selection_replacement_allowed") is not False
        or panel.get("independence_axis") != "taxon_holdout_not_temporal"
        or panel.get("temporal_independence_claim_allowed") is not False
    ):
        raise ValueError("v2.8.3 frozen panel design changed")
    repo = _repo_root(source)
    panel_path = repo / str(panel.get("path", ""))
    if not panel_path.exists() or sha256_file(panel_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 panel bytes changed")
    panel_frame = pd.read_csv(panel_path)
    if (
        len(panel_frame) != 12
        or panel_frame["scientific_name"].astype(str).nunique() != 12
        or panel_frame["validation_stratum"].astype(str).nunique() != 12
        or set(pd.to_numeric(panel_frame["candidate_rank"]).astype(int)) != {1}
    ):
        raise ValueError("v2.8.3 panel denominator changed")

    inherited = payload.get("inherited_scientific_semantics", {})
    if (
        inherited.get("v2_7_1_contract_blob_sha") != EXPECTED_V271_CONTRACT_BLOB
        or inherited.get("v2_7_2_deterministic_contract_blob_sha") != EXPECTED_V272_DETERMINISTIC_BLOB
        or int(inherited.get("model_random_state", -1)) != 0
        or int(inherited.get("selection_process_numpy_seed", -1)) != 0
        or inherited.get("solver") != "liblinear"
    ):
        raise ValueError("v2.8.3 inherited deterministic identity changed")
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
        raise ValueError("v2.8.3 M became an optimization axis")
    if tuple(int(x) for x in fixed.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.8.3 split seeds changed")
    if tuple(float(x) for x in fixed.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.8.3 calibrated fraction changed")
    if int(fixed.get("n_confirmation_parts", -1)) != 3:
        raise ValueError("v2.8.3 scientific part denominator changed")
    for key, expected in {
        "outer_folds": 4,
        "spatial_microblocks": 12,
        "assignment_attempts": 32,
        "minimum_evaluation_occurrences_per_fold": 2,
        "minimum_evaluation_background_rows_per_M_fold": 5,
        "minimum_training_background_rows_per_M_fold": 5,
    }.items():
        if int(fixed.get(key, -1)) != expected:
            raise ValueError(f"v2.8.3 structural setting changed: {key}")
    if fixed.get("assignment_seed_formula") != "part_seed + taxon_index*100 + 271":
        raise ValueError("v2.8.3 partition seed formula changed")
    if fixed.get("process_registry_blob_sha") != EXPECTED_PROCESS_REGISTRY_BLOB:
        raise ValueError("v2.8.3 process registry blob changed")
    if fixed.get("process_registry_sha256") != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry fingerprint changed")
    registry_path = repo / str(fixed.get("process_registry_path", ""))
    if not registry_path.exists() or sha256_file(registry_path) != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry bytes changed")
    if tuple(str(x) for x in fixed.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("v2.8.3 process domains changed")

    library = fixed.get("procedure_library", {})
    if tuple(library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("v2.8.3 procedure strategies changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("v2.8.3 model specs changed")
    for key, expected in {"inner_folds": 3, "outer_folds": 4, "max_predictors": 8}.items():
        if int(library.get(key, -1)) != expected:
            raise ValueError(f"v2.8.3 procedure library changed: {key}")
    if float(library.get("vif_threshold", -1)) != 5.0:
        raise ValueError("v2.8.3 VIF threshold changed")
    if float(library.get("predictive_min_gain", -1)) != 0.0:
        raise ValueError("v2.8.3 predictive threshold changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("v2.8.3 observation-predictor role changed")
    if fixed.get("prediction_adequacy") != {
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
        "candidate_scores_used": False,
        "sealed_rows_used": False,
        "thresholds_unchanged_from_v2_7_development": True,
    }
    if audit != expected_audit:
        raise ValueError("v2.8.3 audit-space freeze changed")

    translation = payload.get("single_fraction_denominator_translation", {})
    if (
        int(translation.get("predecessor_parts", -1)) != 6
        or int(translation.get("successor_parts", -1)) != 3
        or translation.get("duplicate_0_25_parts_allowed") is not False
        or translation.get("new_post_calibration_split_seeds_allowed") is not False
        or int(translation.get("ecological_nondomination_successor_minimum_parts", -1)) != 2
        or int(translation.get("strict_improvement_successor_minimum_parts", -1)) != 2
    ):
        raise ValueError("v2.8.3 three-part denominator translation changed")

    structural = payload.get("structural_transportability", {})
    if (
        structural.get("evaluated_before_any_CHELSA_or_environmental_value_for_v2_8_3") is not True
        or structural.get("partition_module_blob_sha") != EXPECTED_PARTITION_MODULE_BLOB
        or int(structural.get("n_taxon_M_part_cells", -1)) != 108
        or int(structural.get("n_cells_per_part", -1)) != 36
        or structural.get("environmental_extraction_allowed_only_for_structurally_auditable_complete_parts") is not True
        or structural.get("taxon_M_or_seed_replacement_after_structural_result_allowed") is not False
        or structural.get("incomplete_part_partial_repair_allowed") is not False
    ):
        raise ValueError("v2.8.3 structural transportability rule changed")

    decision = payload.get("decision_rule", {})
    if decision.get("all_3_parts_required_for_primary_full_denominator_decision") is not True:
        raise ValueError("v2.8.3 primary denominator changed")
    if decision.get("all_12_taxa_required_in_every_part") is not True:
        raise ValueError("v2.8.3 taxon denominator changed")
    if decision.get("all_3_M_specs_required_in_every_part") is not True:
        raise ValueError("v2.8.3 M denominator changed")
    if decision.get("fewer_than_3_structurally_auditable_parts_primary_state") != "empirical_confirmation_unavailable":
        raise ValueError("v2.8.3 structural fail-closed state changed")
    if decision.get("zero_structurally_auditable_parts_opens_environmental_or_sealed_evidence") is not False:
        raise ValueError("v2.8.3 zero-coverage barrier changed")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("v2.8.3 prediction guardrail changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 2 or int(eco.get("strict_improvement_minimum_parts", -1)) != 2:
        raise ValueError("v2.8.3 ecological decision translation changed")
    proc = decision.get("process_reproducibility", {})
    if abs(float(proc.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("v2.8.3 process reproducibility threshold changed")
    if proc.get("missing_status_is_unavailable_not_consensus") is not True:
        raise ValueError("v2.8.3 missing-process semantics changed")
    for key in (
        "post_outcome_candidate_reselection_allowed",
        "post_outcome_threshold_tuning_allowed",
        "scientific_promotion_allowed_by_this_decision",
    ):
        if decision.get(key) is not False:
            raise ValueError(f"v2.8.3 post-outcome/promotion boundary changed: {key}")
    if decision.get("random_seed_changes_after_outcome_allowed") is not False:
        raise ValueError("v2.8.3 random seed can change after outcome")
    if decision.get("product_b_remains_blocked_until_separate_promotion_decision") is not True:
        raise ValueError("v2.8.3 Product-B boundary changed")

    boundary = payload.get("execution_boundary", {})
    if boundary.get("runtime_implementation_sha") is not None or boundary.get("runtime_frozen_ref") is not None:
        raise ValueError("frozen design unexpectedly contains a runtime identity")
    for key in (
        "execution_allowed",
        "structural_query_allowed_before_separate_runtime_freeze_and_authorization",
        "environmental_extraction_allowed_before_separate_runtime_freeze_and_authorization",
        "model_fitting_allowed_before_separate_runtime_freeze_and_authorization",
        "sealed_ecological_read_allowed_before_separate_runtime_freeze_and_authorization",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if boundary.get(key) is not False:
            raise ValueError(f"v2.8.3 frozen design execution boundary changed: {key}")
    if boundary.get("separate_external_one_shot_authorization_required") is not True:
        raise ValueError("v2.8.3 separate authorization requirement changed")


def _compatibility_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Build the shape expected by the inherited v2.7.2 scientific core."""
    fixed = deepcopy(payload["fixed_design"])
    inherited = payload["inherited_scientific_semantics"]
    fixed["procedure_library"] = deepcopy(fixed["procedure_library"])
    fixed["procedure_library"]["model_random_state"] = int(inherited["model_random_state"])
    fixed["procedure_library"]["selection_process_numpy_seed"] = int(
        inherited["selection_process_numpy_seed"]
    )

    partition = {
        "outer_folds": int(fixed["outer_folds"]),
        "spatial_microblocks": int(fixed["spatial_microblocks"]),
        "assignment_attempts": int(fixed["assignment_attempts"]),
        "assignment_seed_formula": str(fixed["assignment_seed_formula"]),
        "microblock_constructor": "KMeans_on_model_pool_occurrence_unit_sphere_coordinates",
        "fold_assignment": "StratifiedGroupKFold_over_presence_and_all_M_background_resource_types",
        "shared_occurrence_fold_assignment_across_all_M": True,
        "microblock_atomicity_preserved": True,
        "minimum_evaluation_occurrences_per_fold": int(
            fixed["minimum_evaluation_occurrences_per_fold"]
        ),
        "minimum_evaluation_background_rows_per_M_fold": int(
            fixed["minimum_evaluation_background_rows_per_M_fold"]
        ),
        "minimum_training_background_rows_per_M_fold": int(
            fixed["minimum_training_background_rows_per_M_fold"]
        ),
        "choose_feasible_assignment_by": "minimum_max_then_mean_normalized_row_count_imbalance",
        "abstain_if_no_feasible_assignment": True,
        "sealed_rows_used_for_partition_assignment": False,
        "environmental_values_used_for_partition_assignment": False,
        "candidate_scores_used_for_partition_assignment": False,
        "process_knockout_outcomes_used_for_partition_assignment": False,
    }

    audit = deepcopy(fixed["partition_aware_audit_space"])
    audit.pop("thresholds_unchanged_from_v2_7_development", None)
    audit["thresholds_unchanged_from_v2_7_2"] = True

    panel = payload["fresh_taxon_panel"]
    upstream = payload["upstream_fresh_source"]
    decision = payload["decision_rule"]
    view = deepcopy(payload)
    view["purpose"] = "product_a_v2_8_3_runtime_compatibility_view"
    view["source_receipt"] = {
        "path": upstream["receipt_path"],
        "merged_at_sha": upstream["receipt_merge_sha"],
        "blob_sha": upstream["receipt_blob_sha"],
        "workflow_run_id": int(upstream["workflow_run_id"]),
        "workflow_conclusion": upstream["workflow_conclusion"],
    }
    view["fresh_taxon_panel"] = {
        "path": panel["path"],
        "sha256": panel["sha256"],
        "require_all_12_taxa": True,
        "require_all_12_validation_strata": True,
        "predeclared_candidate_rank": int(panel["selected_candidate_rank"]),
        "post_source_taxon_reselection_allowed": False,
    }
    view["fixed_design"] = fixed
    view["evidence_balanced_partition"] = partition
    view["partition_aware_audit_space"] = audit
    view["structural_transportability"] = {
        "n_expected_taxon_M_part_cells": int(
            payload["structural_transportability"]["n_taxon_M_part_cells"]
        ),
        "runs_before_any_CHELSA_or_environmental_value_read": True,
        "runs_before_candidate_model_fitting": True,
        "runs_before_candidate_score_read": True,
        "runs_before_sealed_ecological_outcome_read": True,
        "part_structurally_auditable_if_all_12_taxa_x_all_3_M_joint_support_is_feasible": True,
        "primary_full_denominator_requires_all_3_parts_structurally_auditable": True,
        "conditional_ecology_allowed_only_for_complete_structurally_auditable_parts": True,
        "taxon_seed_M_source_or_threshold_replacement_after_structural_result_allowed": False,
        "incomplete_part_partial_repair_allowed": False,
        "structural_support_is_ecological_support": False,
    }
    view["decision_rule"] = {
        "all_3_parts_required_for_primary_decision": bool(
            decision["all_3_parts_required_for_primary_full_denominator_decision"]
        ),
        "prediction_guardrail": deepcopy(decision["prediction_guardrail"]),
        "ecological_noninferiority": deepcopy(decision["ecological_noninferiority"]),
        "process_reproducibility": deepcopy(decision["process_reproducibility"]),
        "post_outcome_candidate_reselection_allowed": False,
        "post_outcome_threshold_tuning_allowed": False,
        "post_outcome_random_seed_change_allowed": False,
        "post_outcome_fraction_change_allowed": False,
        "scientific_promotion_allowed_by_this_decision": False,
        "product_b_remains_blocked_until_separate_promotion_decision": True,
    }
    view["stage_execution_allowed"] = False
    view["separate_external_one_shot_authorization_required"] = True
    view["scientific_promotion_run"] = False
    view["product_b_unblocked"] = False
    view["frozen_design_contract_blob_sha"] = EXPECTED_DESIGN_BLOB
    view["frozen_design_merge_sha"] = EXPECTED_DESIGN_MERGE
    return view


def load_v2_8_3_fresh_confirmation_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    _validate_frozen_design(source, payload)
    return _compatibility_view(payload)


def load_v2_8_3_source_receipt(
    path: str | Path, *, source_gate_path: str | Path | None = None
) -> dict[str, Any]:
    # Accepted for v2.7.2 core-call compatibility; v2.8.3 has a merged immutable receipt.
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
    focal, target = payload.get("focal", {}), payload.get("target_group", {})
    if focal.get("file_sha256") != EXPECTED_FOCAL_SHA256:
        raise ValueError("v2.8.3 focal source fingerprint changed")
    if focal.get("query_sha256") != EXPECTED_FOCAL_QUERY_SHA256:
        raise ValueError("v2.8.3 focal query changed")
    if target.get("file_sha256") != EXPECTED_TARGET_SHA256:
        raise ValueError("v2.8.3 target source fingerprint changed")
    if target.get("query_sha256") != EXPECTED_TARGET_QUERY_SHA256:
        raise ValueError("v2.8.3 target query changed")
    if target.get("excluded_taxa_sha256") != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 target exclusion panel changed")
    if float(target.get("one_per_grid_cell_degrees", -1)) != 0.05:
        raise ValueError("v2.8.3 target grid sampling changed")
    for key, value in payload.get("information_barrier", {}).items():
        if value is not False:
            raise ValueError(f"v2.8.2 source receipt crossed barrier before v2.8.3: {key}")
    return payload


def v2_7_3_structural_core_view(contract: dict[str, Any]) -> dict[str, Any]:
    """Return the minimal shape expected by the coordinate-only v2.7.3 gate."""
    view = deepcopy(contract)
    view["rank3_panel"] = {
        "path": contract["fresh_taxon_panel"]["path"],
        "sha256": contract["fresh_taxon_panel"]["sha256"],
    }
    view["inherited_evidence_balanced_partition"] = deepcopy(
        contract["evidence_balanced_partition"]
    )
    return view
