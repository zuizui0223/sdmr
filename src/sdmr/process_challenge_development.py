"""Development-only known-truth evaluator for the process challenge learner.

This module is explicitly not a prospective performance test. It uses fresh
post-outcome development seeds to diagnose whether the v3 estimands recover
true generating processes better than the closed v2 necessity-only learner.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .known_truth_response import infer_true_processes
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .model import ModelSpec
from .process_challenge_learner import (
    CONTRIBUTORY,
    REQUIRED,
    fit_process_challenge_learner,
)
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition


ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG = ROOT / "configs" / "process_challenge_v3_development.json"
BASE_CONFIG = ROOT / "configs" / "ecological_identification_learner_validation_successor_v2.json"


def _load() -> tuple[dict, dict]:
    dev = json.loads(DEV_CONFIG.read_text(encoding="utf-8"))
    base = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    if dev.get("purpose") != "process_challenge_v3_development_only":
        raise ValueError("wrong v3 development config")
    if dev.get("development_only") is not True:
        raise ValueError("v3 development denominator must remain development-only")
    if dev.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("development denominator cannot become prospective evidence")
    if tuple(dev.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v3 development family denominator changed")
    seeds = tuple(int(x) for x in dev.get("seeds", ()))
    if seeds != tuple(range(13001, 13011)):
        raise ValueError("v3 development seeds changed")
    if int(dev.get("n_cases", -1)) != len(KNOWN_TRUTH_FAMILIES) * len(seeds):
        raise ValueError("v3 development case denominator changed")
    return dev, base


def _specs(base: dict) -> tuple[ModelSpec, ...]:
    return tuple(
        ModelSpec(
            C=float(row["C"]),
            degree=int(row["degree"]),
            penalty=str(row["penalty"]),
            random_state=int(row["random_state"]),
        )
        for row in base["learner"]["model_specs"]
    )


def _truth_for_family(family: str) -> set[str]:
    frame = pd.DataFrame(
        {
            "scenario": [str(family)],
            "temperature": [0.0],
            "water": [0.0],
            "soil": [0.0],
        }
    )
    return set(infer_true_processes(frame))


def _metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    expected = frame["expected_true_process"].astype(bool).to_numpy()
    detected = frame["process_detected"].astype(bool).to_numpy()
    required = frame["status"].astype(str).eq(REQUIRED).to_numpy()
    true_n = int(expected.sum())
    false_n = int((~expected).sum())
    tp = int(np.sum(expected & detected))
    fp = int(np.sum((~expected) & detected))
    false_required = int(np.sum((~expected) & required))
    return {
        "true_process_detection_recall": float(tp / true_n) if true_n else float("nan"),
        "false_process_detection_rate": float(fp / false_n) if false_n else float("nan"),
        "false_required_rate": float(false_required / false_n) if false_n else float("nan"),
        "n_true_processes": true_n,
        "n_false_processes": false_n,
        "n_detected_true_processes": tp,
        "n_detected_false_processes": fp,
        "n_false_required": false_required,
        "n_replaceable": int(frame["status"].astype(str).eq("replaceable_under_evidence_contract").sum()),
        "n_contributory": int(frame["status"].astype(str).eq(CONTRIBUTORY).sum()),
        "n_required": int(frame["status"].astype(str).eq(REQUIRED).sum()),
        "n_unresolved": int(frame["status"].astype(str).eq("unresolved").sum()),
    }


def run(output_dir: str | Path) -> dict[str, object]:
    dev, base = _load()
    sim_cfg = base["simulation"]
    learner_cfg = base["learner"]
    ecological_predictors = tuple(str(x) for x in base["ecological_predictors"])
    observation_predictors = tuple(str(x) for x in base["observation_predictors"])
    process_universe = tuple(str(x) for x in base["process_universe"])
    registry = pd.DataFrame(base["process_registry"])[["predictor", "process", "role"]].copy()

    process_rows: list[pd.DataFrame] = []
    case_rows: list[dict[str, object]] = []
    for family in tuple(dev["families"]):
        truth = _truth_for_family(family)
        for seed in tuple(int(x) for x in dev["seeds"]):
            simulation = simulate_known_truth_plant_niche(
                family,
                seed=seed,
                n_cells=int(sim_cfg["n_cells"]),
                n_occurrences=int(sim_cfg["n_occurrences"]),
                n_target_group=int(sim_cfg["n_target_group"]),
            )
            occurrences, background = _selection_frames(simulation, family=family, seed=seed)
            split = freeze_occurrence_answer_check_split(
                occurrences,
                id_col="occurrence_id",
                lon_col="longitude",
                lat_col="latitude",
                n_blocks=int(sim_cfg["outer_n_blocks"]),
                holdout_fraction=float(sim_cfg["answer_check_fraction"]),
                random_state=int(sim_cfg["outer_random_state_offset"]) + seed,
            )
            model_presence = split.model_pool(occurrences)
            inner = make_spatial_partition(
                model_presence["longitude"].to_numpy(float),
                model_presence["latitude"].to_numpy(float),
                background["longitude"].to_numpy(float),
                background["latitude"].to_numpy(float),
                n_blocks=int(sim_cfg["inner_n_blocks"]),
                holdout_fraction=0.20,
                random_state=int(sim_cfg["inner_random_state_offset"]) + seed,
            )
            fit = fit_process_challenge_learner(
                model_presence,
                background,
                inner.presence_blocks,
                inner.background_blocks,
                ecological_predictors=ecological_predictors,
                observation_predictors=observation_predictors,
                process_registry=registry,
                process_universe=process_universe,
                model_specs=_specs(base),
                n_splits=int(sim_cfg["inner_n_splits"]),
                chance_score=float(learner_cfg["chance_score"]),
                minimum_margin=float(learner_cfg["minimum_margin"]),
                sem_multiplier=float(learner_cfg["sem_multiplier"]),
                relative_noninferiority_margin=float(dev["relative_noninferiority_margin"]),
                relative_sem_multiplier=float(dev["relative_sem_multiplier"]),
                observation_signal_chance=float(learner_cfg["observation_signal_chance"]),
                observation_signal_margin=float(learner_cfg["observation_signal_margin"]),
                observation_signal_sem_multiplier=float(learner_cfg["observation_signal_sem_multiplier"]),
                observation_weight_truncation_quantile=float(learner_cfg["observation_weight_truncation_quantile"]),
                observation_weight_probability_epsilon=float(learner_cfg["observation_weight_probability_epsilon"]),
                occurrence_split=split,
                occurrence_id_col="occurrence_id",
            )
            p = fit.process_summary.copy()
            p.insert(0, "seed", seed)
            p.insert(0, "family", family)
            p["expected_true_process"] = p["process"].astype(str).isin(truth)
            process_rows.append(p)
            case_rows.append(
                {
                    "family": family,
                    "seed": seed,
                    "selection_receipt": fit.selection_receipt,
                    "prediction_model_label": fit.prediction_model_label,
                    "n_model_pool_occurrences": len(model_presence),
                    "n_answer_check_occurrences": len(split.answer_check_ids),
                    "answer_check_used_in_fit": False,
                }
            )

    process = pd.concat(process_rows, ignore_index=True)
    cases = pd.DataFrame(case_rows)
    overall = _metrics(process)
    family_rows = []
    for family, group in process.groupby("family", sort=True):
        row = {"family": family}
        row.update(_metrics(group))
        family_rows.append(row)
    family_metrics = pd.DataFrame(family_rows)
    decision = {
        "purpose": "process_challenge_v3_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(dev["n_cases"]),
        "relative_noninferiority_margin": float(dev["relative_noninferiority_margin"]),
        "overall_metrics": overall,
        "product_a_reopened": False,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    process.to_csv(out / "process_evaluation.csv", index=False)
    cases.to_csv(out / "case_summary.csv", index=False)
    family_metrics.to_csv(out / "family_metrics.csv", index=False)
    (out / "development_decision.json").write_text(
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
