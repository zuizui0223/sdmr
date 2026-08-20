"""Pre-outcome contract for Product-B v2 fresh known-truth validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES

PURPOSE = "product_b_v2_predeclared_fresh_known_truth_validation"
METHOD_SEEDS = tuple(range(601, 607))
EVALUATION_SEEDS = tuple(range(611, 623))
PROCESS_UNIVERSE = ("temperature", "water", "soil", "seasonality", "noise")
M_SPECS = ("m_core", "m_mid", "m_wide")
EXPECTED_ALIASES = {
    "temperature": "temperature",
    "temp_proxy": "temperature",
    "sparse_temp_proxy": "temperature",
    "water": "water",
    "soil": "soil",
    "seasonality": "seasonality",
    "noise": "noise",
    "sparse_noise": "noise",
    "recording_bias": "observation_process",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _taxon_name(spec: dict[str, Any]) -> str:
    return f"{spec['family']}__seed{int(spec['seed'])}"


def load_product_b_v2_known_truth_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-B v2 known-truth purpose changed")
    for key in (
        "real_empirical_data_read",
        "empirical_sealed_outcomes_read",
        "product_b_formally_unblocked",
        "previously_opened_known_truth_used",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"Product-B v2 known-truth requires {key}=false")
    if int(payload.get("opened_known_truth_seed_maximum", -1)) != 523:
        raise ValueError("opened known-truth maximum must remain 523")

    sim = payload.get("simulation_contract", {})
    expected_sim = {
        "n_cells": 1500,
        "n_occurrences": 150,
        "n_target_group": 600,
        "inner_folds": 2,
        "outer_folds": 2,
        "max_predictors": 4,
        "minimum_predictor_coverage": 0.95,
        "M_specs": list(M_SPECS),
    }
    if sim != expected_sim:
        raise ValueError("Product-B v2 simulation contract changed")
    aliases = {str(k): str(v) for k, v in payload.get("process_predictor_aliases", {}).items()}
    if aliases != EXPECTED_ALIASES:
        raise ValueError("Product-B v2 process aliases changed")
    if tuple(payload.get("ecological_process_universe", ())) != PROCESS_UNIVERSE:
        raise ValueError("Product-B v2 process universe changed")

    method = tuple(payload.get("method_freeze_taxa", ()))
    evaluation = tuple(payload.get("product_b_evaluation_taxa", ()))
    if tuple(int(x["seed"]) for x in method) != METHOD_SEEDS:
        raise ValueError("method-freeze seeds changed")
    if tuple(int(x["seed"]) for x in evaluation) != EVALUATION_SEEDS:
        raise ValueError("Product-B evaluation seeds changed")
    all_specs = (*method, *evaluation)
    if len({int(x["seed"]) for x in all_specs}) != len(all_specs):
        raise ValueError("known-truth seeds are not unique")
    if min(int(x["seed"]) for x in all_specs) <= 523:
        raise ValueError("fresh Product-B known-truth seeds must exceed 523")
    for spec in all_specs:
        if str(spec.get("family")) not in KNOWN_TRUTH_FAMILIES:
            raise ValueError(f"unknown known-truth family: {spec.get('family')!r}")

    freeze = payload.get("method_freeze", {})
    if freeze.get("candidate_selection_target") != "product_a_generalization_gated_niche_recovery":
        raise ValueError("method-freeze target changed")
    if freeze.get("prediction_adequacy") != {
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
    }:
        raise ValueError("method-freeze prediction gate changed")
    if freeze.get("generating_truth_used") is not False:
        raise ValueError("method freeze cannot use generating truth")
    if freeze.get("product_b_evaluation_taxa_simulated_before_freeze") is not False:
        raise ValueError("Product-B evaluation taxa must remain unopened before method freeze")

    process = payload.get("process_constraint_rule", {})
    if abs(float(process.get("min_pareto_worsening_fraction", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("process worsening threshold changed")
    if abs(float(process.get("max_pareto_improvement_fraction", -1)) - 1.0 / 3.0) > 1e-12:
        raise ValueError("process improvement threshold changed")
    for key in ("presence_rank_is_guardrail_not_process_target", "requires_complete_M_x_fold_evidence"):
        if process.get(key) is not True:
            raise ValueError(f"Product-B process rule requires {key}=true")
    if process.get("weighted_super_score") is not False:
        raise ValueError("weighted Product-B super-score is forbidden")

    universality = payload.get("universality_rule", {})
    if tuple(int(x) for x in universality.get("split_seeds", ())) != (71, 72, 73, 74, 75):
        raise ValueError("universality split seeds changed")
    if abs(float(universality.get("validation_fraction", -1)) - 1.0 / 3.0) > 1e-12:
        raise ValueError("universality validation fraction changed")
    if abs(float(universality.get("min_taxon_support_fraction", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("universality support threshold changed")
    if abs(float(universality.get("stable_core_min_validation_confirmation_fraction", -1)) - 0.8) > 1e-12:
        raise ValueError("stable-core threshold changed")

    truth = payload.get("known_truth_expectation", {})
    if tuple(truth.get("universal_processes", ())) != ("temperature", "water"):
        raise ValueError("known universal-process truth changed")
    if truth.get("omitted_driver_additional_process") != "soil":
        raise ValueError("omitted-driver soil truth changed")
    if tuple(truth.get("noncausal_processes", ())) != ("seasonality", "noise"):
        raise ValueError("noncausal process truth changed")
    if truth.get("observation_process_is_not_ecological_process") is not True:
        raise ValueError("observation-process boundary changed")

    required = payload.get("supported_result_requires", {})
    expected_required = {
        "all_method_freeze_taxa_complete": True,
        "all_product_b_taxa_complete": True,
        "universal_process_recall": 1.0,
        "false_stable_universal_processes": 0,
        "mean_taxon_process_recall_minimum": 0.9,
        "mean_taxon_process_precision_minimum": 0.8,
        "stable_core_threshold": 0.8,
    }
    if required != expected_required:
        raise ValueError("Product-B v2 support gate changed")
    order = payload.get("truth_opening_order", {})
    for key in (
        "method_frozen_before_product_b_taxa_simulated",
        "process_losses_frozen_before_generating_truth_audit",
    ):
        if order.get(key) is not True:
            raise ValueError(f"truth-opening order requires {key}=true")
    if order.get("thresholds_retuned_after_truth") is not False:
        raise ValueError("post-truth threshold tuning is forbidden")
    if payload.get("claim_boundary") != "development_known_truth_only_no_empirical_product_b_claim":
        raise ValueError("Product-B v2 claim boundary changed")

    payload["contract_sha256"] = _sha256(source)
    payload["method_freeze_taxon_names"] = [_taxon_name(dict(x)) for x in method]
    payload["product_b_evaluation_taxon_names"] = [_taxon_name(dict(x)) for x in evaluation]
    return payload
