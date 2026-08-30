import hashlib
import json
from pathlib import Path

import pytest


RECOVERY_REF = "refs/heads/frozen/product-a-v2-8-4-sealed-v1-pre-read-recovery-1"
AUTH = Path("configs/product_a_v2_8_4_sealed_execution_authorization.json")
CALLER = Path(".github/workflows/product-a-v2-8-4-sealed-authorized.yml")
GENERATOR = Path(".github/workflows/generate-product-a-v2-8-4-sealed-pre-read-recovery-authorization.yml")
RECOVERY = Path("configs/product_a_v2_8_4_sealed_pre_read_recovery_contract.json")


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_recovery_authorization_generation_is_complete_and_generator_removed():
    assert not GENERATOR.exists(), "temporary authorization generator must not enter main"
    assert AUTH.is_file()
    assert CALLER.is_file()
    assert RECOVERY.is_file()

    payload = json.loads(AUTH.read_text(encoding="utf-8"))
    assert payload["purpose"] == "product_a_v2_8_4_one_shot_sealed_execution_authorization"
    assert payload["scientific_execution_id"] == "product-a-v2-8-4-fresh-confirmation-v1"
    assert payload["one_shot"] is True
    assert payload["operational_attempt"] == 2
    assert payload["authorized_ref"] == RECOVERY_REF
    assert payload["authorized_caller"]["path"] == str(CALLER)
    assert payload["authorized_caller"]["newline_canonical_sha256"] == _sha(CALLER)
    assert payload["implementation_identity"]["runtime_ref"] not in {
        "ba12f96be48545819a72fc714f083cd5c00520ad",
        "2690c169adc2d9261a13b4c801c8a02006fc7cca",
    }

    embedded = payload.pop("authorization_receipt_digest")
    assert embedded == hashlib.sha256(_canonical(payload)).hexdigest()
    payload["authorization_receipt_digest"] = embedded

    recovery = payload["pre_read_recovery"]
    assert int(recovery["prior_workflow_run_id"]) == 33309627503
    assert recovery["prior_failure_fingerprint"] == "ModuleNotFoundError: No module named 'pandas'"
    assert recovery["prior_sealed_read_entered"] is False
    assert recovery["prior_sealed_ecological_outcomes_read"] is False
    assert recovery["prior_scientific_decision_exists"] is False

    execution = payload["execution_boundary"]
    assert execution["sealed_ecological_outcomes_read"] is False
    assert execution["scientific_promotion_allowed"] is False
    assert execution["product_b_unblocked"] is False


def test_recovery_caller_is_exactly_second_dispatch_only():
    text = CALLER.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert RECOVERY_REF in text
    assert "33309627503" in text
    assert "ba12f96be48545819a72fc714f083cd5c00520ad" in text
    assert "total_count',-1)) != 2" in text
    assert "set(by_id) != {prior_run_id,current_run_id}" in text
    assert "99252220557:'success'" in text
    assert "99252233545:'failure'" in text
    assert "99252247454:'skipped'" in text
    assert "99252247966:'skipped'" in text
    assert "third" not in text.lower() or "forbid" in text.lower()
