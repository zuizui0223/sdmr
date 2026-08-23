"""Fail-closed loaders for Product-A v2.7.2 fresh rank-2 confirmation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_PANEL_SHA256 = "918ea2d3e94f93c26616ab30aa055a5dd72b4550d75dbbeb6a675e7a4e950f44"
EXPECTED_PROCESS_REGISTRY_SHA256 = "08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d"
EXPECTED_SEEDS = (2026082201, 2026082202, 2026082203)
EXPECTED_FRACTIONS = (0.20, 0.30)
EXPECTED_M = (150, 300, 500)
EXPECTED_DOMAINS = (
    "thermal", "water", "seasonality_phenology", "energy_productivity", "snow", "wind"
)
EXPECTED_STRATEGIES = ("all", "vif", "predictive_forward", "niche_forward")
EXPECTED_MODEL_SPECS = (
    {"C": 0.1, "degree": 1, "penalty": "l2"},
    {"C": 1.0, "degree": 2, "penalty": "l2"},
)
EXPECTED_MODEL_RANDOM_STATE = 0
EXPECTED_PROCESS_NUMPY_SEED = 0


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _repo_root(path: Path) -> Path:
    return path.parent.parent


def load_v2_7_2_fresh_confirmation_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_2_fresh_taxon_holdout_empirical_confirmation_contract":
        raise ValueError("wrong v2.7.2 fresh confirmation contract")
    if payload.get("predeclared_before_any_v2_7_2_empirical_model_or_sealed_outcome") is not True:
        raise ValueError("v2.7.2 empirical decision was not predeclared")
    if payload.get("independence_axis") != "taxon_holdout_not_temporal":
        raise ValueError("v2.7.2 independence axis changed")
    if payload.get("temporal_independence_claim_allowed") is not False:
        raise ValueError("v2.7.2 may not claim temporal independence")
    if payload.get("scientific_promotion_run") is not False or payload.get("product_b_unblocked") is not False:
        raise ValueError("v2.7.2 confirmation cannot directly promote Product A or unblock Product B")

    known = payload.get("known_truth_prerequisite", {})
    if known.get("determinism_passed") is not True or known.get("scientific_nonregression_supported") is not True:
        raise ValueError("v2.7.2 empirical run requires the frozen known-truth endpoint")
    if int(known.get("workflow_run_id", -1)) != 32629842082:
        raise ValueError("v2.7.2 known-truth run identity changed")

    continuity = payload.get("predecessor_rule_continuity", {})
    changed = [key for key, value in continuity.items() if key.endswith("_changed") and value is not False]
    if changed:
        raise ValueError(f"v2.7.2 changed frozen predecessor science: {changed}")
    if continuity.get("model_hyperparameters_changed_except_random_identity") is not False:
        raise ValueError("v2.7.2 changed model hyperparameters beyond deterministic identity")
    if continuity.get("only_method_change") != "explicit deterministic estimator/process RNG identity":
        raise ValueError("v2.7.2 method-change boundary changed")

    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("sha256") != EXPECTED_PANEL_SHA256 or panel.get("require_all_12_taxa") is not True:
        raise ValueError("v2.7.2 panel identity changed")
    if int(panel.get("predeclared_candidate_rank", -1)) != 2:
        raise ValueError("v2.7.2 panel rank changed")
    if panel.get("disjoint_from_product_a_pilot_12") is not True or panel.get("disjoint_from_v2_7_1_fresh_rank1_panel") is not True:
        raise ValueError("v2.7.2 panel disjointness contract changed")
    repo = _repo_root(source)
    panel_path = repo / str(panel.get("path", ""))
    if not panel_path.exists() or sha256_file(panel_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.7.2 panel file fingerprint changed")
    panel_frame = pd.read_csv(panel_path)
    if len(panel_frame) != 12 or panel_frame["scientific_name"].astype(str).nunique() != 12:
        raise ValueError("v2.7.2 panel denominator changed")

    design = payload.get("fixed_design", {})
    if tuple(int(x) for x in design.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.7.2 split seeds changed")
    if tuple(float(x) for x in design.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.7.2 sealed fractions changed")
    if tuple(int(x) for x in design.get("M_km", ())) != EXPECTED_M:
        raise ValueError("v2.7.2 M grid changed")
    if int(design.get("n_confirmation_parts", -1)) != 6:
        raise ValueError("v2.7.2 confirmation denominator changed")
    if tuple(str(x) for x in design.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("v2.7.2 process domains changed")
    if design.get("process_registry_sha256") != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.7.2 process registry identity changed")
    registry_path = repo / str(design.get("process_registry_path", ""))
    if not registry_path.exists() or sha256_file(registry_path) != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.7.2 process registry file changed")

    library = design.get("procedure_library", {})
    if tuple(library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("v2.7.2 procedure strategies changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("v2.7.2 model specs changed")
    if int(library.get("model_random_state", -1)) != EXPECTED_MODEL_RANDOM_STATE:
        raise ValueError("v2.7.2 model random state changed")
    if int(library.get("selection_process_numpy_seed", -1)) != EXPECTED_PROCESS_NUMPY_SEED:
        raise ValueError("v2.7.2 selection process seed changed")
    for key, value in {"inner_folds": 3, "outer_folds": 4, "max_predictors": 8}.items():
        if int(library.get(key, -1)) != value:
            raise ValueError(f"v2.7.2 procedure library changed: {key}")
    if float(library.get("vif_threshold", -1)) != 5.0 or float(library.get("predictive_min_gain", -1)) != 0.0:
        raise ValueError("v2.7.2 procedure thresholds changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("v2.7.2 CHELSA run has no fitted observation-process predictor")

    adequacy = design.get("prediction_adequacy", {})
    if adequacy != {
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "complete_outer_fold_evidence_required": True,
    }:
        raise ValueError("v2.7.2 prediction adequacy changed")

    partition = payload.get("evidence_balanced_partition", {})
    expected_partition = {
        "outer_folds": 4,
        "spatial_microblocks": 12,
        "assignment_attempts": 32,
        "assignment_seed_formula": "part_seed + taxon_index*100 + 271",
        "microblock_constructor": "KMeans_on_model_pool_occurrence_unit_sphere_coordinates",
        "fold_assignment": "StratifiedGroupKFold_over_presence_and_all_M_background_resource_types",
        "shared_occurrence_fold_assignment_across_all_M": True,
        "microblock_atomicity_preserved": True,
        "minimum_evaluation_occurrences_per_fold": 2,
        "minimum_evaluation_background_rows_per_M_fold": 5,
        "minimum_training_background_rows_per_M_fold": 5,
        "choose_feasible_assignment_by": "minimum_max_then_mean_normalized_row_count_imbalance",
        "abstain_if_no_feasible_assignment": True,
        "sealed_rows_used_for_partition_assignment": False,
        "environmental_values_used_for_partition_assignment": False,
        "candidate_scores_used_for_partition_assignment": False,
        "process_knockout_outcomes_used_for_partition_assignment": False,
    }
    if partition != expected_partition:
        raise ValueError("v2.7.2 evidence-balanced partition changed")

    audit = payload.get("partition_aware_audit_space", {})
    expected_audit = {
        "minimum_predictor_coverage": 0.95,
        "minimum_joint_coverage": 0.8,
        "minimum_processes": 4,
        "minimum_complete_fit_background_rows_per_M_fold": 5,
        "minimum_complete_evaluation_background_rows_per_M_fold": 5,
        "minimum_complete_heldout_occurrence_rows_per_M_fold": 2,
        "sealed_rows_used": False,
        "candidate_scores_used": False,
        "thresholds_unchanged_from_v2_7_1": True,
    }
    if audit != expected_audit:
        raise ValueError("v2.7.2 audit-space contract changed")

    target = payload.get("empirical_target", {})
    if target.get("claim") != "realized_environmental_niche_recovery_and_stability":
        raise ValueError("v2.7.2 empirical target changed")
    if target.get("ordinary_prediction_metrics_are_guardrails_not_tuning_target") is not True:
        raise ValueError("prediction became the v2.7.2 tuning target")
    if target.get("recovery_metrics_must_remain_separate") is not True or target.get("weighted_super_score_allowed") is not False:
        raise ValueError("v2.7.2 recovery metrics must remain separate")
    if target.get("fundamental_niche_truth_claim_allowed") is not False:
        raise ValueError("presence-only v2.7.2 cannot claim fundamental niche truth")

    barrier = payload.get("information_barrier", {})
    if barrier.get("outer_sealed_before_M") is not True or barrier.get("M_built_from_model_pool_only") is not True:
        raise ValueError("v2.7.2 seal-before-M barrier changed")
    for key in (
        "sealed_occurrences_used_for_M", "sealed_occurrences_used_for_partition_assignment",
        "sealed_occurrences_used_for_candidate_selection", "v2_7_1_rank1_model_pool_or_sealed_rows_reused",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"v2.7.2 information barrier changed: {key}")

    decision = payload.get("decision_rule", {})
    if not all(decision.get(k) is True for k in (
        "all_6_parts_required", "all_12_taxa_required_in_every_part",
        "all_3_M_specs_required_in_every_part",
        "structural_or_audit_abstention_makes_part_unavailable_not_pass",
    )):
        raise ValueError("v2.7.2 decision denominator changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 4 or int(eco.get("strict_improvement_minimum_parts", -1)) != 3:
        raise ValueError("v2.7.2 ecological decision rule changed")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("v2.7.2 prediction guardrail changed")
    proc = decision.get("process_reproducibility", {})
    if abs(float(proc.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("v2.7.2 process reproducibility threshold changed")
    if decision.get("post_outcome_candidate_reselection_allowed") is not False or decision.get("post_outcome_threshold_tuning_allowed") is not False or decision.get("post_outcome_random_seed_change_allowed") is not False:
        raise ValueError("v2.7.2 permits post-outcome tuning")
    return payload


def load_v2_7_2_source_receipt(
    receipt_path: str | Path,
    *,
    source_gate_path: str | Path,
) -> dict[str, Any]:
    gate = json.loads(Path(source_gate_path).read_text(encoding="utf-8"))
    if gate.get("purpose") != "product_a_v2_7_2_fresh_empirical_source_gate":
        raise ValueError("wrong v2.7.2 source gate")
    required = gate.get("required_before_execution", {})
    needed = (
        "new_rank2_focal_artifact_run_id", "focal_file_sha256", "focal_query_sha256",
        "new_rank2_excluding_target_group_artifact_run_id", "target_group_file_sha256",
        "target_group_query_sha256", "raw_source_receipt_artifact_id",
        "raw_source_receipt_artifact_digest",
    )
    if any(required.get(key) in (None, "") for key in needed):
        raise ValueError("v2.7.2 raw-source identities are not fully pinned")
    payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_2_fresh_raw_source_receipt":
        raise ValueError("wrong v2.7.2 raw-source receipt")
    if payload.get("workflow_conclusion") != "success":
        raise ValueError("v2.7.2 raw-source run did not succeed")
    if payload.get("fresh_taxon_panel_sha256") != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.7.2 source panel identity changed")
    focal = payload.get("focal", {})
    target = payload.get("target_group", {})
    if focal.get("file_sha256") != required["focal_file_sha256"] or focal.get("query_sha256") != required["focal_query_sha256"]:
        raise ValueError("v2.7.2 focal source fingerprint changed")
    if target.get("file_sha256") != required["target_group_file_sha256"] or target.get("query_sha256") != required["target_group_query_sha256"]:
        raise ValueError("v2.7.2 target source fingerprint changed")
    if target.get("excluded_taxa_sha256") != EXPECTED_PANEL_SHA256 or float(target.get("one_per_grid_cell_degrees", -1)) != 0.05:
        raise ValueError("v2.7.2 target exclusion/sampling contract changed")
    barrier = payload.get("information_barrier", {})
    for key in (
        "environmental_values_read", "candidate_model_fitting_performed",
        "sealed_confirmation_outcomes_read", "scientific_promotion_allowed", "product_b_unblocked",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"v2.7.2 source receipt crossed barrier: {key}")
    return payload
