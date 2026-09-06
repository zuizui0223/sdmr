"""Development audit of residual process information using predictor data only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .known_truth_scenarios import simulate_known_truth_plant_niche
from .process_proxy_audit import audit_process_proxy_reconstructability
from .prospective_identification_validation import _selection_frames


ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG = ROOT / "configs" / "process_challenge_v3_development.json"
BASE_CONFIG = ROOT / "configs" / "ecological_identification_learner_validation_successor_v2.json"


def run(output_dir: str | Path) -> dict[str, object]:
    dev = json.loads(DEV_CONFIG.read_text(encoding="utf-8"))
    base = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    if dev.get("development_only") is not True or dev.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("proxy audit runner requires the development-only denominator")

    predictors = tuple(str(x) for x in base["ecological_predictors"])
    processes = tuple(str(x) for x in base["process_universe"])
    registry = pd.DataFrame(base["process_registry"])[["predictor", "process", "role"]].copy()
    sim_cfg = base["simulation"]

    process_parts: list[pd.DataFrame] = []
    candidate_parts: list[pd.DataFrame] = []
    for family in dev["families"]:
        for seed in dev["seeds"]:
            simulation = simulate_known_truth_plant_niche(
                str(family),
                seed=int(seed),
                n_cells=int(sim_cfg["n_cells"]),
                n_occurrences=int(sim_cfg["n_occurrences"]),
                n_target_group=int(sim_cfg["n_target_group"]),
            )
            _, background = _selection_frames(simulation, family=str(family), seed=int(seed))
            coordinates = background[["longitude", "latitude"]].to_numpy(float)
            groups = KMeans(
                n_clusters=int(sim_cfg["inner_n_blocks"]),
                random_state=0,
                n_init=10,
            ).fit_predict(coordinates)
            audit = audit_process_proxy_reconstructability(
                background,
                registry,
                process_universe=processes,
                predictor_universe=predictors,
                groups=groups,
                n_splits=4,
                degree=2,
            )
            p = audit.process_summary.copy()
            p.insert(0, "seed", int(seed))
            p.insert(0, "family", str(family))
            c = audit.candidate_summary.copy()
            c.insert(0, "seed", int(seed))
            c.insert(0, "family", str(family))
            process_parts.append(p)
            candidate_parts.append(c)

    process = pd.concat(process_parts, ignore_index=True)
    candidate = pd.concat(candidate_parts, ignore_index=True)
    summary = (
        process.groupby("process", as_index=False)
        .agg(
            mean_joint_reconstruction_cv_r2=("mean_anchor_reconstruction_cv_r2", "mean"),
            median_joint_reconstruction_cv_r2=("mean_anchor_reconstruction_cv_r2", "median"),
            max_joint_reconstruction_cv_r2=("max_anchor_reconstruction_cv_r2", "max"),
        )
        .sort_values("mean_joint_reconstruction_cv_r2", ascending=False, kind="mergesort")
    )
    candidates = (
        candidate.groupby(
            ["target_process", "candidate_predictor", "current_processes", "suggested_role"],
            as_index=False,
        )
        .agg(
            mean_univariate_cv_r2=("univariate_cv_r2", "mean"),
            median_univariate_cv_r2=("univariate_cv_r2", "median"),
            mean_abs_spearman=("abs_spearman", "mean"),
            median_abs_spearman=("abs_spearman", "median"),
            n_case_anchor_rows=("univariate_cv_r2", "size"),
        )
        .sort_values(
            ["target_process", "mean_univariate_cv_r2", "mean_abs_spearman", "candidate_predictor"],
            ascending=[True, False, False, True],
            kind="mergesort",
        )
    )
    decision = {
        "purpose": "process_proxy_audit_v3_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(dev["n_cases"]),
        "outcome_used_by_proxy_audit": False,
        "registry_modified_by_proxy_audit": False,
        "auto_frozen_proxy_links": 0,
        "product_a_reopened": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    process.to_csv(out / "process_reconstructability_by_case.csv", index=False)
    candidate.to_csv(out / "proxy_candidates_by_case.csv", index=False)
    summary.to_csv(out / "process_reconstructability_summary.csv", index=False)
    candidates.to_csv(out / "proxy_candidate_summary.csv", index=False)
    (out / "proxy_audit_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    decision = run(args.output_dir)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
