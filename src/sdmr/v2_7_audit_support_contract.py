"""Fail-closed loader for Product-A v2.7 audit-support development."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PURPOSE = "product_a_v2_7_audit_support_development_contract"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v2_7_audit_support_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-A v2.7 audit-support purpose changed")
    for key in ("development_only",):
        if payload.get(key) is not True:
            raise ValueError(f"Product-A v2.7 requires {key}=true")
    for key in (
        "scientific_promotion_allowed",
        "independent_empirical_confirmation_claim_allowed",
        "product_b_unblocked",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"Product-A v2.7 development requires {key}=false")

    predecessor = payload.get("predecessor_v2_6_empirical_result", {})
    expected_predecessor = {
        "exact_run_id": 32445550518,
        "exact_head_sha": "5ce106bb955d0912b1c65ff8dd23a61a3e66aee1",
        "result": "sealed_blind_empirical_confirmation_unavailable",
        "pretruth_artifact_count": 0,
        "sealed_audit_artifact_count": 0,
        "sealed_environment_opened": False,
        "diagnosed_part": "2026081901_0.20",
        "diagnosed_taxon_M_cells": 36,
        "incomplete_taxon_M_cells_per_candidate": 23,
        "all_eight_candidates_incomplete": True,
        "primary_failure": "43_variable_audit_complete_case_support_collapse",
    }
    if predecessor != expected_predecessor:
        raise ValueError("Product-A v2.6 unavailable predecessor evidence changed")

    development_source = payload.get("development_source", {})
    if int(development_source.get("model_pool_materialization_run_id", -1)) != 32260616084:
        raise ValueError("Product-A v2.7 development source changed")
    for key in (
        "model_pool_only_reuse_allowed",
        "current_v2_6_sealed_split_may_not_be_relabelled_as_fresh_v2_7_confirmation",
        "future_independent_confirmation_requires_genuinely_fresh_evidence",
    ):
        if development_source.get(key) is not True:
            raise ValueError(f"Product-A v2.7 development source requires {key}=true")
    if development_source.get("outer_sealed_environment_read_allowed") is not False:
        raise ValueError("Product-A v2.7 development cannot read outer sealed environments")

    candidate = payload.get("candidate_universe", {})
    if candidate.get("process_registry") != "configs/product_a_empirical_process_registry_v1.csv":
        raise ValueError("Product-A v2.7 process registry changed")
    for key in (
        "all_43_predeclared_CHELSA_predictors_remain_candidate_eligible",
        "procedure_library_unchanged_from_v2_6",
        "prediction_adequacy_unchanged_from_v2_6",
        "niche_recovery_metrics_unchanged_from_v2_6",
    ):
        if candidate.get(key) is not True:
            raise ValueError(f"Product-A v2.7 candidate universe requires {key}=true")
    if abs(float(candidate.get("candidate_predictor_availability_gate_unchanged", -1)) - 0.95) > 1e-12:
        raise ValueError("Product-A v2.7 candidate predictor coverage changed")
    if candidate.get("weighted_super_score") is not False:
        raise ValueError("weighted super-score remains forbidden")

    audit = payload.get("audit_space", {})
    expected_audit = {
        "selector": "select_partition_aware_empirical_audit_space",
        "base_selector": "select_empirical_audit_space",
        "one_representative_predictor_per_process_maximum": True,
        "selection_inputs": "model_pool_missingness_only",
        "candidate_scores_used": False,
        "response_magnitudes_used": False,
        "process_knockout_outcomes_used": False,
        "sealed_rows_used": False,
        "minimum_predictor_coverage": 0.95,
        "minimum_joint_coverage": 0.80,
        "minimum_processes": 4,
        "partition_aware_support": True,
        "minimum_complete_fit_background_rows_per_M_fold": 5,
        "minimum_complete_evaluation_background_rows_per_M_fold": 5,
        "minimum_complete_heldout_occurrence_rows_per_M_fold": 2,
        "whole_process_axis_pruning_only": True,
        "pruning_inputs": "complete_row_counts_only",
        "abstain_if_minimum_four_processes_cannot_support_every_M_fold": True,
    }
    if audit != expected_audit:
        raise ValueError("Product-A v2.7 audit-space contract changed")

    information = payload.get("information_order", {})
    for key in (
        "outer_model_pool_partition_fixed_before_candidate_evaluation",
        "audit_space_frozen_before_candidate_benchmark",
        "candidate_benchmark_cannot_change_audit_space",
        "sealed_environment_values_remain_unopened",
    ):
        if information.get(key) is not True:
            raise ValueError(f"Product-A v2.7 information order requires {key}=true")

    success = payload.get("development_success_means", {})
    for key in (
        "audit_support_complete_before_candidate_evaluation",
        "all_four_niche_recovery_metrics_mathematically_evaluable_in_supported_folds",
        "does_not_itself_validate_or_promote_Product_A",
    ):
        if success.get(key) is not True:
            raise ValueError(f"Product-A v2.7 development success requires {key}=true")

    payload["contract_sha256"] = _sha256(source)
    return payload
