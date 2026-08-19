"""Fail-closed loader for the Product-A v2.6 empirical confirmation contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_PURPOSE = "product_a_v2_6_predeclared_empirical_confirmation_contract"
EXPECTED_KNOWN_TRUTH_RUN = "32251711573"
EXPECTED_KNOWN_TRUTH_ARTIFACT = "9364873176"
EXPECTED_KNOWN_TRUTH_DIGEST = "sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba"
EXPECTED_SNAPSHOT_DOI = "10.15468/dl.fs3btq"
EXPECTED_CITATION_SHA = "022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050"
EXPECTED_REGISTRY_SHA = "08f9a68c7854f4df40c2ec89bf287556be34b78186d3c53f9b72f11b790df95d"
EXPECTED_DOMAINS = (
    "thermal", "water", "seasonality_phenology", "energy_productivity", "snow", "wind"
)
EXPECTED_SEEDS = (2026081901, 2026081902, 2026081903)
EXPECTED_FRACTIONS = (0.20, 0.30)
EXPECTED_M = (150, 300, 500)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v2_6_empirical_contract(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("purpose") != EXPECTED_PURPOSE:
        raise ValueError("empirical confirmation purpose changed")
    for key in (
        "scientific_promotion_run",
        "product_b_unblocked",
        "known_truth_outcomes_used_to_tune_empirical_thresholds",
        "old_real_model_outputs_reused",
        "old_real_background_outputs_reused",
        "old_real_sealed_outcomes_read",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"empirical confirmation requires {key}=false")
    if payload.get("source_evidence_reuse_only") is not True:
        raise ValueError("only immutable raw source evidence may be reused")

    truth = payload.get("known_truth_source", {})
    if truth.get("decision") != "v2_6_supported":
        raise ValueError("empirical confirmation requires frozen v2.6 support")
    if str(truth.get("run_id")) != EXPECTED_KNOWN_TRUTH_RUN:
        raise ValueError("known-truth run changed")
    if str(truth.get("artifact_id")) != EXPECTED_KNOWN_TRUTH_ARTIFACT:
        raise ValueError("known-truth artifact changed")
    if str(truth.get("artifact_digest")) != EXPECTED_KNOWN_TRUTH_DIGEST:
        raise ValueError("known-truth digest changed")

    source = payload.get("raw_empirical_sources", {})
    if str(source.get("snapshot_doi", "")).lower() != EXPECTED_SNAPSHOT_DOI:
        raise ValueError("GBIF snapshot DOI changed")
    if str(source.get("citation_sha256", "")).lower() != EXPECTED_CITATION_SHA:
        raise ValueError("GBIF citation fingerprint changed")
    if source.get("target_group", {}).get("focal_taxa_excluded_pre_split") is not True:
        raise ValueError("target group must exclude focal taxa before splitting")
    if abs(float(source.get("target_group", {}).get("one_per_grid_cell_degrees", -1)) - 0.05) > 1e-12:
        raise ValueError("target-group thinning changed")

    barrier = payload.get("information_barrier", {})
    for key in (
        "focal_thinning_before_outer_split",
        "outer_sealed_before_M",
        "M_built_from_model_pool_only",
        "target_group_background_excludes_focal_taxa_pre_split",
        "sealed_occurrences_first_opened_for_final_empirical_audit",
        "M_grid_as_sensitivity_not_optimized",
    ):
        if barrier.get(key) is not True:
            raise ValueError(f"information barrier changed: {key}")
    for key in ("sealed_occurrences_used_for_selection", "sealed_occurrences_used_for_M"):
        if barrier.get(key) is not False:
            raise ValueError(f"information barrier requires {key}=false")

    design = payload.get("fixed_design", {})
    if tuple(int(x) for x in design.get("M_km", ())) != EXPECTED_M:
        raise ValueError("M sensitivity grid changed")
    if tuple(int(x) for x in design.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("empirical split seeds changed")
    if tuple(float(x) for x in design.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("sealed fractions changed")
    if int(design.get("n_confirmation_parts", -1)) != len(EXPECTED_SEEDS) * len(EXPECTED_FRACTIONS):
        raise ValueError("confirmation denominator changed")
    if design.get("require_all_12_taxa") is not True:
        raise ValueError("all 12 predeclared taxa must be retained")
    if tuple(design.get("process_domains", ())) != EXPECTED_DOMAINS:
        raise ValueError("empirical process-domain order changed")
    if design.get("process_registry_sha256") != EXPECTED_REGISTRY_SHA:
        raise ValueError("empirical process-registry fingerprint changed")

    repo_root = config_path.parent.parent
    registry_path = repo_root / str(design.get("process_registry_path", ""))
    manifest_path = repo_root / "configs/chelsa_v2_1_plant_candidates.csv"
    if not registry_path.exists() or _sha256(registry_path) != EXPECTED_REGISTRY_SHA:
        raise ValueError("empirical process registry file differs from frozen fingerprint")
    registry = pd.read_csv(registry_path)
    if registry["predictor"].astype(str).duplicated().any():
        raise ValueError("each CHELSA predictor must have exactly one empirical process domain")
    if set(registry["empirical_process_domain"].astype(str)) != set(EXPECTED_DOMAINS):
        raise ValueError("empirical process registry has missing or unknown domains")
    manifest = pd.read_csv(manifest_path)
    active = set(manifest.loc[manifest["availability"].astype(str).eq("current"), "predictor"].astype(str))
    mapped = set(registry["predictor"].astype(str))
    if mapped != active:
        raise ValueError(f"empirical process registry does not cover active CHELSA exactly: missing={sorted(active-mapped)}, extra={sorted(mapped-active)}")

    target = payload.get("empirical_target", {})
    if target.get("claim") != "realized_environmental_niche_recovery_and_stability":
        raise ValueError("empirical claim target changed")
    if target.get("fundamental_niche_truth_claim_allowed") is not False:
        raise ValueError("presence-only empirical confirmation cannot claim fundamental-niche truth")
    if target.get("ordinary_prediction_metrics_are_guardrails_not_tuning_target") is not True:
        raise ValueError("prediction scores cannot become the empirical tuning target")

    decision = payload.get("decision_rule", {})
    if decision.get("all_6_parts_required") is not True:
        raise ValueError("all six empirical confirmation parts remain required")
    if decision.get("all_12_taxa_required_in_every_part") is not True:
        raise ValueError("every empirical part must retain all 12 taxa")
    if decision.get("all_3_M_specs_required_in_every_part") is not True:
        raise ValueError("every empirical part must retain all three M specs")
    if float(decision.get("prediction_guardrail", {}).get("mean_presence_rank_deficit_vs_auc_comparator_min", 99)) != -0.01:
        raise ValueError("prediction non-inferiority guardrail changed")
    eco = decision.get("ecological_noninferiority", {})
    if int(eco.get("minimum_parts", -1)) != 4 or int(eco.get("strict_improvement_minimum_parts", -1)) != 3:
        raise ValueError("ecological support denominator changed")
    proc = decision.get("process_reproducibility", {})
    if abs(float(proc.get("modal_status_fraction_min", -1)) - 2.0 / 3.0) > 1e-12:
        raise ValueError("process reproducibility threshold changed")
    if decision.get("scientific_promotion_allowed_by_this_decision") is not False:
        raise ValueError("empirical confirmation cannot directly promote Product A")
    if decision.get("product_b_remains_blocked_until_separate_promotion_decision") is not True:
        raise ValueError("Product B cannot be unblocked by empirical confirmation alone")
    return payload
