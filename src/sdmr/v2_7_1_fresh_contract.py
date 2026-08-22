"""Fail-closed loaders for the Product-A v2.7.1 fresh taxon-holdout run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_CONTRACT_SHA256 = "32ed21aedb87bd796324d569b696b97fc58ddbec2ccd848723006f0ea7b1ba5b"
EXPECTED_PANEL_SHA256 = "40364e45ce523abe346a32bf7fbbfa70f8aba152a4d9a89f845a58c05b64e554"
EXPECTED_PROCESS_REGISTRY_SHA256 = "08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d"
EXPECTED_ELIGIBILITY_CONTRACT_SHA256 = "7a5a3fe8d4fada3f4eb73176a382fe5b020f39bce8ec08a89d922edd9b5511d7"
EXPECTED_SOURCE_RUN_ID = 32477393089
EXPECTED_FOCAL_SHA256 = "96810e03ce557faad28d8b384d2e2e92ce348b405790f52ffff75ab5bd56c0a0"
EXPECTED_TARGET_SHA256 = "4d6b1830c5750a2339258219bfde24f9e20435c69aaf27eca20c72f59c15a66a"
EXPECTED_FOCAL_QUERY_SHA256 = "204080e6ca30cb9eafc7093de82d4e42bacefebd251f15fabb14686da02e1716"
EXPECTED_TARGET_QUERY_SHA256 = "80864205a643f65e9a42b4a5c282423737d207fb186283a6296e5063f630142e"
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


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _repo_root(config_path: Path) -> Path:
    return config_path.parent.parent


def load_v2_7_1_fresh_confirmation_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if sha256_file(source) != EXPECTED_CONTRACT_SHA256:
        raise ValueError("fresh confirmation decision contract fingerprint changed")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_1_fresh_taxon_holdout_empirical_confirmation_contract":
        raise ValueError("fresh confirmation purpose changed")
    if payload.get("predeclared_before_any_fresh_taxon_model_or_sealed_outcome") is not True:
        raise ValueError("fresh decision rule was not predeclared")
    if payload.get("development_70_of_72_used_to_tune_thresholds") is not False:
        raise ValueError("development outcome cannot tune fresh thresholds")
    if payload.get("independence_axis") != "taxon_holdout_not_temporal":
        raise ValueError("fresh independence axis changed")
    if payload.get("temporal_independence_claim_allowed") is not False:
        raise ValueError("fresh run cannot claim temporal independence")
    if payload.get("scientific_promotion_run") is not False or payload.get("product_b_unblocked") is not False:
        raise ValueError("fresh confirmation cannot directly promote Product A or unblock Product B")

    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("sha256") != EXPECTED_PANEL_SHA256 or panel.get("require_all_12_taxa") is not True:
        raise ValueError("fresh taxon panel contract changed")
    repo = _repo_root(source)
    panel_path = repo / str(panel.get("path", ""))
    if not panel_path.exists() or sha256_file(panel_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("fresh taxon panel file fingerprint changed")
    panel_frame = pd.read_csv(panel_path)
    if len(panel_frame) != 12 or panel_frame["scientific_name"].astype(str).nunique() != 12:
        raise ValueError("fresh taxon panel denominator changed")

    design = payload.get("fixed_design", {})
    if tuple(int(x) for x in design.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("fresh split seeds changed")
    if tuple(float(x) for x in design.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("fresh sealed fractions changed")
    if tuple(int(x) for x in design.get("M_km", ())) != EXPECTED_M:
        raise ValueError("fresh M sensitivity grid changed")
    if int(design.get("n_confirmation_parts", -1)) != 6:
        raise ValueError("fresh confirmation denominator changed")
    if tuple(str(x) for x in design.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("fresh process-domain order changed")
    if design.get("process_registry_sha256") != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("fresh process registry fingerprint changed")
    registry_path = repo / str(design.get("process_registry_path", ""))
    if not registry_path.exists() or sha256_file(registry_path) != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("fresh process registry file changed")

    library = design.get("procedure_library", {})
    if tuple(library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("fresh procedure strategy order changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("fresh model-spec library changed")
    for key, value in {"inner_folds": 3, "outer_folds": 4, "max_predictors": 8}.items():
        if int(library.get(key, -1)) != value:
            raise ValueError(f"fresh procedure library changed: {key}")
    if float(library.get("vif_threshold", -1)) != 5.0 or float(library.get("predictive_min_gain", -1)) != 0.0:
        raise ValueError("fresh procedure thresholds changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("fresh CHELSA run has no fitted observation-process predictor")

    adequacy = design.get("prediction_adequacy", {})
    expected_adequacy = {
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "complete_outer_fold_evidence_required": True,
    }
    if adequacy != expected_adequacy:
        raise ValueError("fresh prediction adequacy rule changed")

    partition = payload.get("v2_7_1_evidence_balanced_partition", {})
    expected_partition = {
        "spatial_microblocks": 12,
        "outer_folds": 4,
        "assignment_attempts": 32,
        "assignment_seed_formula": "part_seed + taxon_index*100 + 271",
        "microblock_constructor": "KMeans_on_model_pool_occurrence_unit_sphere_coordinates",
        "microblock_atomicity_preserved": True,
        "fold_assignment": "StratifiedGroupKFold_over_presence_and_all_M_background_resource_types",
        "shared_occurrence_fold_assignment_across_all_M": True,
        "minimum_evaluation_occurrences_per_fold": 2,
        "minimum_evaluation_background_rows_per_M_fold": 5,
        "minimum_training_background_rows_per_M_fold": 5,
        "environmental_values_used_for_partition_assignment": False,
        "candidate_scores_used_for_partition_assignment": False,
        "process_knockout_outcomes_used_for_partition_assignment": False,
        "sealed_rows_used_for_partition_assignment": False,
        "choose_feasible_assignment_by": "minimum_max_then_mean_normalized_row_count_imbalance",
        "abstain_if_no_feasible_assignment": True,
    }
    if partition != expected_partition:
        raise ValueError("fresh evidence-balanced partition contract changed")

    audit = payload.get("v2_7_1_partition_aware_audit_space", {})
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
        raise ValueError("fresh partition-aware audit contract changed")

    target = payload.get("empirical_target", {})
    if target.get("claim") != "realized_environmental_niche_recovery_and_stability":
        raise ValueError("fresh empirical target changed")
    if target.get("fundamental_niche_truth_claim_allowed") is not False:
        raise ValueError("presence-only fresh run cannot claim fundamental niche truth")
    if target.get("ordinary_prediction_metrics_are_guardrails_not_tuning_target") is not True:
        raise ValueError("prediction metric became a fresh tuning target")
    if target.get("recovery_metrics_must_remain_separate") is not True or target.get("weighted_super_score_allowed") is not False:
        raise ValueError("fresh recovery metrics must remain separate")

    decision = payload.get("decision_rule", {})
    if not all(decision.get(k) is True for k in (
        "all_6_parts_required", "all_12_taxa_required_in_every_part", "all_3_M_specs_required_in_every_part",
        "structural_or_audit_abstention_makes_part_unavailable_not_pass",
    )):
        raise ValueError("fresh decision denominator changed")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("fresh prediction guardrail changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 4 or int(eco.get("strict_improvement_minimum_parts", -1)) != 3:
        raise ValueError("fresh ecological decision rule changed")
    proc = decision.get("process_reproducibility", {})
    if abs(float(proc.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("fresh process reproducibility threshold changed")
    if decision.get("post_outcome_candidate_reselection_allowed") is not False or decision.get("post_outcome_threshold_tuning_allowed") is not False:
        raise ValueError("fresh decision permits post-outcome retuning")
    return payload


def load_fresh_eligibility_thresholds(contract_path: str | Path) -> dict[str, int]:
    repo = _repo_root(Path(contract_path))
    path = repo / "configs/product_a_v2_7_1_fresh_taxon_eligibility_contract.json"
    if sha256_file(path) != EXPECTED_ELIGIBILITY_CONTRACT_SHA256:
        raise ValueError("fresh eligibility contract fingerprint changed")
    payload = json.loads(path.read_text(encoding="utf-8"))
    thresholds = payload.get("thresholds", {})
    if int(thresholds.get("minimum_occurrences", -1)) != 80:
        raise ValueError("fresh occurrence eligibility threshold changed")
    if int(thresholds.get("minimum_unique_0_05_degree_cells", -1)) != 50:
        raise ValueError("fresh unique-cell eligibility threshold changed")
    return {"minimum_occurrences": 80, "minimum_unique_cells": 50}


def load_fresh_source_receipt(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_1_fresh_raw_source_receipt":
        raise ValueError("fresh raw-source receipt purpose changed")
    if int(payload.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN_ID or payload.get("workflow_conclusion") != "success":
        raise ValueError("fresh raw-source run identity changed")
    if payload.get("fresh_taxon_panel_sha256") != EXPECTED_PANEL_SHA256:
        raise ValueError("fresh raw-source panel fingerprint changed")
    focal = payload.get("focal", {})
    target = payload.get("target_group", {})
    if focal.get("file_sha256") != EXPECTED_FOCAL_SHA256 or focal.get("query_sha256") != EXPECTED_FOCAL_QUERY_SHA256:
        raise ValueError("fresh focal raw-source fingerprint changed")
    if target.get("file_sha256") != EXPECTED_TARGET_SHA256 or target.get("query_sha256") != EXPECTED_TARGET_QUERY_SHA256:
        raise ValueError("fresh target raw-source fingerprint changed")
    if target.get("excluded_taxa_sha256") != EXPECTED_PANEL_SHA256 or float(target.get("one_per_grid_cell_degrees", -1)) != 0.05:
        raise ValueError("fresh target exclusion/sampling contract changed")
    barrier = payload.get("information_barrier", {})
    for key in ("environmental_values_read", "candidate_model_fitting_performed", "sealed_confirmation_outcomes_read", "scientific_promotion_allowed", "product_b_unblocked"):
        if barrier.get(key) is not False:
            raise ValueError(f"fresh raw-source receipt crossed barrier: {key}")
    return payload
