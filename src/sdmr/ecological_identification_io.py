"""Portable preparation bundles for the high-level ecological-identification workflow."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json

import pandas as pd

from .ecological_identification_workflow import (
    EcologicalIdentificationConfig,
    PreparedEcologicalIdentificationStudy,
)
from .model import ModelSpec
from .sealed_occurrence_contract import OccurrenceAnswerCheckSplit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_prepared_ecological_identification_study(
    study: PreparedEcologicalIdentificationStudy,
    directory: str | Path,
) -> Path:
    """Persist the frozen pre-fit contract before M/background construction."""

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    tables = {
        "occurrence_split.csv": study.occurrence_split.assignment,
        "registry_proposal.csv": study.registry_proposal,
        "process_registry.csv": study.process_registry,
    }
    hashes: dict[str, str] = {}
    for filename, frame in tables.items():
        path = root / filename
        frame.to_csv(path, index=False)
        hashes[filename] = _sha256(path)

    cfg = study.config
    manifest = {
        "format": "sdmr_ecological_identification_prepared_v1",
        "split_digest": study.occurrence_split.split_digest,
        "predictors": list(study.predictors),
        "process_universe": list(study.process_universe),
        "config": {
            "id_col": cfg.id_col,
            "lon_col": cfg.lon_col,
            "lat_col": cfg.lat_col,
            "outer_n_blocks": int(cfg.outer_n_blocks),
            "answer_check_fraction": float(cfg.answer_check_fraction),
            "outer_random_state": int(cfg.outer_random_state),
            "inner_n_blocks": int(cfg.inner_n_blocks),
            "inner_n_splits": int(cfg.inner_n_splits),
            "inner_random_state": int(cfg.inner_random_state),
            "chance_score": float(cfg.chance_score),
            "minimum_margin": float(cfg.minimum_margin),
            "sem_multiplier": float(cfg.sem_multiplier),
            "model_specs": [
                {
                    "C": float(spec.C),
                    "degree": int(spec.degree),
                    "penalty": spec.penalty,
                    "random_state": (
                        None if spec.random_state is None else int(spec.random_state)
                    ),
                }
                for spec in cfg.model_specs
            ],
        },
        "files_sha256": hashes,
    }
    manifest_path = root / "study_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def load_prepared_ecological_identification_study(
    directory: str | Path,
) -> PreparedEcologicalIdentificationStudy:
    """Load and hash-verify a frozen preparation bundle."""

    root = Path(directory)
    manifest_path = root / "study_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"prepared study manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "sdmr_ecological_identification_prepared_v1":
        raise ValueError("unsupported ecological-identification preparation format")

    hashes = dict(manifest.get("files_sha256", {}))
    for filename in ("occurrence_split.csv", "registry_proposal.csv", "process_registry.csv"):
        path = root / filename
        if not path.exists():
            raise FileNotFoundError(f"prepared study file missing: {path}")
        expected = str(hashes.get(filename, ""))
        actual = _sha256(path)
        if not expected or actual != expected:
            raise ValueError(f"prepared study file hash mismatch: {filename}")

    raw_cfg = dict(manifest["config"])
    model_specs = tuple(
        ModelSpec(
            C=float(item["C"]),
            degree=int(item["degree"]),
            penalty=str(item["penalty"]),
            random_state=(
                None if item.get("random_state") is None else int(item["random_state"])
            ),
        )
        for item in raw_cfg.pop("model_specs")
    )
    cfg = EcologicalIdentificationConfig(
        **raw_cfg,
        model_specs=model_specs,
    )

    assignment = pd.read_csv(root / "occurrence_split.csv", dtype={cfg.id_col: str})
    split = OccurrenceAnswerCheckSplit(
        assignment=assignment,
        id_col=cfg.id_col,
        split_digest=str(manifest["split_digest"]),
    )
    proposal = pd.read_csv(root / "registry_proposal.csv")
    registry = pd.read_csv(root / "process_registry.csv")
    return PreparedEcologicalIdentificationStudy(
        config=cfg,
        occurrence_split=split,
        registry_proposal=proposal,
        process_registry=registry,
        predictors=tuple(str(x) for x in manifest["predictors"]),
        process_universe=tuple(str(x) for x in manifest["process_universe"]),
    )
