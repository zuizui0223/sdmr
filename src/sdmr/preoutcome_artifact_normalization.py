"""Normalize legacy outer-CV labels in sealed-blind Product-A v2.1 artifacts.

The generic niche-recovery metrics historically call an in-model-pool held-out
fold ``sealed``.  Product-A v2.1 reserves *sealed* for the authoritative outer
answer-check data, so those legacy labels must not cross the pre-outcome decision
boundary unchanged.

Only two known outer-CV columns may be renamed, and only after the artifact's
contract proves that no authoritative sealed row or old external validation
outcome entered the experiment.  Any other sealed-looking column is rejected.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd


LEGACY_OUTER_CV_RENAMES = {
    "n_sealed_occurrences": "n_outer_heldout_occurrences",
    "sealed_pc12_envelope_coverage90": "heldout_pc12_envelope_coverage90",
}


@dataclass(frozen=True)
class PreoutcomeArtifactNormalization:
    metrics_file: str
    renamed_columns: tuple[str, ...]
    model_pool_only_contract_verified: bool
    authoritative_sealed_rows_read: bool = False
    old_external_sealed_outcomes_read: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _load_contract(root: Path) -> dict[str, object]:
    path = root / "product_a_v2_1_preoutcome_contract.json"
    if not path.exists():
        raise FileNotFoundError(path)
    contract = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "development_evidence": "discovery_taxa_model_pool_only",
        "old_external_sealed_outcomes_read": False,
        "sealed_rows_returned_to_experiment": False,
        "scientific_promotion_run": False,
    }
    mismatches = {
        key: {"expected": expected, "observed": contract.get(key)}
        for key, expected in required.items()
        if contract.get(key) != expected
    }
    if mismatches:
        raise ValueError(
            "artifact is not a verified model-pool-only pre-outcome result: "
            + json.dumps(mismatches, sort_keys=True)
        )
    return contract


def _find_metrics_file(root: Path) -> Path:
    for name in (
        "procedure_fold_metrics.csv",
        "discovery_procedure_fold_metrics.csv",
    ):
        path = root / name
        if path.exists():
            return path
    candidates = sorted(root.rglob("*.csv"))
    for path in candidates:
        try:
            columns = set(pd.read_csv(path, nrows=0).columns)
        except (pd.errors.EmptyDataError, OSError):
            continue
        if {"candidate", "species", "perturbation", "fold"} <= columns:
            return path
    raise FileNotFoundError("no candidate fold-metrics CSV found")


def normalize_preoutcome_model_pool_artifact(
    input_dir: str | Path,
) -> PreoutcomeArtifactNormalization:
    """Rename known model-pool outer-CV columns after verifying provenance.

    The function mutates only the fold-metrics CSV inside ``input_dir``.  It
    refuses any unknown ``sealed_*``/``n_sealed_*`` column rather than guessing
    whether it is harmless.
    """

    root = Path(input_dir)
    if not root.exists():
        raise FileNotFoundError(root)
    _load_contract(root)
    metrics_path = _find_metrics_file(root)
    metrics = pd.read_csv(metrics_path)

    sealed_like = {
        str(column)
        for column in metrics.columns
        if str(column).lower().startswith("sealed_")
        or str(column).lower().startswith("n_sealed_")
    }
    unknown = sorted(sealed_like - set(LEGACY_OUTER_CV_RENAMES))
    if unknown:
        raise ValueError(
            "unknown sealed-looking fold-metric columns are forbidden: "
            + ", ".join(unknown)
        )

    active_renames = {
        source: target
        for source, target in LEGACY_OUTER_CV_RENAMES.items()
        if source in metrics.columns
    }
    collisions = sorted(
        target for target in active_renames.values() if target in metrics.columns
    )
    if collisions:
        raise ValueError(
            "outer-heldout normalization would overwrite columns: "
            + ", ".join(collisions)
        )

    if active_renames:
        metrics = metrics.rename(columns=active_renames)
        metrics.to_csv(metrics_path, index=False)

    result = PreoutcomeArtifactNormalization(
        metrics_file=str(metrics_path.relative_to(root)),
        renamed_columns=tuple(sorted(active_renames)),
        model_pool_only_contract_verified=True,
    )
    (root / "preoutcome_artifact_normalization.json").write_text(
        json.dumps(result.as_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    args = parser.parse_args()
    normalize_preoutcome_model_pool_artifact(args.input_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
