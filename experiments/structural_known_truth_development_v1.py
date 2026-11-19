"""Run only burned development seeds for eight structural known-truth worlds.

Never open prospective seeds here. No original forest, beetle or FIA records.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from sdmr.structural_known_truth_v1 import (
    WORLDS, generate_forest_world, score_forest_world
)
from sdmr.structural_process_gate_v1 import assess_forest_development

DEV_SEEDS = (1201, 1202, 1203)


def run_development(seeds: tuple[int, ...]) -> dict:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("unique nonempty seed list required")
    if not set(seeds).issubset(DEV_SEEDS):
        raise ValueError("only burned development seeds 1201–1203 are authorized")
    cases = []
    for seed in seeds:
        for world in WORLDS:
            score = score_forest_world(generate_forest_world(world, seed))
            record = asdict(score)
            gate = assess_forest_development(score)
            record["process_state"] = gate.state
            record["process_reason"] = gate.reason
            record["causal_process_identified"] = gate.causal_process_identified
            record["empirical_promotion_authorized"] = gate.empirical_promotion_authorized
            cases.append(record)
    return {
        "schema": "sdmr.structural_known_truth.development.v1",
        "promotion": "not_authorized",
        "empirical_data_opened": False,
        "prospective_seeds_opened": False,
        "seeds": list(seeds),
        "worlds": list(WORLDS),
        "cases": cases,
        "n_cases": len(cases),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEV_SEEDS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_development(tuple(args.seeds))
    encoded = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print("DEVELOPMENT_ONLY", result["n_cases"], "SHA256", sha256(encoded).hexdigest())
    print("No real biology / prospective seeds / process promotion")
    for world in WORLDS:
        cases = [r for r in result["cases"] if r["world"] == world]
        def mean(field):
            return sum(float(row[field]) for row in cases) / len(cases)
        print(
            "WORLD", world,
            "SPATIAL", round(mean("spatial_gain"), 6),
            "TEMPORAL", round(mean("temporal_gain"), 6),
            "TEMP_CLOSURE", round(mean("temporal_closure_gain"), 6),
            "CLOSURE", round(mean("closure_gain"), 6),
            "BEETLE", round(mean("beetle_gain"), 6),
            "FULL_NULL", round(mean("full_vs_null_gain"), 6),
            "OBSERVED", [r["n_sites_observed"] for r in cases],
            "GATES", [r["process_state"] for r in cases],
        )


if __name__ == "__main__":
    main()
