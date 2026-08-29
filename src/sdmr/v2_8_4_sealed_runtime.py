"""Guarded one-shot sealed runtime for Product-A v2.8.4.

The scientific implementation remains the inherited v2.8.3 adapter around the
frozen v2.7.2 sealed-audit and decision cores.  This module adds only provenance,
receipt, environment, and retry-state guards around that implementation.

Nothing in this module changes candidates, predictors, thresholds, taxa, M,
seeds, fraction, RNG identities, or the fixed three-part decision rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, Mapping

from .v2_8_4_presealed_receipt import ENVIRONMENT_RECEIPT_PURPOSE
from .v2_8_4_sealed_boundary import (
    EXPECTED_SEEDS,
    build_truth_blind_input_gate,
    load_sealed_boundary_contract,
    verify_presealed_receipt_payload,
)

GATE_PURPOSE = "product_a_v2_8_4_truth_blind_sealed_input_gate"
AUDIT_PURPOSE = "product_a_v2_7_2_fresh_part_sealed_audit"
MATERIALIZATION_PURPOSE = "product_a_v2_7_2_fresh_part_model_pool_materialization"
PRETRUTH_PURPOSE = "product_a_v2_7_2_fresh_part_pretruth_freeze"
FINAL_PURPOSE = "product_a_v2_7_2_fresh_final_models_presealed"


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str | Path, payload: Mapping[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _gate(boundary: Mapping[str, object], gate_path: str | Path) -> dict:
    gate = _load(gate_path)
    if gate.get("purpose") != GATE_PURPOSE:
        raise ValueError("v2.8.4 sealed runtime received wrong truth-blind gate")
    embedded = str(gate.get("gate_digest", ""))
    body = dict(gate)
    body.pop("gate_digest", None)
    if embedded != hashlib.sha256(_canonical(body)).hexdigest():
        raise ValueError("v2.8.4 truth-blind gate digest changed")
    if gate.get("scientific_execution_id") != boundary["scientific_execution_id"]:
        raise ValueError("v2.8.4 truth-blind gate scientific identity changed")
    if gate.get("full_primary_denominator_presealed") is not True:
        raise ValueError("v2.8.4 truth-blind gate lacks full denominator")
    if gate.get("sealed_execution_authorized") is not False:
        raise ValueError("truth-blind gate must not itself authorize sealed execution")
    for key in (
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if gate.get(key) is not False:
            raise ValueError(f"v2.8.4 truth-blind gate crossed boundary: {key}")
    expected = {
        int(row["part_seed"]): (
            int(row["artifact_id"]),
            str(row["artifact_digest"]),
            str(row["receipt_digest"]),
        )
        for row in boundary["presealed_receipts"]
    }
    observed = {
        int(row["part_seed"]): (
            int(row["artifact_id"]),
            str(row["artifact_digest"]),
            str(row["receipt_digest"]),
        )
        for row in gate.get("receipt_artifacts", [])
    }
    if observed != expected:
        raise ValueError("v2.8.4 truth-blind gate receipt pins changed")
    return gate


def _receipt(boundary: Mapping[str, object], receipt_path: str | Path, seed: int) -> dict:
    receipt = verify_presealed_receipt_payload(_load(receipt_path), boundary=boundary)
    if int(receipt["part_seed"]) != int(seed) or int(seed) not in EXPECTED_SEEDS:
        raise ValueError("v2.8.4 sealed part receipt seed mismatch")
    return receipt


def _environment(boundary: Mapping[str, object], environment_receipt_path: str | Path) -> dict:
    receipt = _load(environment_receipt_path)
    if receipt.get("purpose") != ENVIRONMENT_RECEIPT_PURPOSE:
        raise ValueError("v2.8.4 sealed runtime received wrong environment receipt")
    implementation = boundary["presealed_implementation_identity"]
    if receipt.get("environment_digest") != implementation["environment_digest"]:
        raise ValueError("v2.8.4 sealed runtime environment digest changed")
    if receipt.get("dependency_lock_sha256") != implementation["dependency_lock_sha256"]:
        raise ValueError("v2.8.4 sealed runtime dependency lock changed")
    for key in (
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if receipt.get(key) is not False:
            raise ValueError(f"v2.8.4 environment receipt crossed boundary: {key}")
    return receipt


def input_gate(
    *, boundary_path: str | Path, receipt_paths: Iterable[str | Path],
    outer_artifact_catalog_path: str | Path, output_path: str | Path,
) -> dict:
    raw = _load(outer_artifact_catalog_path)
    rows = raw.get("artifacts", raw if isinstance(raw, list) else [])
    return build_truth_blind_input_gate(
        boundary_path=boundary_path,
        receipt_paths=receipt_paths,
        outer_artifacts=rows,
        output_path=output_path,
    )


def _verify_artifact_row(
    row: Mapping[str, object], *, pin: Mapping[str, object], expected_run_id: int,
) -> None:
    observed = (
        int(row.get("id", -1)),
        str(row.get("name", "")),
        str(row.get("digest", "")),
        int(row.get("size_in_bytes", -1)),
        bool(row.get("expired", True)),
        int((row.get("workflow_run") or {}).get("id", -1)),
    )
    expected = (
        int(pin["artifact_id"]),
        str(pin["artifact_name"]),
        str(pin["artifact_digest"]),
        int(pin["artifact_size_bytes"]),
        False,
        int(expected_run_id),
    )
    if observed != expected:
        raise ValueError(f"v2.8.4 sealed input artifact changed: {pin['artifact_name']}")


def part_input_manifest(
    *, boundary_path: str | Path, gate_path: str | Path, receipt_path: str | Path,
    artifact_catalog_path: str | Path, part_seed: int, output_path: str | Path,
) -> dict:
    boundary = load_sealed_boundary_contract(boundary_path)
    gate = _gate(boundary, gate_path)
    receipt = _receipt(boundary, receipt_path, part_seed)
    raw = _load(artifact_catalog_path)
    rows = raw.get("artifacts", raw if isinstance(raw, list) else [])
    by_id = {int(row["id"]): row for row in rows}

    source_by_role = {str(row["role"]): row for row in receipt["source_artifacts"]}
    if set(source_by_role) != {"model_pool", "structural_receipt"}:
        raise ValueError("v2.8.4 sealed part source artifact roles changed")
    required = []
    for role in ("model_pool", "structural_receipt"):
        pin = source_by_role[role]
        row = by_id.get(int(pin["artifact_id"]))
        if row is None:
            raise ValueError(f"missing v2.8.4 sealed source metadata: {role}")
        _verify_artifact_row(row, pin=pin, expected_run_id=33036252432)
        required.append({"role": role, **dict(pin), "workflow_run_id": 33036252432})

    outputs = list(receipt["output_artifacts"])
    pretruth = [row for row in outputs if str(row["artifact_name"]).startswith(f"v284-pretruth-{part_seed}")]
    finals = [row for row in outputs if str(row["artifact_name"]).startswith(f"v284-final-{part_seed}-taxon")]
    if len(pretruth) != 1 or len(finals) != 12:
        raise ValueError("v2.8.4 sealed part pretruth/final artifact denominator changed")
    for role, pins in (("pretruth", pretruth), ("final_model", sorted(finals, key=lambda row: str(row["artifact_name"])))):
        for pin in pins:
            row = by_id.get(int(pin["artifact_id"]))
            if row is None:
                raise ValueError(f"missing v2.8.4 sealed presealed-output metadata: {pin['artifact_name']}")
            _verify_artifact_row(row, pin=pin, expected_run_id=int(receipt["workflow_run_id"]))
            required.append({"role": role, **dict(pin), "workflow_run_id": int(receipt["workflow_run_id"])})

    result = {
        "purpose": "product_a_v2_8_4_sealed_part_input_manifest",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "part_seed": int(part_seed),
        "truth_blind_gate_digest": gate["gate_digest"],
        "presealed_receipt_digest": receipt["receipt_digest"],
        "required_artifacts": required,
        "required_artifact_count": len(required),
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    if len(required) != 15:
        raise ValueError("v2.8.4 sealed part requires exactly 15 input artifacts")
    result["manifest_digest"] = hashlib.sha256(_canonical(result)).hexdigest()
    _write(output_path, result)
    return result


def _assert_pre_read_inputs(
    *, part_dir: str | Path, pretruth_dir: str | Path, final_fit_root: str | Path,
) -> None:
    part = Path(part_dir)
    materialization = _load(part / "contract.json")
    if materialization.get("purpose") != MATERIALIZATION_PURPOSE:
        raise ValueError("v2.8.4 sealed runtime received wrong materialization")
    for key in (
        "sealed_occurrence_raster_values_extracted",
        "sealed_background_raster_values_extracted",
    ):
        if materialization.get(key) is not False:
            raise ValueError(f"v2.8.4 materialization crossed sealed barrier: {key}")

    pretruth = _load(Path(pretruth_dir) / "contract.json")
    if pretruth.get("purpose") != PRETRUTH_PURPOSE or pretruth.get("deterministic_successor") is not True:
        raise ValueError("v2.8.4 sealed runtime received wrong pretruth")
    if int(pretruth.get("model_random_state", -1)) != 0 or int(pretruth.get("selection_process_numpy_seed", -1)) != 0:
        raise ValueError("v2.8.4 pretruth RNG identity changed")

    finals = []
    for path in sorted(Path(final_fit_root).rglob("contract.json")):
        payload = _load(path)
        if payload.get("purpose") != FINAL_PURPOSE:
            continue
        if payload.get("sealed_occurrence_environment_read") is not False:
            raise ValueError("v2.8.4 final fit crossed sealed barrier")
        if payload.get("deterministic_successor") is not True or int(payload.get("model_random_state", -1)) != 0:
            raise ValueError("v2.8.4 final fit identity changed")
        finals.append((str(payload.get("taxon", "")), path))
    if len(finals) != 12 or len({taxon for taxon, _ in finals}) != 12:
        raise ValueError("v2.8.4 sealed runtime requires exactly 12 frozen final fits")


def sealed_audit(
    *, boundary_path: str | Path, gate_path: str | Path, receipt_path: str | Path,
    environment_receipt_path: str | Path, scientific_contract_path: str | Path,
    part_dir: str | Path, pretruth_dir: str | Path, final_fit_root: str | Path,
    manifest_path: str | Path, part_seed: int, sealed_authorization_receipt_digest: str,
    state_path: str | Path, output_dir: str | Path,
) -> dict:
    boundary = load_sealed_boundary_contract(boundary_path)
    gate = _gate(boundary, gate_path)
    receipt = _receipt(boundary, receipt_path, part_seed)
    _environment(boundary, environment_receipt_path)
    if len(sealed_authorization_receipt_digest) != 64 or any(
        char not in "0123456789abcdef" for char in sealed_authorization_receipt_digest
    ):
        raise ValueError("v2.8.4 sealed authorization receipt digest is invalid")
    if not Path(manifest_path).is_file():
        raise ValueError("v2.8.4 sealed CHELSA manifest missing before read")
    _assert_pre_read_inputs(
        part_dir=part_dir, pretruth_dir=pretruth_dir, final_fit_root=final_fit_root
    )

    state = {
        "purpose": "product_a_v2_8_4_sealed_read_state",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "part_seed": int(part_seed),
        "truth_blind_gate_digest": gate["gate_digest"],
        "presealed_receipt_digest": receipt["receipt_digest"],
        "sealed_authorization_receipt_digest": sealed_authorization_receipt_digest,
        "pre_read_validation_complete": True,
        "sealed_read_entered": False,
        "sealed_environment_read": False,
        "sealed_audit_completed": False,
        "retry_without_new_explicit_contract_allowed": True,
    }
    _write(state_path, state)

    # From this write forward we conservatively treat any failure as potentially
    # post-read.  This intentionally sacrifices retryability rather than risk a
    # second look at sealed ecological evidence.
    state["sealed_read_entered"] = True
    state["retry_without_new_explicit_contract_allowed"] = False
    _write(state_path, state)

    from . import v2_8_3_fresh_runtime as v283_runtime

    args = SimpleNamespace(
        contract=str(scientific_contract_path),
        part_dir=str(part_dir),
        pretruth_dir=str(pretruth_dir),
        final_fit_root=str(final_fit_root),
        manifest=str(manifest_path),
        output_dir=str(output_dir),
    )
    v283_runtime.sealed_audit(args)
    contract_path = Path(output_dir) / "contract.json"
    contract = _load(contract_path)
    if contract.get("purpose") != AUDIT_PURPOSE or contract.get("v2_8_3_scientific_transport") is not True:
        raise ValueError("v2.8.4 inherited sealed audit returned wrong contract")
    for key in (
        "candidate_or_threshold_retuning_after_sealed_read",
        "random_seed_change_after_sealed_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if contract.get(key) is not False:
            raise ValueError(f"v2.8.4 inherited sealed audit crossed boundary: {key}")
    contract.update({
        "v2_8_4_sealed_successor": True,
        "v2_8_4_stage": "one_shot_sealed_part_audit",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "part_seed": int(part_seed),
        "presealed_receipt_digest": receipt["receipt_digest"],
        "truth_blind_gate_digest": gate["gate_digest"],
        "sealed_authorization_receipt_digest": sealed_authorization_receipt_digest,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    })
    _write(contract_path, contract)
    state["sealed_environment_read"] = bool(contract.get("sealed_occurrence_environment_read"))
    state["sealed_audit_completed"] = True
    _write(state_path, state)
    return contract


def finalize_part(
    *, boundary_path: str | Path, audit_dir: str | Path, structural_part_dir: str | Path,
    taxa_path: str | Path, part_seed: int, output_dir: str | Path,
) -> dict:
    boundary = load_sealed_boundary_contract(boundary_path)
    audit = _load(Path(audit_dir) / "contract.json")
    if audit.get("v2_8_4_sealed_successor") is not True:
        raise ValueError("v2.8.4 finalizer refuses untagged sealed audit")
    if audit.get("scientific_execution_id") != boundary["scientific_execution_id"]:
        raise ValueError("v2.8.4 finalizer scientific identity changed")
    if int(audit.get("part_seed", -1)) != int(part_seed):
        raise ValueError("v2.8.4 finalizer part seed changed")
    from . import v2_8_3_fresh_aggregate as aggregate_core

    result = aggregate_core.finalize_part(
        structural_part_dir=structural_part_dir,
        audit_dir=audit_dir,
        taxa_path=taxa_path,
        seed=int(part_seed),
        output_dir=output_dir,
    )
    result = _load(Path(output_dir) / "contract.json")
    result.update({
        "v2_8_4_sealed_successor": True,
        "v2_8_4_stage": "finalized_sealed_part",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "part_seed": int(part_seed),
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    })
    _write(Path(output_dir) / "contract.json", result)
    return result


def aggregate_decision(
    *, boundary_path: str | Path, gate_path: str | Path,
    environment_receipt_path: str | Path, scientific_contract_path: str | Path,
    structural_aggregate_dir: str | Path, finalized_root: str | Path,
    sealed_authorization_receipt_digest: str, output_dir: str | Path,
) -> dict:
    boundary = load_sealed_boundary_contract(boundary_path)
    gate = _gate(boundary, gate_path)
    _environment(boundary, environment_receipt_path)
    finalized = []
    for path in sorted(Path(finalized_root).rglob("contract.json")):
        payload = _load(path)
        if payload.get("v2_8_4_sealed_successor") is not True:
            continue
        if payload.get("v2_8_4_stage") != "finalized_sealed_part":
            continue
        if payload.get("scientific_execution_id") != boundary["scientific_execution_id"]:
            raise ValueError("v2.8.4 aggregate found mixed scientific identity")
        finalized.append(payload)
    if len(finalized) != 3 or {int(row.get("part_seed", -1)) for row in finalized} != set(EXPECTED_SEEDS):
        raise ValueError("v2.8.4 aggregate requires exactly three finalized sealed parts")

    from . import v2_8_3_fresh_aggregate as aggregate_core

    aggregate_core.aggregate(
        contract_path=scientific_contract_path,
        structural_aggregate_dir=structural_aggregate_dir,
        audit_root=finalized_root,
        output_dir=output_dir,
    )
    contract_path = Path(output_dir) / "contract.json"
    result = _load(contract_path)
    result.update({
        "v2_8_4_sealed_successor": True,
        "v2_8_4_stage": "terminal_scientific_decision",
        "scientific_execution_id": boundary["scientific_execution_id"],
        "truth_blind_gate_digest": gate["gate_digest"],
        "sealed_authorization_receipt_digest": sealed_authorization_receipt_digest,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    })
    _write(contract_path, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("input-gate")
    p.add_argument("--boundary", required=True)
    p.add_argument("--receipt", action="append", required=True)
    p.add_argument("--outer-artifact-catalog", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=lambda a: input_gate(
        boundary_path=a.boundary,
        receipt_paths=a.receipt,
        outer_artifact_catalog_path=a.outer_artifact_catalog,
        output_path=a.output,
    ))

    p = sub.add_parser("part-manifest")
    p.add_argument("--boundary", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--artifact-catalog", required=True)
    p.add_argument("--part-seed", required=True, type=int)
    p.add_argument("--output", required=True)
    p.set_defaults(func=lambda a: part_input_manifest(
        boundary_path=a.boundary, gate_path=a.gate, receipt_path=a.receipt,
        artifact_catalog_path=a.artifact_catalog, part_seed=a.part_seed,
        output_path=a.output,
    ))

    p = sub.add_parser("sealed-audit")
    p.add_argument("--boundary", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--environment-receipt", required=True)
    p.add_argument("--scientific-contract", required=True)
    p.add_argument("--part-dir", required=True)
    p.add_argument("--pretruth-dir", required=True)
    p.add_argument("--final-fit-root", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--part-seed", required=True, type=int)
    p.add_argument("--sealed-authorization-receipt-digest", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--output-dir", required=True)
    p.set_defaults(func=lambda a: sealed_audit(
        boundary_path=a.boundary, gate_path=a.gate, receipt_path=a.receipt,
        environment_receipt_path=a.environment_receipt,
        scientific_contract_path=a.scientific_contract, part_dir=a.part_dir,
        pretruth_dir=a.pretruth_dir, final_fit_root=a.final_fit_root,
        manifest_path=a.manifest, part_seed=a.part_seed,
        sealed_authorization_receipt_digest=a.sealed_authorization_receipt_digest,
        state_path=a.state, output_dir=a.output_dir,
    ))

    p = sub.add_parser("finalize-part")
    p.add_argument("--boundary", required=True)
    p.add_argument("--audit-dir", required=True)
    p.add_argument("--structural-part-dir", required=True)
    p.add_argument("--taxa", required=True)
    p.add_argument("--part-seed", required=True, type=int)
    p.add_argument("--output-dir", required=True)
    p.set_defaults(func=lambda a: finalize_part(
        boundary_path=a.boundary, audit_dir=a.audit_dir,
        structural_part_dir=a.structural_part_dir, taxa_path=a.taxa,
        part_seed=a.part_seed, output_dir=a.output_dir,
    ))

    p = sub.add_parser("aggregate")
    p.add_argument("--boundary", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--environment-receipt", required=True)
    p.add_argument("--scientific-contract", required=True)
    p.add_argument("--structural-aggregate-dir", required=True)
    p.add_argument("--finalized-root", required=True)
    p.add_argument("--sealed-authorization-receipt-digest", required=True)
    p.add_argument("--output-dir", required=True)
    p.set_defaults(func=lambda a: aggregate_decision(
        boundary_path=a.boundary, gate_path=a.gate,
        environment_receipt_path=a.environment_receipt,
        scientific_contract_path=a.scientific_contract,
        structural_aggregate_dir=a.structural_aggregate_dir,
        finalized_root=a.finalized_root,
        sealed_authorization_receipt_digest=a.sealed_authorization_receipt_digest,
        output_dir=a.output_dir,
    ))
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
