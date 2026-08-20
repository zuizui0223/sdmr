"""Contract loader for Product-B v2.1 fresh known-truth validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from .product_b_v2_known_truth_contract import EXPECTED_ALIASES, M_SPECS, PROCESS_UNIVERSE

PURPOSE = "product_b_v2_1_predeclared_fresh_known_truth_validation"
METHOD_SEEDS = tuple(range(651, 657))
EVALUATION_SEEDS = tuple(range(661, 673))
EXCLUDED_V20_EVALUATION_SEEDS = tuple(range(611, 623))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _taxon_name(spec: dict[str, Any]) -> str:
    return f"{spec['family']}__seed{int(spec['seed'])}"


def load_product_b_v2_1_known_truth_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-B v2.1 purpose changed")
    predecessor = payload.get("successor_to_failed_pretruth_run", {})
    if predecessor != {
        "run_id": 32345246380,
        "head_sha": "5be2b16d98404846bff01c79aad101ea45de9c3b",
        "failure_stage": "pretruth_freeze",
        "generating_process_truth_opened": False,
        "failure_reason": "one or more requested outer folds were structurally unevaluable because a held-out spatial fold lacked sufficient matched background",
    }:
        raise ValueError("Product-B v2.1 predecessor boundary changed")
    if tuple(int(x) for x in payload.get("previous_model_only_evaluation_seeds_excluded", ())) != EXCLUDED_V20_EVALUATION_SEEDS:
        raise ValueError("Product-B v2.0 model-only evaluation seeds must remain excluded")
    if int(payload.get("opened_generating_truth_seed_maximum", -1)) != 523:
        raise ValueError("opened generating-truth maximum must remain 523")
    for key in ("real_empirical_data_read", "empirical_sealed_outcomes_read", "product_b_formally_unblocked"):
        if payload.get(key) is not False:
            raise ValueError(f"Product-B v2.1 requires {key}=false")

    sim = payload.get("simulation_contract", {})
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
    if sim != expected_sim:
        raise ValueError("Product-B v2.1 simulation contract changed")
    partition = payload.get("partition_contract", {})
    expected_partition = {
        "method_partition_seed_formula": "960000 + taxon_index*10 + M_index",
        "process_partition_seed_formula": "970000 + taxon_index*10 + M_index",
        "fixed_n_spatial_blocks": 8,
        "partition_search_or_reselection": False,
        "partition_uses_coordinates_only": True,
        "partition_uses_generating_truth": False,
        "partition_uses_niche_recovery_scores": False,
        "all_requested_outer_folds_must_be_evaluable": True,
    }
    if partition != expected_partition:
        raise ValueError("Product-B v2.1 partition contract changed")
    if {str(k): str(v) for k, v in payload.get("process_predictor_aliases", {}).items()} != EXPECTED_ALIASES:
        raise ValueError("Product-B v2.1 process aliases changed")
    if tuple(payload.get("ecological_process_universe", ())) != PROCESS_UNIVERSE:
        raise ValueError("Product-B v2.1 process universe changed")

    method = tuple(payload.get("method_freeze_taxa", ()))
    evaluation = tuple(payload.get("product_b_evaluation_taxa", ()))
    if tuple(int(x["seed"]) for x in method) != METHOD_SEEDS:
        raise ValueError("Product-B v2.1 method seeds changed")
    if tuple(int(x["seed"]) for x in evaluation) != EVALUATION_SEEDS:
        raise ValueError("Product-B v2.1 evaluation seeds changed")
    all_specs = (*method, *evaluation)
    seeds = [int(x["seed"]) for x in all_specs]
    if len(set(seeds)) != len(seeds) or min(seeds) <= max(EXCLUDED_V20_EVALUATION_SEEDS):
        raise ValueError("Product-B v2.1 seeds are not fresh and unique")
    for spec in all_specs:
        if str(spec.get("family")) not in KNOWN_TRUTH_FAMILIES:
            raise ValueError(f"unknown known-truth family: {spec.get('family')!r}")

    freeze = payload.get("method_freeze", {})
    if freeze != {
        "candidate_selection_target": "product_a_generalization_gated_niche_recovery",
        "prediction_adequacy": {"chance_auc": 0.5, "minimum_auc_margin": 0.01, "auc_sem_multiplier": 1.0},
        "generating_truth_used": False,
        "product_b_evaluation_taxa_simulated_before_freeze": False,
    }:
        raise ValueError("Product-B v2.1 method-freeze contract changed")
    rule = payload.get("process_constraint_rule", {})
    if abs(float(rule.get("min_pareto_worsening_fraction", -1)) - 2/3) > 1e-12:
        raise ValueError("Product-B process worsening threshold changed")
    if abs(float(rule.get("max_pareto_improvement_fraction", -1)) - 1/3) > 1e-12:
        raise ValueError("Product-B process improvement threshold changed")
    if rule.get("weighted_super_score") is not False:
        raise ValueError("weighted Product-B score remains forbidden")
    for key in ("presence_rank_is_guardrail_not_process_target", "requires_complete_M_x_fold_evidence"):
        if rule.get(key) is not True:
            raise ValueError(f"Product-B process rule requires {key}=true")
    universality = payload.get("universality_rule", {})
    if tuple(int(x) for x in universality.get("split_seeds", ())) != (71,72,73,74,75):
        raise ValueError("universality split seeds changed")
    if abs(float(universality.get("validation_fraction", -1)) - 1/3) > 1e-12:
        raise ValueError("universality validation fraction changed")
    if abs(float(universality.get("min_taxon_support_fraction", -1)) - 2/3) > 1e-12:
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
        "all_method_freeze_taxa_complete": True,
        "all_product_b_taxa_complete": True,
        "universal_process_recall": 1.0,
        "false_stable_universal_processes": 0,
        "mean_taxon_process_recall_minimum": 0.9,
        "mean_taxon_process_precision_minimum": 0.8,
        "stable_core_threshold": 0.8,
    }:
        raise ValueError("Product-B v2.1 support gate changed")
    order = payload.get("truth_opening_order", {})
    if order != {
        "method_frozen_before_product_b_taxa_simulated": True,
        "process_losses_frozen_before_generating_truth_audit": True,
        "thresholds_retuned_after_truth": False,
    }:
        raise ValueError("truth-opening order changed")
    if payload.get("claim_boundary") != "development_known_truth_only_no_empirical_product_b_claim":
        raise ValueError("claim boundary changed")
    payload["contract_sha256"] = _sha(source)
    payload["method_freeze_taxon_names"] = [_taxon_name(dict(x)) for x in method]
    payload["product_b_evaluation_taxon_names"] = [_taxon_name(dict(x)) for x in evaluation]
    return payload
