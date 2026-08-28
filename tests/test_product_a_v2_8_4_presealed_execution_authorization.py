import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "configs" / "product_a_v2_8_4_presealed_execution_authorization.json"
CALLER = ROOT / ".github" / "workflows" / "product-a-v2-8-4-presealed-authorized.yml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_authorization_digest_and_caller_are_exactly_pinned():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    embedded = auth.pop("authorization_receipt_digest")
    canonical = json.dumps(auth, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == embedded
    assert _sha(CALLER) == auth["authorized_caller_workflow_sha256"]
    assert auth["implementation_identity"]["runtime_ref"] == "b4c8e05ef75f1e65edc3603aad3040cf427a7d30"


def test_authorization_opens_presealed_only_and_preserves_science():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    boundary = auth["execution_boundary"]
    assert boundary["presealed_workflow_implemented_and_reviewed"] is True
    assert boundary["presealed_execution_allowed"] is True
    assert boundary["workflow_dispatch_allowed"] is True
    for key in (
        "sealed_workflow_implemented_and_reviewed",
        "sealed_execution_allowed",
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        assert boundary[key] is False
    for key, value in auth["scientific_invariants"].items():
        if key.endswith("_changed"):
            assert value is False
    assert auth["authorized_part_seeds"] == [2026082201, 2026082202, 2026082203]


def test_retry_and_publication_stops_are_fail_closed():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    retry = auth["dispatch_and_retry_policy"]
    assert retry["successful_logical_group_recomputation_allowed"] is False
    assert retry["selective_failed_job_retry_allowed_presealed_only"] is True
    assert retry["broad_rerun_after_partial_success_allowed"] is False
    assert retry["technical_failure_may_not_change_taxa_M_seeds_fraction_thresholds_candidates_or_denominator"] is True
    assert auth["runtime_environment"]["technical_STOP_is_scientific_negative"] is False
    assert auth["publication_stop_rule"]["Product_B_must_not_delay_Product_A_manuscript"] is True


def test_caller_dispatches_only_frozen_choices_into_pinned_reusable_workflow():
    text = CALLER.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    for seed in ("2026082201", "2026082202", "2026082203"):
        assert f"- '{seed}'" in text
    assert "@b4c8e05ef75f1e65edc3603aad3040cf427a7d30" in text
    assert "runtime_ref: b4c8e05ef75f1e65edc3603aad3040cf427a7d30" in text
    assert "product-a-v2-8-4-fresh-confirmation-v1" in text
    assert "sealed" in text
    assert "sealed-audit" not in text
