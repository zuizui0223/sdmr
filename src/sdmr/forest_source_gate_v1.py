"""Response-blind source admission for real forest SDMR x Structural studies.

A verified ecological-source metadata receipt is NOT a biological result.
This layer only audits whether a *new*, independently frozen evaluation
protocol could be specified. It never loads species responses, fits models,
or reinterprets archived negative or positive ecological effects.

True zero catch, no sampling, missing observations, selected survivors
and unknown status must not be collapsed into a single "absence".
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from math import isfinite
from typing import Mapping, Sequence


OBSERVATION_MODES = frozenset({
    "capture_conditional", "survivor_conditional", "unconditional",
    "metadata_only",
})
FRAMES = frozenset({
    "complete_including_zeros", "detected_only", "survivors_only",
    "not_audited",
})
EFFORT_STATES = frozenset({"verified", "conditional", "unknown"})
ATTRITION_STATES = frozenset({
    "accounted", "not_applicable", "survivor_selected", "unknown",
})
TAXON_STATES = frozenset({
    "verified_for_declared_response", "partial_format_sensitivity",
    "header_only", "not_applicable", "unknown",
})
BLOCK_STATES = frozenset({
    "verified_independent", "single_site_block", "nested_parent_unknown",
    "region_time_singleton", "unknown",
})
CARRIER_STATES = frozenset({"complete", "partial", "unknown"})
RESPONSE_STATES = frozenset({"unopened", "previously_opened"})
RECEIPT_ROLES = frozenset({"original_source", "source_only_audit", "analysis_artifact"})
DESIGN_STATES = frozenset({"outcome_blind", "historical_outcome_exposed", "unfrozen"})


@dataclass(frozen=True)
class ForestSourceProfile:
    """Source-only metadata. No response measurement or effect fields."""

    source_id: str
    study_reference: str
    evidence_family_id: str
    publisher_source: str
    receipt_role: str
    receipt_sha256: str
    endpoint: str
    operator: str
    observation_mode: str
    sampling_frame: str
    effort_status: str
    attrition_status: str
    taxon_status: str
    block_status: str
    process_carriers: str
    response_state: str
    design_state: str
    n_source_units: int
    n_eligible_units: int | None
    n_blocks_reported: int | None
    min_block_units: int | None
    source_identity_verified: bool
    temporal_alignment_verified: bool
    notes: str

    def __post_init__(self) -> None:
        for field in (
            "source_id", "study_reference", "evidence_family_id",
            "publisher_source", "endpoint", "operator", "notes",
        ):
            if not str(getattr(self, field)).strip():
                raise ValueError(f"{field} must be nonempty")
        enums = {
            "receipt_role": RECEIPT_ROLES,
            "observation_mode": OBSERVATION_MODES,
            "sampling_frame": FRAMES,
            "effort_status": EFFORT_STATES,
            "attrition_status": ATTRITION_STATES,
            "taxon_status": TAXON_STATES,
            "block_status": BLOCK_STATES,
            "process_carriers": CARRIER_STATES,
            "response_state": RESPONSE_STATES,
            "design_state": DESIGN_STATES,
        }
        for field, allowed in enums.items():
            if getattr(self, field) not in allowed:
                raise ValueError(f"invalid {field}")
        digest = self.receipt_sha256
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("receipt_sha256 must be lowercase SHA256")
        if (not isinstance(self.n_source_units, int) or
                self.n_source_units < 0):
            raise ValueError("n_source_units must be a nonnegative integer")
        for field in ("n_eligible_units", "n_blocks_reported", "min_block_units"):
            value = getattr(self, field)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{field} must be null or a nonnegative integer")
        if (self.n_eligible_units is not None and
                self.n_eligible_units > self.n_source_units):
            raise ValueError("eligible units exceed source units")
        if (self.n_blocks_reported is None) != (self.min_block_units is None):
            raise ValueError("reported blocks and minimum block size must be paired")
        if self.observation_mode == "unconditional":
            if (self.sampling_frame != "complete_including_zeros" or
                    self.effort_status != "verified"):
                raise ValueError(
                    "unconditional estimand requires audited zeros AND effort"
                )
        if self.observation_mode == "survivor_conditional":
            if self.sampling_frame != "survivors_only":
                raise ValueError("survivor estimand requires survivors_only frame")
        if self.observation_mode == "capture_conditional":
            if self.sampling_frame not in ("detected_only", "complete_including_zeros"):
                raise ValueError("capture estimand requires recorded sample opportunity")
        if self.design_state == "historical_outcome_exposed" and (
            self.response_state != "previously_opened"
        ):
            raise ValueError("outcome-exposed design must have previously opened response")
        if self.response_state == "unopened" and self.design_state == "historical_outcome_exposed":
            raise ValueError("unopened response cannot have historical exposure")


@dataclass(frozen=True)
class ForestSourceDecision:
    source_id: str
    status: str
    reasons: tuple[str, ...]
    n_source_units: int
    n_eligible_units: int | None
    independent_blocks: int | None
    observation_process_adequate: bool
    process_carriers_complete: bool
    response_opening_authorized: bool
    biological_effect_estimated: bool
    source_only: bool


def assess_forest_source(
    source: ForestSourceProfile,
    *,
    minimum_independent_blocks: int = 6,
    minimum_per_block: int = 2,
) -> ForestSourceDecision:
    """Conservatively authorize *protocol drafting*, never biological opening.

    Boolean flags and counts are declarations tied to source receipts; passing
    this gate is necessary but not sufficient for valid original data linkage.
    """
    if minimum_independent_blocks < 2 or minimum_per_block < 2:
        raise ValueError("independent-group thresholds must be >=2")
    reasons: list[str] = []
    if not source.source_identity_verified:
        reasons.append("source_identity_or_method_grain_unverified")
    if source.n_eligible_units is None:
        reasons.append("source_eligible_denominator_unknown")
    elif source.n_eligible_units == 0:
        reasons.append("zero_eligible_observation_units")
    if source.n_blocks_reported is None:
        reasons.append("independent_block_denominator_unknown")
    elif source.n_blocks_reported < minimum_independent_blocks:
        reasons.append("insufficient_independent_blocks")
    if source.min_block_units is None:
        reasons.append("minimum_block_support_unknown")
    elif source.min_block_units < minimum_per_block:
        reasons.append("insufficient_units_per_block")
    if source.block_status != "verified_independent":
        reasons.append(f"block_design_{source.block_status}")
    if source.taxon_status not in (
        "verified_for_declared_response", "not_applicable"
    ):
        reasons.append(f"response_ontology_{source.taxon_status}")
    if not source.temporal_alignment_verified:
        reasons.append("measurement_time_alignment_unverified")

    # Even when the biological endpoint is explicitly *conditional on detected
    # or surviving units*, that conditionality is not a causal sampling model.
    observation_adequate = (
        source.sampling_frame == "complete_including_zeros"
        and source.effort_status == "verified"
        and source.attrition_status in ("accounted", "not_applicable")
    )
    if not observation_adequate:
        reasons.append("observation_selection_or_zero_frame_unresolved")
    if source.process_carriers != "complete":
        reasons.append(f"declared_process_carriers_{source.process_carriers}")
    if source.response_state == "previously_opened":
        reasons.append("prior_response_exposed_no_fresh_confirmation")
    if source.design_state != "outcome_blind":
        reasons.append(f"design_{source.design_state}")

    # Do not turn sample-source eligibility into a response-opening permission.
    if ("zero_eligible_observation_units" in reasons or
            "insufficient_independent_blocks" in reasons or
            "insufficient_units_per_block" in reasons or
            "block_design_region_time_singleton" in reasons):
        status = "not_estimable_under_new_protocol"
    elif any(x.startswith("source_") or x.startswith("response_ontology_")
             or x.startswith("block_design_") or
             x == "measurement_time_alignment_unverified" for x in reasons):
        status = "source_or_ontology_hold"
    elif "observation_selection_or_zero_frame_unresolved" in reasons:
        status = "observation_unresolved"
    elif "prior_response_exposed_no_fresh_confirmation" in reasons:
        status = "retrospective_only"
    elif reasons:
        status = "method_contract_incomplete"
    else:
        status = "metadata_ready_for_separate_protocol_freeze"

    return ForestSourceDecision(
        source_id=source.source_id,
        status=status,
        reasons=tuple(reasons),
        n_source_units=source.n_source_units,
        n_eligible_units=source.n_eligible_units,
        independent_blocks=source.n_blocks_reported,
        observation_process_adequate=observation_adequate,
        process_carriers_complete=source.process_carriers == "complete",
        response_opening_authorized=False,
        biological_effect_estimated=False,
        source_only=True,
    )


def source_catalog_receipt(
    catalog: Mapping[str, object],
    *,
    minimum_independent_blocks: int = 6,
    minimum_per_block: int = 2,
) -> dict[str, object]:
    """Audit exact fields of a saved source-only catalog; reject hidden rows."""
    if catalog.get("schema") != "sdmr.forest_observation_source_only.v1":
        raise ValueError("unrecognized source-only catalog schema")
    entries = catalog.get("sources")
    if not isinstance(entries, list) or not entries:
        raise ValueError("nonempty sources array required")
    expected = set(ForestSourceProfile.__dataclass_fields__)
    actual: list[ForestSourceProfile] = []
    for row in entries:
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError(
                "source metadata field mismatch: no biological outcome columns permitted"
            )
        actual.append(ForestSourceProfile(**row))
    source_ids = [s.source_id for s in actual]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("duplicate source ID")
    results = [
        asdict(assess_forest_source(
            source, minimum_independent_blocks=minimum_independent_blocks,
            minimum_per_block=minimum_per_block))
        for source in actual
    ]
    by_status: dict[str, int] = {}
    for result in results:
        by_status[result["status"]] = by_status.get(result["status"], 0) + 1
    return {
        "schema": "sdmr.forest_source_gate_receipt.v1",
        "n_source_profiles": len(results),
        "n_protocol_ready": sum(
            r["status"] == "metadata_ready_for_separate_protocol_freeze"
            for r in results
        ),
        "n_biological_outcomes_opened": 0,
        "n_new_models_fit": 0,
        "no_existing_result_reclassified": True,
        "status_counts": by_status,
        "decisions": results,
    }
