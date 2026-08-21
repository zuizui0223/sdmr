"""Merge three M-specific v2.6 empirical model-pool worker artifacts for one taxon.

This is a computational sharding adapter only. It requires the three frozen M
specifications, identical taxon/seed/admissible predictor sets, and sealed-blind
worker contracts, then reconstructs the original taxon-level worker artifact
shape consumed by the pretruth aggregate and final-fit stages.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v2_6_empirical_model_pool_worker import M_NAMES


def _concat_csv(paths: list[Path], name: str) -> pd.DataFrame:
    """Concatenate shard CSVs while treating blank optional tables as empty.

    Some valid worker diagnostics (notably ``selection_trace.csv``) have no rows
    for an M shard.  ``DataFrame().to_csv`` serializes that state as a blank
    line, which raises ``pandas.errors.EmptyDataError`` on read.  A blank table is
    absence of optional diagnostic rows, not missing scientific evidence, so it
    is skipped here.  Nonblank malformed CSVs still fail normally, and required
    predictor-admissibility ledgers are read separately and remain fail-closed.
    """

    frames = []
    for path in paths:
        file = path / name
        if not file.exists():
            continue
        if not file.read_text(encoding="utf-8").strip():
            continue
        frame = pd.read_csv(file)
        if not frame.empty:
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def merge_m_workers(*, worker_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(worker_root)
    workers: list[tuple[Path, dict]] = []
    for path in sorted(root.rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") == "product_a_v2_6_empirical_model_pool_worker":
            workers.append((path.parent, payload))
    if len(workers) != 3:
        raise ValueError(f"expected exactly 3 M-specific workers, found {len(workers)}")

    contracts = [payload for _, payload in workers]
    if any(c.get("sealed_occurrence_environment_read") is not False for c in contracts):
        raise ValueError("cannot merge a worker that opened sealed environments")
    taxa = {str(c["taxon"]) for c in contracts}
    seeds = {int(c["part_seed"]) for c in contracts}
    indices = {int(c["taxon_index"]) for c in contracts}
    if len(taxa) != 1 or len(seeds) != 1 or len(indices) != 1:
        raise ValueError("M-specific workers disagree on taxon, taxon_index, or part_seed")
    observed_m = [tuple(str(x) for x in c.get("M_specs", [])) for c in contracts]
    flat_m = sorted(x[0] for x in observed_m if len(x) == 1)
    if flat_m != sorted(M_NAMES) or any(len(x) != 1 for x in observed_m):
        raise ValueError(f"M-specific workers do not cover the frozen M set exactly: {observed_m}")
    predictor_sets = {tuple(str(x) for x in c.get("admissible_predictors", [])) for c in contracts}
    if len(predictor_sets) != 1:
        raise ValueError("M-specific workers disagree on the 3-M-derived admissible predictor set")

    paths = [path for path, _ in workers]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in ("base_fold_metrics.csv", "knockout_fold_metrics.csv", "worker_status.csv", "selection_trace.csv"):
        _concat_csv(paths, name).to_csv(out / name, index=False)

    coverage = [pd.read_csv(path / "predictor_coverage.csv") for path in paths]
    canonical = coverage[0].sort_values(list(coverage[0].columns), kind="mergesort").reset_index(drop=True)
    for frame in coverage[1:]:
        other = frame.sort_values(list(frame.columns), kind="mergesort").reset_index(drop=True)
        if not canonical.equals(other):
            raise ValueError("M-specific workers disagree on predictor admissibility ledger")
    coverage[0].to_csv(out / "predictor_coverage.csv", index=False)

    predictors = next(iter(predictor_sets))
    merged = {
        "purpose": "product_a_v2_6_empirical_model_pool_worker",
        "taxon": next(iter(taxa)),
        "taxon_index": next(iter(indices)),
        "part_seed": next(iter(seeds)),
        "M_specs": list(M_NAMES),
        "n_admissible_predictors": len(predictors),
        "admissible_predictors": list(predictors),
        "computational_sharding": "taxon_x_M_then_exact_merge",
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "old_real_model_outputs_reused": False,
        "old_real_sealed_outcomes_read": False,
    }
    (out / "contract.json").write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    merge_m_workers(worker_root=args.worker_root, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
