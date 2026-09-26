"""Fail-closed contracts for the fresh empirical SDMR programme."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence

from sdmr.process_id.taxonomy import DEFAULT_PLANT_PROCESSES


EMPIRICAL_GATES = ("EMP-A", "EMP-B", "EMP-C", "EMP-D", "EMP-E", "EMP-F")
PRIMARY_RECONSTRUCTION_METRIC = "balanced_presence_background_log_score"
OUTER_SPLIT_RULE = "coordinate_only_before_environmental_feature_access"
REQUIRED_COMPARATORS = (
    "auc_oriented_flat_selector",
    "correlation_vif_flat_filter",
    "matched_learner_flat_predictive_selector",
    "sdmr_process_first",
)
PROGRAM = "sdmr-fresh-empirical-prefreeze-v1"
KNOWN_TRUTH_PROGRAM = "sdmr-v6-prospective-known-truth-v2"
PLANNING_STATUS = "planning_frozen_no_outcomes"
FINAL_STATUS = "frozen_ready_for_fresh_execution"


class FreshContractError(ValueError):
    """Raised when a fresh empirical contract violates a fail-closed invariant."""


def _mapping(value, *, name: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise FreshContractError(f"{name} must be an object")
    return value


def _explicit_bool(value, *, name: str) -> bool:
    if type(value) is not bool:
        raise FreshContractError(f"{name} must be an explicit boolean")
    return value


def _nonempty_text(value, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FreshContractError(f"{name} must be non-empty text")
    return value.strip()


def _sha256_receipt(value, *, name: str) -> str:
    text = _nonempty_text(value, name=name)
    if not text.startswith("sha256:") or len(text) != 71:
        raise FreshContractError(f"{name} must be a sha256: receipt")
    payload = text.removeprefix("sha256:")
    if any(ch not in "0123456789abcdef" for ch in payload.lower()):
        raise FreshContractError(f"{name} must contain a hexadecimal SHA-256 digest")
    return text


def _probability(value, *, name: str) -> float:
    if isinstance(value, bool):
        raise FreshContractError(f"{name} must be numeric")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise FreshContractError(f"{name} must be numeric") from exc
    if not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise FreshContractError(f"{name} must be in [0, 1]")
    return x


def _finite_number(value, *, name: str) -> float:
    if isinstance(value, bool):
        raise FreshContractError(f"{name} must be numeric")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise FreshContractError(f"{name} must be numeric") from exc
    if not math.isfinite(x):
        raise FreshContractError(f"{name} must be finite")
    return x


def contract_sha256(contract: Mapping) -> str:
    """Return a canonical SHA-256 receipt for an in-memory contract."""
    payload = json.dumps(
        contract,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_prefreeze_contract(contract: Mapping) -> None:
    """Validate invariants that must hold before any fresh empirical outcome access.

    Numerical EMP-A through EMP-D thresholds and the exact taxon denominator may
    remain intentionally unset at the pre-freeze stage.  Everything that protects
    the historical boundary, known-truth prerequisite, sealed answer-check, and
    strict conjunction is already enforced here.
    """
    c = _mapping(contract, name="contract")

    if c.get("program") != PROGRAM:
        raise FreshContractError(f"program must be {PROGRAM!r}")
    if c.get("status") not in {"prefreeze_scaffold_no_outcomes", PLANNING_STATUS, FINAL_STATUS}:
        raise FreshContractError("unexpected fresh empirical contract status")
    if c.get("product_a_boundary") != "closed_not_reopened":
        raise FreshContractError("Product-A boundary must remain closed_not_reopened")
    if _explicit_bool(c.get("fresh_outcomes_opened"), name="fresh_outcomes_opened"):
        raise FreshContractError("fresh empirical outcomes must remain unopened")

    kt = _mapping(c.get("known_truth_prerequisite"), name="known_truth_prerequisite")
    if kt.get("program") != KNOWN_TRUTH_PROGRAM:
        raise FreshContractError("wrong prospective known-truth prerequisite")
    if _explicit_bool(kt.get("terminal_passed"), name="known_truth_prerequisite.terminal_passed") is not True:
        raise FreshContractError("prospective known-truth prerequisite did not pass")
    if not isinstance(kt.get("workflow_run"), int) or kt["workflow_run"] <= 0:
        raise FreshContractError("known-truth workflow_run must be a positive integer")
    if not isinstance(kt.get("artifact_id"), int) or kt["artifact_id"] <= 0:
        raise FreshContractError("known-truth artifact_id must be a positive integer")
    _sha256_receipt(
        kt.get("artifact_digest"),
        name="known_truth_prerequisite.artifact_digest",
    )

    scope = _mapping(c.get("scientific_scope"), name="scientific_scope")
    if scope.get("taxon_group") != "vascular_plants":
        raise FreshContractError("first fresh empirical cohort must be vascular_plants")
    if scope.get("response") != "occurrence_only":
        raise FreshContractError("fresh empirical response must remain occurrence_only")

    cohort = _mapping(c.get("cohort"), name="cohort")
    if list(cohort.get("planning_range", [])) != [30, 50]:
        raise FreshContractError("cohort planning_range must remain [30, 50]")
    if _explicit_bool(
        cohort.get("replacement_after_outcome_access"),
        name="cohort.replacement_after_outcome_access",
    ):
        raise FreshContractError("taxon replacement after outcome access is forbidden")
    if _explicit_bool(
        cohort.get("historical_product_a_taxa_excluded"),
        name="cohort.historical_product_a_taxa_excluded",
    ) is not True:
        raise FreshContractError("historical Product-A taxa must be excluded")

    exact_denominator = cohort.get("exact_denominator")
    if exact_denominator is not None:
        if isinstance(exact_denominator, bool) or not isinstance(exact_denominator, int):
            raise FreshContractError("cohort.exact_denominator must be an integer or null")
        if not 30 <= exact_denominator <= 50:
            raise FreshContractError("cohort.exact_denominator must stay inside [30, 50]")

    identities_frozen = _explicit_bool(
        cohort.get("taxon_identities_frozen"),
        name="cohort.taxon_identities_frozen",
    )
    identity_hash = cohort.get("taxon_identity_manifest_sha256")
    if identities_frozen:
        _sha256_receipt(identity_hash, name="cohort.taxon_identity_manifest_sha256")
    elif identity_hash is not None:
        raise FreshContractError(
            "taxon identity manifest hash cannot be populated before identities are frozen"
        )

    source_manifest_frozen = _explicit_bool(
        cohort.get("source_manifest_frozen"),
        name="cohort.source_manifest_frozen",
    )
    source_hash = cohort.get("source_manifest_sha256")
    if source_manifest_frozen:
        _sha256_receipt(source_hash, name="cohort.source_manifest_sha256")
    elif source_hash is not None:
        raise FreshContractError(
            "source manifest hash cannot be populated before the manifest is frozen"
        )

    data = _mapping(c.get("data_boundary"), name="data_boundary")
    if data.get("outer_split_rule") != OUTER_SPLIT_RULE:
        raise FreshContractError("outer split must be coordinate-only before feature access")
    if _explicit_bool(
        data.get("answer_check_sealed"),
        name="data_boundary.answer_check_sealed",
    ) is not True:
        raise FreshContractError("answer-check must remain sealed")

    registry = _mapping(c.get("process_registry"), name="process_registry")
    if tuple(registry.get("processes", ())) != tuple(DEFAULT_PLANT_PROCESSES):
        raise FreshContractError("fresh empirical process taxonomy drifted from the frozen plant taxonomy")
    _explicit_bool(registry.get("frozen"), name="process_registry.frozen")

    metric = _mapping(c.get("primary_metric"), name="primary_metric")
    if metric.get("name") != PRIMARY_RECONSTRUCTION_METRIC:
        raise FreshContractError("primary ecological reconstruction metric drifted")
    if _explicit_bool(metric.get("frozen"), name="primary_metric.frozen") is not True:
        raise FreshContractError("primary ecological reconstruction metric must already be frozen")

    comparators = _mapping(c.get("comparators"), name="comparators")
    if tuple(comparators.get("required", ())) != REQUIRED_COMPARATORS:
        raise FreshContractError("required comparator set drifted")
    primary_comparator = comparators.get("primary")
    if primary_comparator is not None and primary_comparator not in REQUIRED_COMPARATORS[:-1]:
        raise FreshContractError("primary comparator must be one of the declared flat baselines")
    _explicit_bool(comparators.get("frozen"), name="comparators.frozen")

    learners = _mapping(c.get("learner_design_panel"), name="learner_design_panel")
    if learners.get("disagreement_policy") != "unresolved_not_averaged":
        raise FreshContractError("learner disagreement must remain unresolved_not_averaged")
    routes = learners.get("routes")
    if not isinstance(routes, Sequence) or isinstance(routes, (str, bytes)):
        raise FreshContractError("learner_design_panel.routes must be a sequence")
    _explicit_bool(learners.get("frozen"), name="learner_design_panel.frozen")

    promotion = _mapping(c.get("promotion"), name="promotion")
    if tuple(promotion.get("strict_conjunction", ())) != EMPIRICAL_GATES:
        raise FreshContractError("promotion must use the exact EMP-A through EMP-F conjunction")
    gate_vector = _mapping(promotion.get("gate_vector"), name="promotion.gate_vector")
    if tuple(gate_vector.keys()) != EMPIRICAL_GATES:
        raise FreshContractError("promotion.gate_vector must contain EMP-A through EMP-F in order")
    emp_e = _mapping(gate_vector["EMP-E"], name="promotion.gate_vector.EMP-E")
    if emp_e.get("maximum_violation_rate") != 0:
        raise FreshContractError("EMP-E must forbid abstention-integrity violations")
    emp_f = _mapping(gate_vector["EMP-F"], name="promotion.gate_vector.EMP-F")
    if emp_f.get("required") is not True:
        raise FreshContractError("EMP-F denominator integrity must be required")
    _explicit_bool(promotion.get("frozen"), name="promotion.frozen")



def validate_planning_freeze_contract(contract: Mapping) -> None:
    """Require the pre-outcome planning decisions to be frozen.

    This intermediate gate deliberately does not require taxon identities,
    source manifests, provider/QC details, or the process-registry manifest.
    It freezes only choices that can be justified without opening the fresh
    empirical answer-check.
    """
    validate_prefreeze_contract(contract)
    c = _mapping(contract, name="contract")
    if c.get("status") not in {PLANNING_STATUS, FINAL_STATUS}:
        raise FreshContractError(
            f"planning freeze status must be {PLANNING_STATUS!r} or {FINAL_STATUS!r}"
        )

    cohort = _mapping(c["cohort"], name="cohort")
    exact_denominator = cohort.get("exact_denominator")
    if isinstance(exact_denominator, bool) or not isinstance(exact_denominator, int):
        raise FreshContractError("planning freeze requires an exact taxon denominator")
    if not 30 <= exact_denominator <= 50:
        raise FreshContractError("planning freeze denominator must stay inside [30, 50]")

    metric = _mapping(c["primary_metric"], name="primary_metric")
    _nonempty_text(
        metric.get("prediction_guardrail"),
        name="primary_metric.prediction_guardrail",
    )
    if _explicit_bool(
        metric.get("prediction_guardrail_frozen"),
        name="primary_metric.prediction_guardrail_frozen",
    ) is not True:
        raise FreshContractError("planning freeze requires a frozen prediction guardrail")

    comparators = _mapping(c["comparators"], name="comparators")
    if _explicit_bool(comparators.get("frozen"), name="comparators.frozen") is not True:
        raise FreshContractError("planning freeze requires frozen comparators")
    if comparators.get("primary") not in REQUIRED_COMPARATORS[:-1]:
        raise FreshContractError("planning freeze requires one flat primary comparator")

    learners = _mapping(c["learner_design_panel"], name="learner_design_panel")
    if _explicit_bool(learners.get("frozen"), name="learner_design_panel.frozen") is not True:
        raise FreshContractError("planning freeze requires a frozen learner/design panel")
    routes = tuple(learners.get("routes", ()))
    if len(routes) < 2 or any(
        not isinstance(route, str) or not route.strip() for route in routes
    ):
        raise FreshContractError(
            "planning freeze requires at least two named learner/design routes"
        )

    promotion = _mapping(c["promotion"], name="promotion")
    if _explicit_bool(promotion.get("frozen"), name="promotion.frozen") is not True:
        raise FreshContractError("planning freeze requires frozen EMP thresholds")
    gates = _mapping(promotion["gate_vector"], name="promotion.gate_vector")
    _finite_number(
        _mapping(gates["EMP-A"], name="EMP-A").get("minimum_mean_gain"),
        name="EMP-A.minimum_mean_gain",
    )
    _finite_number(
        _mapping(gates["EMP-B"], name="EMP-B").get("minimum_lower_bound"),
        name="EMP-B.minimum_lower_bound",
    )
    emp_c = _mapping(gates["EMP-C"], name="EMP-C")
    margin = _finite_number(
        emp_c.get("noninferiority_margin"),
        name="EMP-C.noninferiority_margin",
    )
    if margin < 0:
        raise FreshContractError("EMP-C noninferiority margin must be >= 0")
    _probability(
        _mapping(gates["EMP-D"], name="EMP-D").get("minimum_stable_fraction"),
        name="EMP-D.minimum_stable_fraction",
    )
    if _mapping(gates["EMP-E"], name="EMP-E").get("maximum_violation_rate") != 0:
        raise FreshContractError("EMP-E maximum_violation_rate must remain zero")
    if _mapping(gates["EMP-F"], name="EMP-F").get("required") is not True:
        raise FreshContractError("EMP-F must remain required")


def validate_final_freeze_contract(contract: Mapping) -> None:
    """Require a complete, execution-ready empirical contract with no outcome access."""
    validate_prefreeze_contract(contract)
    c = _mapping(contract, name="contract")
    if c.get("status") != FINAL_STATUS:
        raise FreshContractError(f"final contract status must be {FINAL_STATUS!r}")

    cohort = _mapping(c["cohort"], name="cohort")
    exact_denominator = cohort.get("exact_denominator")
    if isinstance(exact_denominator, bool) or not isinstance(exact_denominator, int):
        raise FreshContractError("final freeze requires an exact taxon denominator")
    if _explicit_bool(cohort.get("eligibility_rules_frozen"), name="cohort.eligibility_rules_frozen") is not True:
        raise FreshContractError("final freeze requires frozen cohort eligibility rules")
    if _explicit_bool(cohort.get("taxon_identities_frozen"), name="cohort.taxon_identities_frozen") is not True:
        raise FreshContractError("final freeze requires frozen taxon identities")
    _sha256_receipt(
        cohort.get("taxon_identity_manifest_sha256"),
        name="cohort.taxon_identity_manifest_sha256",
    )
    if _explicit_bool(cohort.get("source_manifest_frozen"), name="cohort.source_manifest_frozen") is not True:
        raise FreshContractError("final freeze requires a frozen source manifest")
    _sha256_receipt(cohort.get("source_manifest_sha256"), name="cohort.source_manifest_sha256")

    data = _mapping(c["data_boundary"], name="data_boundary")
    for key in (
        "provider",
        "temporal_window",
        "occurrence_qc_rule",
        "accessible_area_rule",
    ):
        _nonempty_text(data.get(key), name=f"data_boundary.{key}")

    registry = _mapping(c["process_registry"], name="process_registry")
    if _explicit_bool(registry.get("frozen"), name="process_registry.frozen") is not True:
        raise FreshContractError("final freeze requires a frozen process registry")
    _sha256_receipt(
        registry.get("registry_manifest_sha256"),
        name="process_registry.registry_manifest_sha256",
    )

    metric = _mapping(c["primary_metric"], name="primary_metric")
    _nonempty_text(metric.get("prediction_guardrail"), name="primary_metric.prediction_guardrail")
    if _explicit_bool(metric.get("prediction_guardrail_frozen"), name="primary_metric.prediction_guardrail_frozen") is not True:
        raise FreshContractError("prediction guardrail must be frozen before outcome access")

    comparators = _mapping(c["comparators"], name="comparators")
    if _explicit_bool(comparators.get("frozen"), name="comparators.frozen") is not True:
        raise FreshContractError("final freeze requires frozen comparators")
    if comparators.get("primary") not in REQUIRED_COMPARATORS[:-1]:
        raise FreshContractError("final freeze requires one flat primary comparator")

    learners = _mapping(c["learner_design_panel"], name="learner_design_panel")
    if _explicit_bool(learners.get("frozen"), name="learner_design_panel.frozen") is not True:
        raise FreshContractError("final freeze requires a frozen learner/design panel")
    routes = tuple(learners.get("routes", ()))
    if len(routes) < 2 or any(not isinstance(route, str) or not route.strip() for route in routes):
        raise FreshContractError("final freeze requires at least two named learner/design routes")

    promotion = _mapping(c["promotion"], name="promotion")
    if _explicit_bool(promotion.get("frozen"), name="promotion.frozen") is not True:
        raise FreshContractError("final freeze requires frozen EMP thresholds")
    gates = _mapping(promotion["gate_vector"], name="promotion.gate_vector")
    _finite_number(_mapping(gates["EMP-A"], name="EMP-A").get("minimum_mean_gain"), name="EMP-A.minimum_mean_gain")
    _finite_number(_mapping(gates["EMP-B"], name="EMP-B").get("minimum_lower_bound"), name="EMP-B.minimum_lower_bound")
    emp_c = _mapping(gates["EMP-C"], name="EMP-C")
    margin = _finite_number(emp_c.get("noninferiority_margin"), name="EMP-C.noninferiority_margin")
    if margin < 0:
        raise FreshContractError("EMP-C noninferiority margin must be >= 0")
    _probability(_mapping(gates["EMP-D"], name="EMP-D").get("minimum_stable_fraction"), name="EMP-D.minimum_stable_fraction")
    if _mapping(gates["EMP-E"], name="EMP-E").get("maximum_violation_rate") != 0:
        raise FreshContractError("EMP-E maximum_violation_rate must remain zero")
    if _mapping(gates["EMP-F"], name="EMP-F").get("required") is not True:
        raise FreshContractError("EMP-F must remain required")
