"""Fail-closed loaders for Product-A v2.8.3 fresh scientific confirmation.

The v2.8.3 runtime inherits the deterministic v2.7.2 scientific core, but changes
only the already frozen fresh source/panel, the single calibrated sealed fraction
0.25, and the predeclared three-part/structural-transportability wrapper.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_SOURCE_RECEIPT_BLOB = "ed4d90a84db354e06a4a214f6a3a184c7e36ea7f"
EXPECTED_SOURCE_RECEIPT_MERGE = "641b0cce93f5349fc00577bdd12312f327f854c5"
EXPECTED_SOURCE_RUN = 33006988136
EXPECTED_PANEL_SHA256 = "835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1"
EXPECTED_FOCAL_SHA256 = "4366258f2495604a0c9a5058aeb0111a751493b538ba436760f8555182d32fc5"
EXPECTED_TARGET_SHA256 = "9e8fb2827919e86d450cb5870093cef2adc752bee22a15540406265747d20bf6"
EXPECTED_FOCAL_QUERY_SHA256 = "40f25b5bafff11f5471b389778e29d29f7be02a4e76cd335cfdcee637517dc7e"
EXPECTED_TARGET_QUERY_SHA256 = "b2261d66b156189bf9fd949046ad4f5b0a10697c584efe2ba009ca2d5dc8fdf7"
EXPECTED_PROCESS_REGISTRY_SHA256 = "08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d"
EXPECTED_PREDECESSOR_CONTRACT_BLOB = "04ec0d9519b8ea5ed7720f04cffb79ec0cdf4291"
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


def load_v2_8_3_fresh_confirmation_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_3_fresh_taxon_holdout_empirical_confirmation_contract":
        raise ValueError("wrong v2.8.3 scientific confirmation contract")
    if payload.get("tracks_issue") != 158 or payload.get("resolves_methodology_issue") != 132:
        raise ValueError("v2.8.3 methodological provenance changed")
    if payload.get("predeclared_before_any_v2_8_3_environmental_model_or_sealed_outcome") is not True:
        raise ValueError("v2.8.3 scientific rule was not predeclared")
    if payload.get("stage_execution_allowed") is not False:
        raise ValueError("v2.8.3 stage must remain non-executing")
    if payload.get("separate_external_one_shot_authorization_required") is not True:
        raise ValueError("v2.8.3 external authorization gate changed")
    if payload.get("scientific_promotion_run") is not False or payload.get("product_b_unblocked") is not False:
        raise ValueError("v2.8.3 scientific runtime cannot promote Product A or unblock Product B")

    source_pin = payload.get("source_receipt", {})
    if source_pin.get("blob_sha") != EXPECTED_SOURCE_RECEIPT_BLOB:
        raise ValueError("v2.8.3 source receipt blob pin changed")
    if source_pin.get("merged_at_sha") != EXPECTED_SOURCE_RECEIPT_MERGE:
        raise ValueError("v2.8.3 source receipt merge pin changed")
    if int(source_pin.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN or source_pin.get("workflow_conclusion") != "success":
        raise ValueError("v2.8.3 source run identity changed")

    continuity = payload.get("predecessor_rule_continuity", {})
    if continuity.get("scientific_predecessor_contract_blob_sha") != EXPECTED_PREDECESSOR_CONTRACT_BLOB:
        raise ValueError("v2.8.3 deterministic predecessor contract changed")
    for key in (
        "v2_7_1_scientific_meaning_inherited",
        "v2_7_2_deterministic_correction_inherited",
    ):
        if continuity.get(key) is not True:
            raise ValueError(f"v2.8.3 predecessor continuity changed: {key}")
    if continuity.get("scientific_thresholds_retuned_from_outcomes") is not False:
        raise ValueError("v2.8.3 thresholds were retuned")
    for key in (
        "M_grid_changed", "partition_rule_changed", "audit_space_rule_changed",
        "procedure_strategies_changed", "model_hyperparameters_changed",
        "process_domains_changed", "sealed_recovery_metrics_changed",
    ):
        if continuity.get(key) is not False:
            raise ValueError(f"v2.8.3 inherited science changed: {key}")

    repo = _repo_root(source)
    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("sha256") != EXPECTED_PANEL_SHA256 or panel.get("require_all_12_taxa") is not True:
        raise ValueError("v2.8.3 panel identity changed")
    panel_path = repo / str(panel.get("path", ""))
    if not panel_path.exists() or sha256_file(panel_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 panel bytes changed")
    frame = pd.read_csv(panel_path)
    if len(frame) != 12 or frame["scientific_name"].astype(str).nunique() != 12:
        raise ValueError("v2.8.3 panel denominator changed")
    if frame["validation_stratum"].astype(str).nunique() != 12:
        raise ValueError("v2.8.3 validation-stratum denominator changed")
    if set(pd.to_numeric(frame["candidate_rank"]).astype(int)) != {1}:
        raise ValueError("v2.8.3 candidate rank changed")

    design = payload.get("fixed_design", {})
    if tuple(int(x) for x in design.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.8.3 split seeds changed")
    if tuple(float(x) for x in design.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.8.3 calibrated sealed fraction changed")
    if tuple(int(x) for x in design.get("M_km", ())) != EXPECTED_M:
        raise ValueError("v2.8.3 M sensitivity grid changed")
    if int(design.get("n_confirmation_parts", -1)) != 3:
        raise ValueError("v2.8.3 must have exactly three nonduplicated parts")
    if tuple(str(x) for x in design.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("v2.8.3 process domains changed")
    if design.get("process_registry_sha256") != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry fingerprint changed")
    registry_path = repo / str(design.get("process_registry_path", ""))
    if not registry_path.exists() or sha256_file(registry_path) != EXPECTED_PROCESS_REGISTRY_SHA256:
        raise ValueError("v2.8.3 process registry bytes changed")

    library = design.get("procedure_library", {})
    if tuple(library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("v2.8.3 procedure strategies changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("v2.8.3 model specifications changed")
    if int(library.get("model_random_state", -1)) != 0 or int(library.get("selection_process_numpy_seed", -1)) != 0:
        raise ValueError("v2.8.3 deterministic RNG identity changed")
    for key, expected in {"inner_folds": 3, "outer_folds": 4, "max_predictors": 8}.items():
        if int(library.get(key, -1)) != expected:
            raise ValueError(f"v2.8.3 procedure library changed: {key}")
    if float(library.get("vif_threshold", -1)) != 5.0 or float(library.get("predictive_min_gain", -1)) != 0.0:
        raise ValueError("v2.8.3 procedure thresholds changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("v2.8.3 CHELSA run has no fitted observation-process predictor")

    adequacy = design.get("prediction_adequacy", {})
    if adequacy != {
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "complete_outer_fold_evidence_required": True,
    }:
        raise ValueError("v2.8.3 prediction adequacy changed")

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
        raise ValueError("v2.8.3 evidence-balanced partition changed")

    audit = payload.get("partition_aware_audit_space", {})
    if audit != {
        "minimum_predictor_coverage": 0.95,
        "minimum_joint_coverage": 0.8,
        "minimum_processes": 4,
        "minimum_complete_fit_background_rows_per_M_fold": 5,
        "minimum_complete_evaluation_background_rows_per_M_fold": 5,
        "minimum_complete_heldout_occurrence_rows_per_M_fold": 2,
        "sealed_rows_used": False,
        "candidate_scores_used": False,
        "thresholds_unchanged_from_v2_7_2": True,
    }:
        raise ValueError("v2.8.3 audit-space rule changed")

    structural = payload.get("structural_transportability", {})
    if int(structural.get("n_expected_taxon_M_part_cells", -1)) != 108:
        raise ValueError("v2.8.3 structural denominator changed")
    for key in (
        "runs_before_any_CHELSA_or_environmental_value_read",
        "runs_before_candidate_model_fitting",
        "runs_before_candidate_score_read",
        "runs_before_sealed_ecological_outcome_read",
        "part_structurally_auditable_if_all_12_taxa_x_all_3_M_joint_support_is_feasible",
        "primary_full_denominator_requires_all_3_parts_structurally_auditable",
        "conditional_ecology_allowed_only_for_complete_structurally_auditable_parts",
    ):
        if structural.get(key) is not True:
            raise ValueError(f"v2.8.3 structural gate changed: {key}")
    for key in (
        "taxon_seed_M_source_or_threshold_replacement_after_structural_result_allowed",
        "incomplete_part_partial_repair_allowed",
        "structural_support_is_ecological_support",
    ):
        if structural.get(key) is not False:
            raise ValueError(f"v2.8.3 structural fail-closed rule changed: {key}")

    decision = payload.get("decision_rule", {})
    if decision.get("all_3_parts_required_for_primary_decision") is not True:
        raise ValueError("v2.8.3 primary denominator changed")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("v2.8.3 prediction guardrail changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 2 or int(eco.get("strict_improvement_minimum_parts", -1)) != 2:
        raise ValueError("v2.8.3 three-part ecological decision changed")
    proc = decision.get("process_reproducibility", {})
    if abs(float(proc.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("v2.8.3 process reproducibility threshold changed")
    for key in (
        "post_outcome_candidate_reselection_allowed", "post_outcome_threshold_tuning_allowed",
        "post_outcome_random_seed_change_allowed", "post_outcome_fraction_change_allowed",
        "scientific_promotion_allowed_by_this_decision",
    ):
        if decision.get(key) is not False:
            raise ValueError(f"v2.8.3 post-outcome/promotion barrier changed: {key}")
    if decision.get("product_b_remains_blocked_until_separate_promotion_decision") is not True:
        raise ValueError("v2.8.3 Product-B barrier changed")
    return payload


def load_v2_8_3_source_receipt(
    path: str | Path, *, source_gate_path: str | Path | None = None
) -> dict[str, Any]:
    # source_gate_path is intentionally accepted for v2.7.2 core-call compatibility;
    # v2.8.3 has one already merged repository receipt rather than a mutable source gate.
    del source_gate_path
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_2_fresh_raw_source_receipt":
        raise ValueError("wrong v2.8.2 source receipt for v2.8.3")
    if int(payload.get("workflow_run_id", -1)) != EXPECTED_SOURCE_RUN or payload.get("workflow_conclusion") != "success":
        raise ValueError("v2.8.3 source run changed")
    panel = payload.get("fresh_taxon_panel", {})
    if panel.get("sha256") != EXPECTED_PANEL_SHA256 or float(panel.get("selected_global_sealed_fraction", -1)) != 0.25:
        raise ValueError("v2.8.3 source panel/fraction changed")
    focal, target = payload.get("focal", {}), payload.get("target_group", {})
    if focal.get("file_sha256") != EXPECTED_FOCAL_SHA256 or focal.get("query_sha256") != EXPECTED_FOCAL_QUERY_SHA256:
        raise ValueError("v2.8.3 focal source fingerprint changed")
    if target.get("file_sha256") != EXPECTED_TARGET_SHA256 or target.get("query_sha256") != EXPECTED_TARGET_QUERY_SHA256:
        raise ValueError("v2.8.3 target source fingerprint changed")
    if target.get("excluded_taxa_sha256") != EXPECTED_PANEL_SHA256 or float(target.get("one_per_grid_cell_degrees", -1)) != 0.05:
        raise ValueError("v2.8.3 target exclusion/sampling changed")
    barrier = payload.get("information_barrier", {})
    for key, value in barrier.items():
        if value is not False:
            raise ValueError(f"v2.8.2 source receipt crossed information barrier before v2.8.3: {key}")
    return payload


def v2_7_3_structural_core_view(contract: dict[str, Any]) -> dict[str, Any]:
    """Return an in-memory compatibility view for the coordinate-only v2.7.3 gate."""
    view = deepcopy(contract)
    view["rank3_panel"] = {
        "path": contract["fresh_taxon_panel"]["path"],
        "sha256": contract["fresh_taxon_panel"]["sha256"],
    }
    view["inherited_evidence_balanced_partition"] = deepcopy(
        contract["evidence_balanced_partition"]
    )
    return view
