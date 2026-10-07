"""Fail-closed deterministic reproduction gate for prospective v26."""
from __future__ import annotations

from collections.abc import Mapping


PURPOSE = "sealed_answer_superiority_v26_truth_blind_refinement_receipt"
COMPARE_FIELDS = (
    "n_contexts",
    "n_supported_members",
    "n_separator_rows",
    "context_sets_sha256",
    "separator_evidence_sha256",
    "context_refinements_sha256",
    "member_audit_sha256",
)


def compare_truth_blind_receipts(
    receipt_a: Mapping[str, object],
    receipt_b: Mapping[str, object],
) -> dict[str, object]:
    """Authorize truth opening only after exact truth-blind reproduction."""
    receipts = (receipt_a, receipt_b)
    for receipt in receipts:
        if receipt.get("purpose") != PURPOSE:
            raise ValueError("wrong v26 truth-blind receipt purpose")
        if receipt.get("truth_opened") is not False:
            raise ValueError("determinism gate requires truth-blind receipts")
        missing = [field for field in COMPARE_FIELDS if field not in receipt]
        if missing:
            raise ValueError("truth-blind receipt missing fields: " + ", ".join(missing))

    replicate_ids = [str(receipt_a.get("replicate_id", "")), str(receipt_b.get("replicate_id", ""))]
    if not all(replicate_ids) or replicate_ids[0] == replicate_ids[1]:
        raise ValueError("determinism gate requires two distinct replicate ids")

    mismatched = [
        field for field in COMPARE_FIELDS
        if receipt_a[field] != receipt_b[field]
    ]
    matched = not mismatched
    return {
        "purpose": "sealed_answer_superiority_v26_determinism_gate",
        "replicate_ids": replicate_ids,
        "compared_fields": list(COMPARE_FIELDS),
        "mismatched_fields": mismatched,
        "deterministic_match": matched,
        "truth_open_authorized": matched,
    }
