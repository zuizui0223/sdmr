"""Fail-closed loader for the Product-A v2.6 empirical confirmation contract."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXPECTED_PURPOSE = "product_a_v2_6_predeclared_empirical_confirmation_contract"
EXPECTED_KNOWN_TRUTH_RUN = "32251711573"
EXPECTED_KNOWN_TRUTH_ARTIFACT = "9364873176"
EXPECTED_KNOWN_TRUTH_DIGEST = "sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba"
EXPECTED_SNAPSHOT_DOI = "10.15468/dl.fs3btq"
EXPECTED_CITATION_SHA = "022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050"
EXPECTED_SEEDS = (2026081901, 2026081902, 2026081903)
EXPECTED_FRACTIONS = (0.20, 0.30)
EXPECTED_M = (150, 300, 500)


def load_v2_6_empirical_contract(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
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

    target = payload.get("empirical_target", {})
    if target.get("claim") != "realized_environmental_niche_recovery_and_stability":
        raise ValueError("empirical claim target changed")
    if target.get("fundamental_niche_truth_claim_allowed") is not False:
        raise ValueError("presence-only empirical confirmation cannot claim fundamental-niche truth")
    if target.get("ordinary_prediction_metrics_are_guardrails_not_tuning_target") is not True:
        raise ValueError("prediction scores cannot become the empirical tuning target")
    return payload
