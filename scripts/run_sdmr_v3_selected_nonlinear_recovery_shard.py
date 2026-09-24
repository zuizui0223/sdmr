#!/usr/bin/env python3
"""Run one learner × split shard of the frozen selected recovery retest."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from sdmr.process_id.known_truth.selected_recovery import (
    run_selected_recovery_retest,
)


_ALLOWED_LEARNERS = {"linear", "quadratic", "hgb"}
_ALLOWED_SPLITS = {"spatial", "random_cell"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--learner", required=True)
    parser.add_argument("--split-mode", required=True)
    args = parser.parse_args()

    learner = str(args.learner)
    split_mode = str(args.split_mode)
    if learner not in _ALLOWED_LEARNERS:
        raise ValueError(f"invalid learner shard: {learner}")
    if split_mode not in _ALLOWED_SPLITS:
        raise ValueError(f"invalid split shard: {split_mode}")

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("status") != "development_only":
        raise ValueError("selected recovery shard requires development_only")
    if learner not in set(config["learners"]):
        raise ValueError("learner shard outside frozen contract")
    if split_mode not in set(config["split_modes"]):
        raise ValueError("split shard outside frozen contract")
    if config["hgb_profile"] != "shallow3":
        raise ValueError("sharded recovery requires shallow3")
    if config["screen_target"]["selection_used_process_recovery"] is not False:
        raise ValueError("screen selection must remain outcome blind")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    odo = config["odo_target"]
    result = run_selected_recovery_retest(
        seeds=tuple(config["seeds"]),
        worlds=tuple(config["worlds"]),
        learners=(learner,),
        split_modes=(split_mode,),
        n_cells=int(config["n_cells"]),
        n_occurrences=int(config["n_occurrences"]),
        n_background=int(config["n_background"]),
        n_splits=int(config["n_splits"]),
        hgb_profile=str(config["hgb_profile"]),
        odo_margin=float(config["margin"]),
        odo_sem_multiplier=float(config["sem_multiplier"]),
        odo_adequacy_floor=float(config["adequacy_floor"]),
        odo_approximation_tolerance=float(odo["approximation_tolerance"]),
        finite_margin=float(config["margin"]),
        finite_sem_multiplier=float(config["sem_multiplier"]),
        finite_adequacy_floor=float(config["adequacy_floor"]),
        logistic_C=float(config["logistic_C"]),
        expected_odo_state_hash=str(odo["state_key_sha256"]),
    )

    result.states.to_csv(outdir / "states.csv", index=False)
    result.metrics.to_csv(outdir / "metrics.csv", index=False)
    summary = {
        "learner": learner,
        "split_mode": split_mode,
        "hgb_profile": config["hgb_profile"],
        "odo_state_hash": result.odo_state_hash,
        "metrics": result.metrics.to_dict(orient="records"),
    }
    (outdir / "summary.json").write_text(
        json.dumps(_clean(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "program": config["program"],
        "execution": "sharded_duplicate_of_v1",
        "learner": learner,
        "split_mode": split_mode,
        "config_sha256": _sha256(config_path),
        "odo_state_hash": result.odo_state_hash,
        "outputs": {
            name: _sha256(outdir / name)
            for name in ("states.csv", "metrics.csv", "summary.json")
        },
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
