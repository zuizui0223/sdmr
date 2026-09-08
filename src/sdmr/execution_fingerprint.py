"""Stable fingerprint of the Product-A v2.7.2 scientific execution surface.

Execution-gate JSON files are deliberately excluded because they are expected to
change when run/artifact identities become available. Scientific code, frozen
scientific contracts, the deterministic workflows, and the pinned runtime stack
must remain byte-identical between the determinism probe, 216-shard build, and
post-shard continuation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


FROZEN_SCIENCE_FILES = (
    "pyproject.toml",
    "configs/product_a_v2_7_1_fresh_confirmation_contract.json",
    "configs/product_a_v2_7_1_fresh_confirmation_taxa.csv",
    "configs/product_a_empirical_process_registry_v1.csv",
    "configs/chelsa_v2_1_plant_candidates.csv",
    "configs/product_a_v2_7_2_deterministic_execution_contract.json",
    "configs/product_a_v2_7_2_fresh_promotion_contract.json",
    "configs/product_a_v2_7_2_runtime_constraints.txt",
    ".github/workflows/product-a-v2-7-2-determinism-probe.yml",
    ".github/workflows/product-a-v2-7-2-presealed-shard-build.yml",
    ".github/workflows/product-a-v2-7-2-post-shard-continuation.yml",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scientific_execution_manifest(root: str | Path = ".") -> list[dict[str, object]]:
    root_path = Path(root).resolve()
    paths: set[Path] = set()
    source_root = root_path / "src" / "sdmr"
    if not source_root.is_dir():
        raise FileNotFoundError(f"missing scientific source directory: {source_root}")
    for path in source_root.rglob("*.py"):
        if path.is_file():
            paths.add(path)
    for relative in FROZEN_SCIENCE_FILES:
        path = root_path / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing frozen science file: {relative}")
        paths.add(path)

    manifest: list[dict[str, object]] = []
    for path in sorted(paths, key=lambda p: p.relative_to(root_path).as_posix()):
        relative = path.relative_to(root_path).as_posix()
        manifest.append(
            {
                "path": relative,
                "size": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
        )
    return manifest


def scientific_execution_fingerprint(root: str | Path = ".") -> dict[str, object]:
    manifest = scientific_execution_manifest(root)
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "purpose": "product_a_v2_7_2_scientific_execution_fingerprint",
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "n_files": len(manifest),
        "files": manifest,
    }


def main() -> None:
    print(json.dumps(scientific_execution_fingerprint(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
