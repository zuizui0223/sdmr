"""Fail-closed contract loader for Product-B v3 A-conditioned known-truth validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from .product_b_v2_known_truth_contract import EXPECTED_ALIASES, M_SPECS, PROCESS_UNIVERSE

PURPOSE = "product_b_v3_predeclared_a_conditioned_known_truth_validation"
EVALUATION_SEEDS = tuple(range(701, 713))
EXCLUDED_SEEDS = (*tuple(range(611, 623)), *tuple(range(661, 673)), *tuple(range(681, 693)))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _taxon_name(spec: dict[str, Any]) -> str:
    return f"{spec['family']}__seed{int(spec['seed'])}"


def load_product_b_v3_known_truth_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-B v3 purpose changed")
    history = payload.get("successor_history", [])
    if len(history) != 4:
        raise ValueError("Product-B v3 successor history changed")
    if any(x.get("generating_process_truth_opened") is not False for x in history):
        raise ValueError("a Product-B predecessor unexpectedly opened generating truth")
    diagnosis = payload.get("diagnosis", {})
    if diagnosis.get("candidate_selection_uses_process_ablation_outcomes") is not False:
        raise ValueError("Product-B v3 cannot select Product-A candidate from B ablation outcomes")
    if diagnosis.get("candidate_selection_uses_generating_truth") is not False:
        raise ValueError("Product-B v3 cannot select Product-A candidate from truth")
    if int(payload.get("opened_generating_truth_seed_maximum", -1)) != 523:
        raise ValueError("opened generating-truth maximum must remain 523")
    excluded = tuple(int(x) for x in payload.get("previous_model_only_evaluation_seeds_excluded", ()))
    if excluded != EXCLUDED_SEEDS:
        raise ValueError("Product-B v3 excluded model-only seeds changed")
    for key in ("real_empirical_data_read", "empirical_sealed_outcomes_read", "product_b_formally_unblocked"):
        if payload.get(key) is not False:
            raise ValueError(f"Product-B v3 requires {key}=false")

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
        raise ValueError("Product-B v3 simulation contract changed")
    expected_partition = {
        "partition_seed_base": 1110000,
        "partition_seed_formula": "1110000 + taxon_index*10 + M_index",
        "fixed_n_spatial_blocks": 8,
        "partition_search_or_reselection": False,
        "partition_uses_coordinates_only": True,
        "partition_uses_generating_truth": False,
        "partition_uses_process_ablation_outcomes": False,
    }
    if payload.get("partition_contract") != expected_partition:
        raise ValueError("Product-B v3 partition contract changed")

    specs = tuple(payload.get("product_b_evaluation_taxa", ()))
    seeds = tuple(int(x["seed"]) for x in specs)
    if seeds != EVALUATION_SEEDS:
        raise ValueError("Product-B v3 evaluation seeds changed")
    if set(seeds) & set(EXCLUDED_SEEDS) or min(seeds) <= max(EXCLUDED_SEEDS):
        raise ValueError("Product-B v3 evaluation taxa are not fresh")
    for spec in specs:
        if str(spec.get("family")) not in KNOWN_TRUTH_FAMILIES:
            raise ValueError(f"unknown known-truth family: {spec.get('family')!r}")

    selector = payload.get("product_a_selector", {})
    if selector != {
        "candidate_pool": "four_frozen_strategies_x_two_frozen_model_specs",
        "requires_complete_taxon_M_fold_evidence": True,
        "chance_auc": 0.50,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "selector": "select_generalization_gated_niche_recovery_protocol",
        "representative_frozen_before_any_product_b_process_ablation": True,
        "weighted_super_score": False,
    }:
        raise ValueError("Product-A selector contract changed inside Product-B v3")

    aliases = {str(k): str(v) for k, v in payload.get("process_predictor_aliases", {}).items()}
    if aliases != EXPECTED_ALIASES:
        raise ValueError("Product-B v3 process aliases changed")
    if tuple(payload.get("ecological_process_universe", ())) != PROCESS_UNIVERSE:
        raise ValueError("Product-B v3 process universe changed")
    if payload.get("process_ablation_semantics") != {
        "use_product_a_base_fold_selected_predictors_already_frozen_by_product_a_benchmark": True,
        "predictor_reselection_after_process_drop": False,
        "refit_statistical_response_after_drop": True,
        "same_outer_fold_partition_as_product_a_base_evidence": True,
        "compensated_reoptimization_is_not_used_for_process_support": True,
        "interpretation": "cross-taxon process contribution conditional on the niche representation recovered by the Product-A selector",
    }:
        raise ValueError("Product-B v3 ablation semantics changed")

    rule = payload.get("process_constraint_rule", {})
    if abs(float(rule.get("min_pareto_worsening_fraction", -1)) - 2 / 3) > 1e-12:
        raise ValueError("Product-B v3 process worsening threshold changed")
    if abs(float(rule.get("max_pareto_improvement_fraction", -1)) - 1 / 3) > 1e-12:
        raise ValueError("Product-B v3 process improvement threshold changed")
    if rule.get("weighted_super_score") is not False:
        raise ValueError("weighted Product-B score remains forbidden")
    if rule.get("presence_rank_is_guardrail_not_process_target") is not True or rule.get("requires_complete_M_x_fold_evidence") is not True:
        raise ValueError("Product-B v3 process evidence rule changed")

    universality = payload.get("universality_rule", {})
    if universality != {
        "split_seeds": [71, 72, 73, 74, 75],
        "validation_fraction": 1 / 3,
        "min_taxon_support_fraction": 2 / 3,
        "stable_core_min_validation_confirmation_fraction": 0.8,
    }:
        raise ValueError("Product-B v3 universality rule changed")
    if payload.get("known_truth_expectation") != {
        "universal_processes": ["temperature", "water"],
        "omitted_driver_additional_process": "soil",
        "noncausal_processes": ["seasonality", "noise"],
        "observation_process_is_not_ecological_process": True,
    }:
        raise ValueError("Product-B v3 known process truth changed")
    if payload.get("supported_result_requires") != {
        "product_a_representative_available": True,
        "all_product_b_taxa_complete": True,
        "universal_process_recall": 1.0,
        "false_stable_universal_processes": 0,
        "mean_taxon_process_recall_minimum": 0.9,
        "mean_taxon_process_precision_minimum": 0.8,
        "stable_core_threshold": 0.8,
    }:
        raise ValueError("Product-B v3 support gate changed")
    if payload.get("truth_opening_order") != {
        "product_a_candidate_frozen_before_process_ablation": True,
        "process_losses_frozen_before_generating_truth_audit": True,
        "thresholds_retuned_after_truth": False,
    }:
        raise ValueError("Product-B v3 truth-opening order changed")
    if payload.get("claim_boundary") != "development_known_truth_only_no_empirical_product_b_claim":
        raise ValueError("Product-B v3 claim boundary changed")

    payload["contract_sha256"] = _sha(source)
    payload["product_b_evaluation_taxon_names"] = [_taxon_name(dict(x)) for x in specs]
    return payload
