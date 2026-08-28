import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "configs" / "product_a_v2_8_4_environment_timeout_freeze.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _newline_canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_calibration_decision_and_environment_are_exactly_pinned():
    freeze = _load(FREEZE_PATH)
    evidence = freeze["calibration_evidence"]
    decision_path = ROOT / evidence["decision_path"]
    decision = _load(decision_path)
    embedded_digest = decision.pop("decision_digest")
    canonical = json.dumps(decision, sort_keys=True, separators=(",", ":")).encode()

    assert evidence["workflow_run_id"] == 33140419810
    assert evidence["artifact_id"] == 9677721184
    assert evidence["artifact_digest"] == "sha256:3742b48a6f964e2b599dc1c6fadfc656d1e41a4a34c539b0eefdd7144613fc6a"
    assert _newline_canonical_sha256(decision_path) == evidence["decision_file_sha256"]
    assert hashlib.sha256(canonical).hexdigest() == embedded_digest == evidence["decision_digest"]
    assert evidence["completed_cell_count"] == evidence["cell_count"] == 21
    assert evidence["sealed_ecological_outcomes_read"] is False
    assert evidence["telemetry_used_for_scientific_selection"] is False


def test_runtime_sources_and_hashed_dependency_lock_are_frozen():
    freeze = _load(FREEZE_PATH)
    runtime = freeze["runtime_implementation_identity"]
    environment = freeze["runtime_environment"]

    assert runtime["frozen_repository_ref"] == "86ff5212025f36aab996a55c724255d46eb2f634"
    for relative_path, expected in runtime["files"].items():
        assert _newline_canonical_sha256(ROOT / relative_path) == expected
    assert _newline_canonical_sha256(ROOT / environment["requirements_input_path"]) == environment["requirements_input_sha256"]
    assert _newline_canonical_sha256(ROOT / environment["requirements_lock_path"]) == environment["requirements_lock_sha256"]
    lock_text = (ROOT / environment["requirements_lock_path"]).read_text(encoding="utf-8")
    assert environment["lock_resolution_python_minor"] == "3.12"
    assert "--python-version 3.12" in lock_text
    assert "--hash=sha256:" in lock_text
    for name, version in environment["direct_dependencies"].items():
        normalized = name.replace("-", "_")
        assert f"{name}=={version}" in lock_text or f"{normalized}=={version}" in lock_text


def test_timeout_retry_and_receipt_barriers_fail_closed():
    freeze = _load(FREEZE_PATH)
    timeout = freeze["timeout_freeze"]
    retry = freeze["checkpoint_and_retry_identity"]
    receipt = freeze["receipt_barrier"]
    boundary = freeze["execution_boundary"]

    assert timeout["scientific_group_command_timeout_minutes"] == 225
    assert timeout["group_job_timeout_minutes"] == 255
    assert timeout["post_launch_timeout_extension_allowed"] is False
    assert timeout["post_outcome_timeout_retuning_allowed"] is False
    assert retry["technical_retry_allowed_only_presealed"] is True
    assert retry["successful_logical_work_must_not_be_recomputed_after_checkpoint_validation"] is True
    assert retry["partial_checkpoint_requires_exact_input_runtime_and_environment_digest_match"] is True
    assert receipt["presealed_and_sealed_workflows_must_be_separate"] is True
    assert receipt["presealed_receipt_required_before_any_sealed_workflow"] is True
    assert receipt["sealed_retry_after_any_sealed_read_requires_separate_explicit_contract"] is True
    assert boundary["environment_timeout_freeze_complete"] is True
    for key in (
        "presealed_workflow_implemented_and_reviewed",
        "presealed_execution_allowed",
        "sealed_workflow_implemented_and_reviewed",
        "sealed_execution_allowed",
        "workflow_dispatch_allowed",
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        assert boundary[key] is False


def test_scientific_identity_and_source_denominator_are_unchanged():
    freeze = _load(FREEZE_PATH)
    invariants = freeze["scientific_invariants"]
    for key in (
        "taxa_changed",
        "M_changed",
        "seeds_changed",
        "sealed_fraction_changed",
        "thresholds_changed",
        "candidate_library_changed",
        "candidate_predictor_universe_changed",
        "denominator_changed",
        "decision_rule_changed",
    ):
        assert invariants[key] is False
    assert invariants["split_seeds"] == [2026082201, 2026082202, 2026082203]
    assert invariants["M_km"] == [150, 300, 500]
    assert invariants["sealed_fraction"] == 0.25
    assert invariants["primary_denominator"] == 3

    artifacts = freeze["immutable_presealed_source_artifacts"]
    assert len(artifacts) == 6
    assert {a["part_seed"] for a in artifacts} == set(invariants["split_seeds"])
    assert {a["role"] for a in artifacts} == {"model_pool", "structural_receipt"}
    assert len({a["artifact_id"] for a in artifacts}) == 6
    assert all(a["artifact_digest"].startswith("sha256:") for a in artifacts)
