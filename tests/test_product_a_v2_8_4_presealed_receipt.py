import hashlib
import importlib.metadata
import json
from pathlib import Path

import pytest

from sdmr.v2_8_4_presealed_receipt import (
    ENVIRONMENT_IDENTITY_PURPOSE,
    PRESEALED_RECEIPT_PURPOSE,
    build_presealed_part_receipt,
    write_environment_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "configs" / "product_a_v2_8_4_environment_timeout_freeze.json"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_environment_receipt_reuses_exact_calibration_identity(monkeypatch, tmp_path):
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    expected = freeze["runtime_environment"]["direct_dependencies"]
    monkeypatch.setattr(importlib.metadata, "version", lambda name: expected[name])
    monkeypatch.setattr("platform.python_version", lambda: "3.12.11")
    monkeypatch.setattr("platform.python_implementation", lambda: "CPython")
    monkeypatch.setattr(
        "platform.platform",
        lambda: "Linux-6.11.0-1018-azure-x86_64-with-glibc2.39",
    )
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setenv("RUNNER_ARCH", "X64")
    monkeypatch.setenv("ImageOS", "ubuntu24")
    monkeypatch.setenv("ImageVersion", "20250812.1.0")

    identity = {
        "purpose": ENVIRONMENT_IDENTITY_PURPOSE,
        "python_version": "3.12.11",
        "python_implementation": "CPython",
        "platform": "Linux-6.11.0-1018-azure-x86_64-with-glibc2.39",
        "runner_os": "Linux",
        "runner_arch": "X64",
        "runner_image_os": "ubuntu24",
        "runner_image_version": "20250812.1.0",
        "dependencies": expected,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    freeze["runtime_environment"]["scientific_receipt_must_match_environment_digest"] = digest
    local_freeze = tmp_path / "freeze.json"
    _write(local_freeze, freeze)

    receipt = write_environment_receipt(
        freeze_path=local_freeze, output_path=tmp_path / "environment.json"
    )
    assert receipt["environment_digest"] == digest
    assert receipt["sealed_ecological_outcomes_read"] is False
    assert receipt["scientific_promotion_allowed"] is False
    assert receipt["product_b_unblocked"] is False


def _fake_outputs(tmp_path: Path, seed: int, environment_digest: str):
    roots = {
        "precompute": tmp_path / "precompute",
        "M": tmp_path / "M",
        "worker": tmp_path / "worker",
        "pretruth": tmp_path / "pretruth",
        "final": tmp_path / "final",
    }
    artifact_names = []
    group_names = set()
    for taxon in range(12):
        for kind, name in (
            ("precompute", f"v284-precompute-{seed}-taxon{taxon}"),
            ("worker", f"v284-worker-{seed}-taxon{taxon}"),
            ("final", f"v284-final-{seed}-taxon{taxon}"),
        ):
            directory = roots[kind] / name
            _write(directory / "contract.json", {"sealed_occurrence_environment_read": False})
            _write(directory / "environment_receipt.json", {
                "purpose": "product_a_v2_8_4_scientific_environment_receipt",
                "environment_digest": environment_digest,
            })
            artifact_names.append(name)
        for M in ("buffer_150km", "buffer_300km", "buffer_500km"):
            name = f"v284-M-{seed}-taxon{taxon}-{M}"
            directory = roots["M"] / name
            _write(directory / "contract.json", {"sealed_occurrence_environment_read": False})
            _write(directory / "environment_receipt.json", {
                "purpose": "product_a_v2_8_4_scientific_environment_receipt",
                "environment_digest": environment_digest,
            })
            rows = []
            for group in (
                "base", "thermal", "water", "seasonality_phenology",
                "energy_productivity", "snow", "wind",
            ):
                group_name = f"v284-group-{seed}-taxon{taxon}-{M}-{group}-attempt1"
                group_names.add(group_name)
                rows.append({
                    "artifact_name": group_name,
                    "logical_shard_id": f"execution::{seed}::{taxon}::{M}::{group}",
                })
            _write(directory / "group_input_manifest.json", {
                "part_seed": seed, "groups": rows,
            })
            artifact_names.append(name)
    pretruth_name = f"v284-pretruth-{seed}"
    pretruth = roots["pretruth"] / pretruth_name
    _write(pretruth / "contract.json", {"sealed_occurrence_environment_read": False})
    _write(pretruth / "environment_receipt.json", {
        "purpose": "product_a_v2_8_4_scientific_environment_receipt",
        "environment_digest": environment_digest,
    })
    artifact_names.append(pretruth_name)
    artifact_names.extend(group_names)
    return roots, artifact_names


def test_presealed_receipt_requires_and_pins_full_part_denominator(tmp_path):
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    seed = 2026082201
    environment_digest = freeze["runtime_environment"][
        "scientific_receipt_must_match_environment_digest"
    ]
    roots, names = _fake_outputs(tmp_path, seed, environment_digest)
    artifacts = [
        {
            "id": index + 1,
            "name": name,
            "digest": "sha256:" + hashlib.sha256(name.encode()).hexdigest(),
            "size_in_bytes": 100 + index,
            "expired": False,
            "workflow_run": {"id": 12345},
        }
        for index, name in enumerate(names)
    ]
    catalog = tmp_path / "artifacts.json"
    _write(catalog, {"artifacts": artifacts})

    receipt = build_presealed_part_receipt(
        freeze_path=FREEZE,
        artifact_catalog_path=catalog,
        precompute_root=roots["precompute"],
        M_root=roots["M"],
        worker_root=roots["worker"],
        pretruth_root=roots["pretruth"],
        final_root=roots["final"],
        scientific_execution_id="product-a-v2-8-4-fresh-confirmation-v1",
        part_seed=seed,
        workflow_run_id=12345,
        workflow_run_attempt=1,
        runtime_commit_sha="a" * 40,
        reusable_workflow_sha256="b" * 64,
        authorization_receipt_digest="c" * 64,
        output_path=tmp_path / "receipt.json",
    )
    assert receipt["purpose"] == PRESEALED_RECEIPT_PURPOSE
    assert receipt["full_denominator"]["logical_group_shards"] == 252
    assert receipt["full_denominator"]["complete"] is True
    assert len(receipt["output_artifacts"]) == len(set(names))
    assert receipt["sealed_ecological_outcomes_read"] is False
    assert receipt["scientific_promotion_allowed"] is False
    assert receipt["product_b_unblocked"] is False
    assert receipt["authorization_receipt_digest"] == "c" * 64


def test_presealed_receipt_fails_closed_on_missing_final_model(tmp_path):
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    seed = 2026082201
    environment_digest = freeze["runtime_environment"][
        "scientific_receipt_must_match_environment_digest"
    ]
    roots, names = _fake_outputs(tmp_path, seed, environment_digest)
    missing = roots["final"] / f"v284-final-{seed}-taxon11"
    for path in missing.rglob("*"):
        if path.is_file():
            path.unlink()
    missing.rmdir()
    catalog = tmp_path / "artifacts.json"
    _write(catalog, {"artifacts": []})
    with pytest.raises(ValueError, match="full denominator incomplete"):
        build_presealed_part_receipt(
            freeze_path=FREEZE,
            artifact_catalog_path=catalog,
            precompute_root=roots["precompute"],
            M_root=roots["M"],
            worker_root=roots["worker"],
            pretruth_root=roots["pretruth"],
            final_root=roots["final"],
            scientific_execution_id="product-a-v2-8-4-fresh-confirmation-v1",
            part_seed=seed,
            workflow_run_id=12345,
            workflow_run_attempt=1,
            runtime_commit_sha="a" * 40,
            reusable_workflow_sha256="b" * 64,
            authorization_receipt_digest="c" * 64,
            output_path=tmp_path / "receipt.json",
        )
