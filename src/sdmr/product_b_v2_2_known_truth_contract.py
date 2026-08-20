"""Fail-closed contract loader for Product-B v2.2 known-truth validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from .product_b_v2_known_truth_contract import EXPECTED_ALIASES, M_SPECS, PROCESS_UNIVERSE

PURPOSE = "product_b_v2_2_predeclared_frozen_representation_known_truth_validation"
EVALUATION_SEEDS = tuple(range(681, 693))
EXCLUDED_MODEL_ONLY_SEEDS = (*tuple(range(611, 623)), *tuple(range(661, 673)))
FROZEN_METHOD_SOURCE = {
    "run_id": 32356754388,
    "head_sha": "064db306a44ce1104327b73b70e055e56e451018",
    "artifact_id": 9402671599,
    "artifact_name": "product-b-v2-1-frozen-method",
    "artifact_digest": "sha256:e4ec80cd5b6827c47f1d5eab41f29739711d1c85c399296fdaed0ee59c0d8a41",
    "expected_purpose": "product_b_v2_frozen_product_a_method_pretruth",
    "source_contract_sha256": "55136e97bb5230ed13309a75482f63a69901255905ad75d6f8233c8bb92f1815",
    "frozen_candidate": "niche_forward|logit_l2_C1_degree2",
    "candidate_frozen_before_v2_1_evaluation_taxa": True,
    "generating_truth_read": False,
}
BASE_EXECUTION_CONTRACT = {
    "chance_auc": 0.5,
    "minimum_auc_margin": 0.01,
    "auc_sem_multiplier": 1.0,
    "observation_correction_active": False,
    "observation_weight_truncation_quantile": 0.99,
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _taxon_name(spec: dict[str, Any]) -> str:
    return f"{spec['family']}__seed{int(spec['seed'])}"


def load_product_b_v2_2_known_truth_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-B v2.2 purpose changed")
    history = payload.get("successor_history", [])
    expected_history = [
        {
            "version": "v2.0",
            "run_id": 32345246380,
            "failure_stage": "pretruth_freeze",
            "generating_process_truth_opened": False,
            "reason": "requested outer-fold denominator was structurally incomplete",
        },
        {
            "version": "v2.1",
            "run_id": 32356754388,
            "head_sha": "064db306a44ce1104327b73b70e055e56e451018",
            "failure_stage": "process_shard",
            "generating_process_truth_opened": False,
            "reason": "process removal followed by niche-forward reselection made some otherwise valid water-knockout folds procedure-unevaluable",
        },
    ]
    if history != expected_history:
        raise ValueError("Product-B v2.2 predecessor boundary changed")
    if payload.get("frozen_product_a_method_source") != FROZEN_METHOD_SOURCE:
        raise ValueError("Product-B v2.2 frozen method source changed")
    excluded = tuple(int(x) for x in payload.get("previous_model_only_evaluation_seeds_excluded", ()))
    if excluded != EXCLUDED_MODEL_ONLY_SEEDS:
        raise ValueError("Product-B v2.2 excluded model-only seeds changed")
    if int(payload.get("opened_generating_truth_seed_maximum", -1)) != 523:
        raise ValueError("opened generating-truth maximum must remain 523")
    for key in ("real_empirical_data_read", "empirical_sealed_outcomes_read", "product_b_formally_unblocked"):
        if payload.get(key) is not False:
            raise ValueError(f"Product-B v2.2 requires {key}=false")

    expected_sim = {
        "n_cells": 1500,
        "n_occurrences": 150,
        "n_target_group": 600,
        "inner_folds": 2,
        "outer_folds": 2,
        "n_spatial_blocks": 8,
        "max_predictors": 4,
        "minimum_predictor_coverage": 0.95,
        "M_specs": list(M_SPECS),
    }
    if payload.get("simulation_contract") != expected_sim:
        raise ValueError("Product-B v2.2 simulation contract changed")
    if payload.get("base_procedure_execution_contract") != BASE_EXECUTION_CONTRACT:
        raise ValueError("Product-B v2.2 base procedure execution contract changed")
    expected_partition = {
        "process_partition_seed_base": 990000,
        "process_partition_seed_formula": "990000 + taxon_index*10 + M_index",
        "fixed_n_spatial_blocks": 8,
        "partition_search_or_reselection": False,
        "partition_uses_coordinates_only": True,
        "partition_uses_generating_truth": False,
        "partition_uses_niche_recovery_scores": False,
        "all_requested_outer_folds_must_be_evaluable": True,
    }
    if payload.get("partition_contract") != expected_partition:
        raise ValueError("Product-B v2.2 partition contract changed")

    specs = tuple(payload.get("product_b_evaluation_taxa", ()))
    seeds = tuple(int(x["seed"]) for x in specs)
    if seeds != EVALUATION_SEEDS:
        raise ValueError("Product-B v2.2 evaluation seeds changed")
    if set(seeds) & set(EXCLUDED_MODEL_ONLY_SEEDS) or min(seeds) <= max(EXCLUDED_MODEL_ONLY_SEEDS):
        raise ValueError("Product-B v2.2 evaluation taxa are not fresh")
    for spec in specs:
        if str(spec.get("family")) not in KNOWN_TRUTH_FAMILIES:
            raise ValueError(f"unknown known-truth family: {spec.get('family')!r}")

    aliases = {str(k): str(v) for k, v in payload.get("process_predictor_aliases", {}).items()}
    if aliases != EXPECTED_ALIASES:
        raise ValueError("Product-B v2.2 process aliases changed")
    if tuple(payload.get("ecological_process_universe", ())) != PROCESS_UNIVERSE:
        raise ValueError("Product-B v2.2 process universe changed")

    semantics = payload.get("process_ablation_semantics", {})
    expected_semantics = {
        "base_product_a_procedure_is_frozen": True,
        "base_selected_predictors_are_frozen_within_outer_fold": True,
        "remove_only_selected_predictors_in_target_process": True,
        "predictor_reselection_after_process_drop": False,
        "refit_statistical_response_after_drop": True,
        "same_outer_fold_partition_for_base_and_ablation": True,
        "constant_null_representation_allowed_if_no_predictor_remains": True,
        "constant_null_ecological_representation_allowed_if_only_observation_predictors_remain": True,
        "compensated_reoptimization_is_not_used_for_core_process_support": True,
        "interpretation": "process contribution to the already recovered niche representation, distinct from Product-A replaceability/necessity",
    }
    if semantics != expected_semantics:
        raise ValueError("Product-B v2.2 ablation semantics changed")

    rule = payload.get("process_constraint_rule", {})
    if abs(float(rule.get("min_pareto_worsening_fraction", -1)) - 2 / 3) > 1e-12:
        raise ValueError("Product-B process worsening threshold changed")
    if abs(float(rule.get("max_pareto_improvement_fraction", -1)) - 1 / 3) > 1e-12:
        raise ValueError("Product-B process improvement threshold changed")
    if rule.get("weighted_super_score") is not False:
        raise ValueError("weighted Product-B score remains forbidden")
    for key in ("presence_rank_is_guardrail_not_process_target", "requires_complete_M_x_fold_evidence"):
        if rule.get(key) is not True:
            raise ValueError(f"Product-B v2.2 process rule requires {key}=true")

    universality = payload.get("universality_rule", {})
    if tuple(int(x) for x in universality.get("split_seeds", ())) != (71, 72, 73, 74, 75):
        raise ValueError("universality split seeds changed")
    if abs(float(universality.get("validation_fraction", -1)) - 1 / 3) > 1e-12:
        raise ValueError("universality validation fraction changed")
    if abs(float(universality.get("min_taxon_support_fraction", -1)) - 2 / 3) > 1e-12:
        raise ValueError("universality support threshold changed")
    if abs(float(universality.get("stable_core_min_validation_confirmation_fraction", -1)) - 0.8) > 1e-12:
        raise ValueError("universality stable-core threshold changed")

    if payload.get("known_truth_expectation") != {
        "universal_processes": ["temperature", "water"],
        "omitted_driver_additional_process": "soil",
        "noncausal_processes": ["seasonality", "noise"],
        "observation_process_is_not_ecological_process": True,
    }:
        raise ValueError("known process truth changed")
    if payload.get("supported_result_requires") != {
        "all_product_b_taxa_complete": True,
        "universal_process_recall": 1.0,
        "false_stable_universal_processes": 0,
        "mean_taxon_process_recall_minimum": 0.9,
        "mean_taxon_process_precision_minimum": 0.8,
        "stable_core_threshold": 0.8,
    }:
        raise ValueError("Product-B v2.2 support gate changed")
    if payload.get("truth_opening_order") != {
        "frozen_product_a_method_preexists_fresh_v2_2_taxa": True,
        "process_losses_frozen_before_generating_truth_audit": True,
        "thresholds_retuned_after_truth": False,
    }:
        raise ValueError("Product-B v2.2 truth-opening order changed")
    if payload.get("claim_boundary") != "development_known_truth_only_no_empirical_product_b_claim":
        raise ValueError("Product-B v2.2 claim boundary changed")

    payload["contract_sha256"] = _sha(source)
    payload["product_b_evaluation_taxon_names"] = [_taxon_name(dict(x)) for x in specs]
    return payload
