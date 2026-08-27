"""Fail-closed contract/source loaders for Product-A v2.8.3 fresh confirmation.

The v2.8.3 design is intentionally separate from the historical v2.7.1/v2.7.2
loaders because those loaders freeze the predecessor two-fraction/six-part
cohorts.  This module validates the already merged single-fraction design and
provides a compatibility view for deterministic predecessor worker semantics
without changing any historical contract or module.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_DESIGN_BLOB_SHA = "1928de6d8f1289117415047c7a8d1ee894ca6bbe"
EXPECTED_SOURCE_RECEIPT_BLOB_SHA = "ed4d90a84db354e06a4a214f6a3a184c7e36ea7f"
EXPECTED_PANEL_BLOB_SHA = "5c00886724405edeb13dae4f029ec19573ad180f"
EXPECTED_PANEL_SHA256 = "835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1"
EXPECTED_SOURCE_RUN_ID = 33006988136
EXPECTED_FOCAL_SHA256 = "4366258f2495604a0c9a5058aeb0111a751493b538ba436760f8555182d32fc5"
EXPECTED_FOCAL_QUERY_SHA256 = "40f25b5bafff11f5471b389778e29d29f7be02a4e76cd335cfdcee637517dc7e"
EXPECTED_TARGET_SHA256 = "9e8fb2827919e86d450cb5870093cef2adc752bee22a15540406265747d20bf6"
EXPECTED_TARGET_QUERY_SHA256 = "b2261d66b156189bf9fd949046ad4f5b0a10697c584efe2ba009ca2d5dc8fdf7"
EXPECTED_SNAPSHOT_CATALOG_SHA256 = "47300bbeb7d7b10711e685cff20d7574737c3440228e9b0247efac40a3d0ca84"
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
EXPECTED_PROCESS_REGISTRY_SHA256 = "08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _repo_root(path: Path) -> Path:
    return path.parent.parent


def load_v2_8_3_fresh_confirmation_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_3_single_fraction_fresh_confirmation_contract":
        raise ValueError("wrong v2.8.3 confirmation contract")
    if int(payload.get("tracks_issue", -1)) != 158:
        raise ValueError("v2.8.3 confirmation issue changed")
    if payload.get("predeclared_before_any_v2_8_3_structural_or_environmental_outcome") is not True:
        raise ValueError("v2.8.3 confirmation design was not predeclared")

    geometry = payload.get("upstream_geometry_calibration", {})
    if (
        int(geometry.get("workflow_run_id", -1)) != 32943026025
        or geometry.get("implementation_sha") != "32d5b67f7b18634830191df52ef56128589f5d82"
        or int(geometry.get("decision_artifact_id", -1)) != 9609352973
        or geometry.get("decision_artifact_digest")
        != "sha256:a08c9f40d89b65ccf7357289b7e89bda7e6844cc6c2014edaeafb14c368c63d6"
        or float(geometry.get("selected_global_sealed_fraction", -1)) != 0.25
        or geometry.get("fraction_retuning_allowed") is not False
        or geometry.get("geometry_result_is_ecological_support") is not False
    ):
        raise ValueError("v2.8 geometry calibration identity/decision changed")

    repo = _repo_root(source)
    panel = payload.get("fresh_taxon_panel", {})
    panel_path = repo / str(panel.get("path", ""))
    if not panel_path.exists() or sha256_file(panel_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 fresh panel bytes changed")
    panel_frame = pd.read_csv(panel_path)
    if (
        len(panel_frame) != 12
        or panel_frame["scientific_name"].astype(str).nunique() != 12
        or panel_frame["validation_stratum"].astype(str).nunique() != 12
        or set(panel_frame["candidate_rank"].astype(int)) != {1}
    ):
        raise ValueError("v2.8.3 fresh panel denominator changed")
    if panel.get("sha256") != EXPECTED_PANEL_SHA256 or panel.get("blob_sha") != EXPECTED_PANEL_BLOB_SHA:
        raise ValueError("v2.8.3 fresh panel provenance changed")
    if panel.get("post_selection_replacement_allowed") is not False:
        raise ValueError("v2.8.3 permits post-selection panel replacement")
    if panel.get("independence_axis") != "taxon_holdout_not_temporal" or panel.get("temporal_independence_claim_allowed") is not False:
        raise ValueError("v2.8.3 independence claim boundary changed")

    upstream = payload.get("upstream_fresh_source", {})
    receipt_path = repo / str(upstream.get("receipt_path", ""))
    if not receipt_path.exists():
        raise ValueError("v2.8.3 source receipt missing")
    if upstream.get("receipt_blob_sha") != EXPECTED_SOURCE_RECEIPT_BLOB_SHA:
        raise ValueError("v2.8.3 source receipt Git blob changed")
    receipt = load_v2_8_3_source_receipt(receipt_path)
    if int(upstream.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN_ID:
        raise ValueError("v2.8.3 source run changed")
    for key, expected in {
        "focal_file_sha256": EXPECTED_FOCAL_SHA256,
        "focal_query_sha256": EXPECTED_FOCAL_QUERY_SHA256,
        "target_file_sha256": EXPECTED_TARGET_SHA256,
        "target_query_sha256": EXPECTED_TARGET_QUERY_SHA256,
        "snapshot_shard_catalog_sha256": EXPECTED_SNAPSHOT_CATALOG_SHA256,
    }.items():
        if upstream.get(key) != expected:
            raise ValueError(f"v2.8.3 source identity changed: {key}")
    if receipt["fresh_taxon_panel"]["sha256"] != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 source receipt panel differs")

    design = payload.get("fixed_design", {})
    if tuple(int(x) for x in design.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.8.3 split seeds changed")
    if tuple(float(x) for x in design.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.8.3 sealed fraction changed")
    if tuple(int(x) for x in design.get("M_km", ())) != EXPECTED_M:
        raise ValueError("v2.8.3 M grid changed")
    if int(design.get("n_confirmation_parts", -1)) != 3:
        raise ValueError("v2.8.3 confirmation denominator changed")
    if design.get("M_is_sensitivity_not_optimization") is not True:
        raise ValueError("v2.8.3 M became an optimization axis")
    for key, expected in {
        "outer_folds": 4,
        "spatial_microblocks": 12,
        "assignment_attempts": 32,
        "minimum_evaluation_occurrences_per_fold": 2,
        "minimum_evaluation_background_rows_per_M_fold": 5,
        "minimum_training_background_rows_per_M_fold": 5,
    }.items():
        if int(design.get(key, -1)) != expected:
            raise ValueError(f"v2.8.3 structural design changed: {key}")
    if tuple(str(x) for x in design.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("v2.8.3 process domains changed")
    if design.get("process_registry_sha256") != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry SHA changed")
    registry_path = repo / str(design.get("process_registry_path", ""))
    if not registry_path.exists() or sha256_file(registry_path) != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry bytes changed")

    library = design.get("procedure_library", {})
    if tuple(library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("v2.8.3 procedure strategies changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("v2.8.3 model specs changed")
    for key, expected in {"inner_folds": 3, "outer_folds": 4, "max_predictors": 8}.items():
        if int(library.get(key, -1)) != expected:
            raise ValueError(f"v2.8.3 procedure library changed: {key}")
    if float(library.get("vif_threshold", -1)) != 5.0 or float(library.get("predictive_min_gain", -1)) != 0.0:
        raise ValueError("v2.8.3 procedure thresholds changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("v2.8.3 CHELSA confirmation has no fitted observation-process predictor")

    inherited = payload.get("inherited_scientific_semantics", {})
    if int(inherited.get("model_random_state", -1)) != 0 or int(inherited.get("selection_process_numpy_seed", -1)) != 0:
        raise ValueError("v2.8.3 deterministic RNG identity changed")
    if inherited.get("solver") != "liblinear":
        raise ValueError("v2.8.3 deterministic solver changed")
    for key in (
        "all_other_model_hyperparameters_changed", "procedure_strategies_changed",
        "candidate_predictor_universe_changed", "prediction_adequacy_changed",
        "ecological_recovery_metrics_changed", "weighted_super_score_allowed",
    ):
        if inherited.get(key) is not False:
            raise ValueError(f"v2.8.3 inherited science changed: {key}")

    structural = payload.get("structural_transportability", {})
    if int(structural.get("n_taxon_M_part_cells", -1)) != 108 or int(structural.get("n_cells_per_part", -1)) != 36:
        raise ValueError("v2.8.3 structural denominator changed")
    if structural.get("environmental_extraction_allowed_only_for_structurally_auditable_complete_parts") is not True:
        raise ValueError("v2.8.3 structural admission no longer gates environment")
    if structural.get("taxon_M_or_seed_replacement_after_structural_result_allowed") is not False or structural.get("incomplete_part_partial_repair_allowed") is not False:
        raise ValueError("v2.8.3 structural result permits rescue")

    translation = payload.get("single_fraction_denominator_translation", {})
    if (
        int(translation.get("predecessor_parts", -1)) != 6
        or int(translation.get("successor_parts", -1)) != 3
        or int(translation.get("ecological_nondomination_successor_minimum_parts", -1)) != 2
        or int(translation.get("strict_improvement_successor_minimum_parts", -1)) != 2
        or translation.get("duplicate_0_25_parts_allowed") is not False
        or translation.get("new_post_calibration_split_seeds_allowed") is not False
    ):
        raise ValueError("v2.8.3 single-fraction denominator translation changed")

    decision = payload.get("decision_rule", {})
    if not all(decision.get(key) is True for key in (
        "all_3_parts_required_for_primary_full_denominator_decision",
        "all_12_taxa_required_in_every_part",
        "all_3_M_specs_required_in_every_part",
        "structural_or_audit_abstention_makes_part_unavailable_not_pass",
    )):
        raise ValueError("v2.8.3 primary decision denominator changed")
    if decision.get("fewer_than_3_structurally_auditable_parts_primary_state") != "empirical_confirmation_unavailable":
        raise ValueError("v2.8.3 structural fail-closed state changed")
    if decision.get("zero_structurally_auditable_parts_opens_environmental_or_sealed_evidence") is not False:
        raise ValueError("v2.8.3 zero-part gate opens scientific evidence")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("v2.8.3 prediction guardrail changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 2 or int(eco.get("strict_improvement_minimum_parts", -1)) != 2:
        raise ValueError("v2.8.3 ecological decision threshold changed")
    proc = decision.get("process_reproducibility", {})
    if abs(float(proc.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("v2.8.3 process reproducibility changed")
    for key in (
        "post_outcome_candidate_reselection_allowed", "post_outcome_threshold_tuning_allowed",
        "random_seed_changes_after_outcome_allowed", "scientific_promotion_allowed_by_this_decision",
    ):
        if decision.get(key) is not False:
            raise ValueError(f"v2.8.3 decision crossed frozen boundary: {key}")
    if decision.get("product_b_remains_blocked_until_separate_promotion_decision") is not True:
        raise ValueError("v2.8.3 confirmation unblocked Product B")

    boundary = payload.get("execution_boundary", {})
    if boundary.get("execution_allowed") is not False:
        raise ValueError("v2.8.3 design self-authorized execution")
    for key in (
        "structural_query_allowed_before_separate_runtime_freeze_and_authorization",
        "environmental_extraction_allowed_before_separate_runtime_freeze_and_authorization",
        "model_fitting_allowed_before_separate_runtime_freeze_and_authorization",
        "sealed_ecological_read_allowed_before_separate_runtime_freeze_and_authorization",
        "scientific_promotion_allowed", "product_b_unblocked",
    ):
        if boundary.get(key) is not False:
            raise ValueError(f"v2.8.3 design crossed execution boundary: {key}")
    if boundary.get("separate_external_one_shot_authorization_required") is not True:
        raise ValueError("v2.8.3 separate execution authorization requirement changed")
    return payload


def load_v2_8_3_source_receipt(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_2_fresh_raw_source_receipt":
        raise ValueError("wrong v2.8.2 raw-source receipt")
    if int(payload.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN_ID or payload.get("workflow_conclusion") != "success":
        raise ValueError("v2.8.2 raw-source run identity changed")
    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("sha256") != EXPECTED_PANEL_SHA256 or int(panel.get("n_taxa", -1)) != 12:
        raise ValueError("v2.8.2 raw-source panel identity changed")
    if float(panel.get("selected_global_sealed_fraction", -1)) != 0.25 or panel.get("sealed_fraction_retuning_allowed") is not False:
        raise ValueError("v2.8.2 source receipt changed calibrated fraction")
    focal = payload.get("focal", {})
    target = payload.get("target_group", {})
    if focal.get("file_sha256") != EXPECTED_FOCAL_SHA256 or focal.get("query_sha256") != EXPECTED_FOCAL_QUERY_SHA256:
        raise ValueError("v2.8.2 focal raw-source fingerprint changed")
    if target.get("file_sha256") != EXPECTED_TARGET_SHA256 or target.get("query_sha256") != EXPECTED_TARGET_QUERY_SHA256:
        raise ValueError("v2.8.2 target raw-source fingerprint changed")
    if target.get("excluded_taxa_sha256") != EXPECTED_PANEL_SHA256 or int(target.get("excluded_taxa_count", -1)) != 12:
        raise ValueError("v2.8.2 target exclusion changed")
    if float(target.get("one_per_grid_cell_degrees", -1)) != 0.05:
        raise ValueError("v2.8.2 target sampling changed")
    snapshot = payload.get("snapshot", {})
    if int(snapshot.get("snapshot_shard_count", -1)) != 9705 or snapshot.get("snapshot_shard_catalog_sha256") != EXPECTED_SNAPSHOT_CATALOG_SHA256:
        raise ValueError("v2.8.2 snapshot catalog changed")
    barrier = payload.get("information_barrier", {})
    for key in (
        "environmental_values_read", "CHELSA_environmental_values_read",
        "candidate_model_fitting_performed", "candidate_scores_read",
        "niche_recovery_outcomes_read", "sealed_confirmation_outcomes_read",
        "scientific_confirmation_allowed", "scientific_promotion_allowed", "product_b_unblocked",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"v2.8.2 source receipt crossed barrier: {key}")
    return payload


def as_v2_7_2_worker_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a v2.7.2 worker-shaped view without changing v2.8.3 science."""
    result = copy.deepcopy(payload)
    design = result["fixed_design"]
    library = design["procedure_library"]
    inherited = result["inherited_scientific_semantics"]
    library["model_random_state"] = int(inherited["model_random_state"])
    library["selection_process_numpy_seed"] = int(inherited["selection_process_numpy_seed"])
    result["partition_aware_audit_space"] = copy.deepcopy(design["partition_aware_audit_space"])
    result["evidence_balanced_partition"] = {
        "outer_folds": int(design["outer_folds"]),
        "spatial_microblocks": int(design["spatial_microblocks"]),
        "assignment_attempts": int(design["assignment_attempts"]),
        "assignment_seed_formula": str(design["assignment_seed_formula"]),
        "microblock_constructor": "KMeans_on_model_pool_occurrence_unit_sphere_coordinates",
        "fold_assignment": "StratifiedGroupKFold_over_presence_and_all_M_background_resource_types",
        "shared_occurrence_fold_assignment_across_all_M": True,
        "microblock_atomicity_preserved": True,
        "minimum_evaluation_occurrences_per_fold": int(design["minimum_evaluation_occurrences_per_fold"]),
        "minimum_evaluation_background_rows_per_M_fold": int(design["minimum_evaluation_background_rows_per_M_fold"]),
        "minimum_training_background_rows_per_M_fold": int(design["minimum_training_background_rows_per_M_fold"]),
        "choose_feasible_assignment_by": "minimum_max_then_mean_normalized_row_count_imbalance",
        "abstain_if_no_feasible_assignment": True,
        "sealed_rows_used_for_partition_assignment": False,
        "environmental_values_used_for_partition_assignment": False,
        "candidate_scores_used_for_partition_assignment": False,
        "process_knockout_outcomes_used_for_partition_assignment": False,
    }
    result["fresh_taxon_panel"]["require_all_12_taxa"] = True
    return result
