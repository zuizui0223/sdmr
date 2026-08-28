"""Truth-blind environment and receipt barrier for Product-A v2.8.4.

This module never reads sealed occurrence environments.  It records the exact
runtime identity and proves that one presealed part completed its full frozen
denominator before any separate sealed workflow may be considered.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
from typing import Iterable


ENVIRONMENT_IDENTITY_PURPOSE = "product_a_v2_8_4_runtime_calibration_environment"
ENVIRONMENT_RECEIPT_PURPOSE = "product_a_v2_8_4_scientific_environment_receipt"
PRESEALED_RECEIPT_PURPOSE = "product_a_v2_8_4_presealed_part_receipt"
M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")
GROUPS = (
    "base",
    "thermal",
    "water",
    "seasonality_phenology",
    "energy_productivity",
    "snow",
    "wind",
)


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_environment_receipt(*, freeze_path: str | Path, output_path: str | Path) -> dict:
    freeze = _load(freeze_path)
    expected = freeze["runtime_environment"]["direct_dependencies"]
    versions = {name: importlib.metadata.version(name) for name in expected}
    if versions != expected:
        raise ValueError(f"Product-A v2.8.4 scientific dependency identity changed: {versions}")
    identity = {
        "purpose": ENVIRONMENT_IDENTITY_PURPOSE,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "runner_image_os": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "dependencies": versions,
    }
    if identity["python_version"] != freeze["runtime_environment"]["python_patch"]:
        raise ValueError("Product-A v2.8.4 scientific Python patch changed")
    digest = hashlib.sha256(_canonical(identity)).hexdigest()
    expected_digest = freeze["runtime_environment"][
        "scientific_receipt_must_match_environment_digest"
    ]
    if digest != expected_digest:
        raise ValueError(
            "Product-A v2.8.4 runner environment differs from the frozen calibration environment"
        )
    receipt = {
        "purpose": ENVIRONMENT_RECEIPT_PURPOSE,
        "calibration_environment_identity": identity,
        "environment_digest": digest,
        "dependency_lock_sha256": freeze["runtime_environment"][
            "requirements_lock_sha256"
        ],
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _contract_paths(roots: Iterable[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        paths.extend(Path(root).rglob("contract.json"))
    return sorted(set(paths))


def _assert_presealed_contract(path: Path, payload: dict) -> None:
    forbidden_true = (
        "sealed_occurrence_environment_read",
        "sealed_occurrence_used_for_selection",
        "sealed_occurrence_used_for_process_status",
        "sealed_ecological_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    )
    for key in forbidden_true:
        if payload.get(key) is True:
            raise ValueError(f"presealed receipt found opened/promoted state: {path}:{key}")


def _artifact_catalog_by_name(catalog_path: str | Path, run_id: int) -> dict[str, dict]:
    raw = _load(catalog_path)
    rows = raw.get("artifacts", raw if isinstance(raw, list) else [])
    result: dict[str, dict] = {}
    for row in rows:
        workflow_run = row.get("workflow_run") or {}
        if int(workflow_run.get("id", run_id)) != int(run_id):
            continue
        name = str(row.get("name", ""))
        if name in result:
            raise ValueError(f"duplicate artifact name in presealed run: {name}")
        result[name] = row
    return result


def _pin_artifact(row: dict) -> dict:
    digest = str(row.get("digest", ""))
    if not digest.startswith("sha256:"):
        raise ValueError(f"artifact has no immutable SHA-256 digest: {row.get('name')}")
    if row.get("expired") is True:
        raise ValueError(f"artifact expired before presealed receipt: {row.get('name')}")
    return {
        "artifact_id": int(row["id"]),
        "artifact_name": str(row["name"]),
        "artifact_digest": digest,
        "artifact_size_bytes": int(row["size_in_bytes"]),
    }


def build_presealed_part_receipt(
    *, freeze_path: str | Path, artifact_catalog_path: str | Path,
    precompute_root: str | Path, M_root: str | Path, worker_root: str | Path,
    pretruth_root: str | Path, final_root: str | Path,
    scientific_execution_id: str, part_seed: int, workflow_run_id: int,
    workflow_run_attempt: int, runtime_commit_sha: str,
    reusable_workflow_sha256: str, authorization_receipt_digest: str,
    output_path: str | Path,
) -> dict:
    freeze = _load(freeze_path)
    if int(part_seed) not in freeze["scientific_invariants"]["split_seeds"]:
        raise ValueError("presealed receipt part seed is not frozen")
    if freeze["execution_boundary"]["sealed_execution_allowed"] is not False:
        raise ValueError("environment freeze unexpectedly authorizes sealed execution")

    expected_environment = freeze["runtime_environment"][
        "scientific_receipt_must_match_environment_digest"
    ]
    roots = [precompute_root, M_root, worker_root, pretruth_root, final_root]
    contracts = _contract_paths(roots)
    for path in contracts:
        _assert_presealed_contract(path, _load(path))

    environment_receipts = sorted(
        path for root in roots for path in Path(root).rglob("environment_receipt.json")
    )
    if not environment_receipts:
        raise ValueError("presealed outputs contain no environment receipts")
    for path in environment_receipts:
        receipt = _load(path)
        if receipt.get("purpose") != ENVIRONMENT_RECEIPT_PURPOSE:
            raise ValueError(f"wrong scientific environment receipt: {path}")
        if receipt.get("environment_digest") != expected_environment:
            raise ValueError(f"presealed output environment changed: {path}")

    expected_counts = {
        "precompute": 12,
        "M": 36,
        "worker": 12,
        "pretruth": 1,
        "final": 12,
    }
    observed_counts = {
        "precompute": len(list(Path(precompute_root).glob(f"v284-precompute-{part_seed}-taxon*"))),
        "M": len(list(Path(M_root).glob(f"v284-M-{part_seed}-taxon*-buffer_*km"))),
        "worker": len(list(Path(worker_root).glob(f"v284-worker-{part_seed}-taxon*"))),
        "pretruth": len(list(Path(pretruth_root).glob(f"v284-pretruth-{part_seed}"))),
        "final": len(list(Path(final_root).glob(f"v284-final-{part_seed}-taxon*"))),
    }
    if observed_counts != expected_counts:
        raise ValueError(f"presealed full denominator incomplete: {observed_counts}")

    group_names: set[str] = set()
    logical_group_ids: set[str] = set()
    for manifest_path in sorted(Path(M_root).rglob("group_input_manifest.json")):
        manifest = _load(manifest_path)
        if int(manifest.get("part_seed", -1)) != int(part_seed):
            continue
        for row in manifest.get("groups", []):
            group_names.add(str(row["artifact_name"]))
            logical_group_ids.add(str(row["logical_shard_id"]))
    if len(group_names) != 252 or len(logical_group_ids) != 252:
        raise ValueError("presealed receipt does not cover 12 taxa x 3 M x 7 groups")

    required_artifact_names = set(group_names)
    required_artifact_names.update(
        path.name
        for root in roots
        for path in Path(root).iterdir()
        if path.is_dir()
    )
    catalog = _artifact_catalog_by_name(artifact_catalog_path, workflow_run_id)
    missing = required_artifact_names - set(catalog)
    if missing:
        raise ValueError(f"presealed receipt artifact catalog incomplete: {sorted(missing)}")
    pinned = [_pin_artifact(catalog[name]) for name in sorted(required_artifact_names)]

    result = {
        "purpose": PRESEALED_RECEIPT_PURPOSE,
        "scientific_execution_id": str(scientific_execution_id),
        "part_seed": int(part_seed),
        "workflow_run_id": int(workflow_run_id),
        "workflow_run_attempt": int(workflow_run_attempt),
        "runtime_commit_sha": str(runtime_commit_sha),
        "runtime_ref": str(runtime_commit_sha),
        "reusable_workflow_sha256": str(reusable_workflow_sha256),
        "authorization_receipt_digest": str(authorization_receipt_digest),
        "environment_digest": expected_environment,
        "dependency_lock_sha256": freeze["runtime_environment"]["requirements_lock_sha256"],
        "source_artifacts": [
            row
            for row in freeze["immutable_presealed_source_artifacts"]
            if int(row["part_seed"]) == int(part_seed)
        ],
        "output_artifacts": pinned,
        "full_denominator": {
            "taxa": 12,
            "M": 3,
            "evaluation_groups_per_M": 7,
            "logical_group_shards": 252,
            "M_shards": 36,
            "final_models": 12,
            "complete": True,
        },
        "checkpoint_retry_identity_preserved": True,
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    result["receipt_digest"] = hashlib.sha256(_canonical(result)).hexdigest()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    env = sub.add_parser("environment")
    env.add_argument("--freeze", required=True)
    env.add_argument("--output", required=True)
    env.set_defaults(func=lambda a: write_environment_receipt(
        freeze_path=a.freeze, output_path=a.output
    ))

    receipt = sub.add_parser("presealed-receipt")
    receipt.add_argument("--freeze", required=True)
    receipt.add_argument("--artifact-catalog", required=True)
    receipt.add_argument("--precompute-root", required=True)
    receipt.add_argument("--M-root", required=True)
    receipt.add_argument("--worker-root", required=True)
    receipt.add_argument("--pretruth-root", required=True)
    receipt.add_argument("--final-root", required=True)
    receipt.add_argument("--scientific-execution-id", required=True)
    receipt.add_argument("--part-seed", type=int, required=True)
    receipt.add_argument("--workflow-run-id", type=int, required=True)
    receipt.add_argument("--workflow-run-attempt", type=int, required=True)
    receipt.add_argument("--runtime-commit-sha", required=True)
    receipt.add_argument("--reusable-workflow-sha256", required=True)
    receipt.add_argument("--authorization-receipt-digest", required=True)
    receipt.add_argument("--output", required=True)
    receipt.set_defaults(func=lambda a: build_presealed_part_receipt(
        freeze_path=a.freeze,
        artifact_catalog_path=a.artifact_catalog,
        precompute_root=a.precompute_root,
        M_root=a.M_root,
        worker_root=a.worker_root,
        pretruth_root=a.pretruth_root,
        final_root=a.final_root,
        scientific_execution_id=a.scientific_execution_id,
        part_seed=a.part_seed,
        workflow_run_id=a.workflow_run_id,
        workflow_run_attempt=a.workflow_run_attempt,
        runtime_commit_sha=a.runtime_commit_sha,
        reusable_workflow_sha256=a.reusable_workflow_sha256,
        authorization_receipt_digest=a.authorization_receipt_digest,
        output_path=a.output,
    ))
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
