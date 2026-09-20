#!/usr/bin/env python3
"""Run the burned-development SDMR occurrence-distribution oracle audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from sdmr.process_id.known_truth.occurrence_oracle_audit import (
    run_occurrence_oracle_audit,
)
from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_json(value):
    if isinstance(value, dict):
        return {str(k): _clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "development_only":
        raise ValueError("audit runner requires status=development_only")
    if payload.get("product_a_boundary") != "closed_not_reopened":
        raise ValueError("audit runner cannot reopen Product A")
    if tuple(payload.get("worlds", ())) != KNOWN_TRUTH_WORLDS:
        raise ValueError("audit runner requires exact W1-W8 world order")
    if payload.get("prospective_status") != "not_frozen":
        raise ValueError("audit runner cannot consume prospective settings")
    if payload.get("prospective_validation_seeds") != []:
        raise ValueError("prospective validation seeds must remain unopened")
    if payload.get("fresh_empirical_open") is not False:
        raise ValueError("fresh empirical data must remain unopened")
    if payload.get("finite", {}).get("learners") != ["linear", "quadratic"]:
        raise ValueError("audit runner requires linear and quadratic finite learners")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = _load_contract(config_path)

    truth = config["truth_oracle"]
    occurrence = config["occurrence_oracle"]
    finite = config["finite"]
    result = run_occurrence_oracle_audit(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        truth_margin=float(truth["margin"]),
        truth_sem_multiplier=float(truth["sem_multiplier"]),
        truth_baseline_r2_floor=float(truth["baseline_r2_floor"]),
        truth_required_r2_ceiling=float(truth["required_r2_ceiling"]),
        occurrence_oracle_margin=float(occurrence["margin"]),
        occurrence_oracle_sem_multiplier=float(occurrence["sem_multiplier"]),
        occurrence_oracle_adequacy_floor=float(occurrence["adequacy_floor"]),
        occurrence_oracle_approximation_tolerance=float(
            occurrence["approximation_tolerance"]
        ),
        finite_margin=float(finite["margin"]),
        finite_sem_multiplier=float(finite["sem_multiplier"]),
        finite_adequacy_floor=float(finite["adequacy_floor"]),
        logistic_C=float(finite["logistic_C"]),
    )

    frames = {
        "truth_states.csv": result.truth_states,
        "occurrence_oracle_states.csv": result.occurrence_oracle_states,
        "occurrence_oracle_evidence.csv": result.occurrence_oracle_evidence,
        "finite_states.csv": result.finite_states,
        "identifiability_crosswalk.csv": result.crosswalk,
        "by_world.csv": result.by_world,
        "by_process.csv": result.by_process,
    }
    for filename, frame in frames.items():
        frame.to_csv(outdir / filename, index=False)

    metrics_path = outdir / "metrics.json"
    metrics_path.write_text(
        json.dumps(_clean_json(result.metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    output_names = list(frames) + ["metrics.json"]
    manifest = {
        "program": config["program"],
        "status": "development_only",
        "product_a_boundary": "closed_not_reopened",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "seeds": config["seeds"],
        "worlds": config["worlds"],
        "outputs": {name: _sha256(outdir / name) for name in output_names},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
