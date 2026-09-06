"""Development-only known-truth evaluator for process challenge v3/v3.1.

This module is explicitly not a prospective performance test. It uses fresh
post-outcome development seeds to diagnose both the v3 challenge signal and the
v3.1 shared-carrier attribution layer. Model fitting remains restricted to the
model-pool occurrences; shared-carrier auditing uses predictor/background rows
only. Generating-process truth is used only to score the resulting development
outputs.
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
from .process_challenge_learner import CONTRIBUTORY, REQUIRED, fit_process_challenge_learner
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .shared_carrier_attribution import CONTESTED_SHARED, fit_shared_carrier_attribution
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
    attribution = dev.get("shared_carrier_attribution", {})
    if attribution.get("threshold_status") != (
        "post_outcome_development_heuristic_not_prospectively_validated"
    ):
        raise ValueError("v3.1 attribution thresholds lost development-only status")
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
    challenge_detected = (
        frame["challenge_signal_detected"].astype(bool).to_numpy()
        if "challenge_signal_detected" in frame.columns
        else frame["process_detected"].astype(bool).to_numpy()
    )
    unique_detected = (
        frame["unique_process_evidence"].astype(bool).to_numpy()
        if "unique_process_evidence" in frame.columns
        else challenge_detected
    )
    attribution_status = (
        frame["attribution_status"].astype(str)
        if "attribution_status" in frame.columns
        else frame["status"].astype(str)
    )
    required = attribution_status.eq(REQUIRED).to_numpy()
    contested = attribution_status.eq(CONTESTED_SHARED).to_numpy()

    true_n = int(expected.sum())
    false_n = int((~expected).sum())
    challenge_tp = int(np.sum(expected & challenge_detected))
    challenge_fp = int(np.sum((~expected) & challenge_detected))
    unique_tp = int(np.sum(expected & unique_detected))
    unique_fp = int(np.sum((~expected) & unique_detected))
    false_required = int(np.sum((~expected) & required))
    true_contested = int(np.sum(expected & contested))
    false_contested = int(np.sum((~expected) & contested))

    return {
        # Legacy v3 names retained for direct comparison with the first
        # development run. They refer to the challenge signal, not v3.1 unique
        # attribution.
        "true_process_detection_recall": float(challenge_tp / true_n) if true_n else float("nan"),
        "false_process_detection_rate": float(challenge_fp / false_n) if false_n else float("nan"),
        "true_process_challenge_recall": float(challenge_tp / true_n) if true_n else float("nan"),
        "false_process_challenge_rate": float(challenge_fp / false_n) if false_n else float("nan"),
        "true_process_unique_attribution_recall": float(unique_tp / true_n) if true_n else float("nan"),
        "false_process_unique_attribution_rate": float(unique_fp / false_n) if false_n else float("nan"),
        "false_required_rate": float(false_required / false_n) if false_n else float("nan"),
        "true_process_contested_rate": float(true_contested / true_n) if true_n else float("nan"),
        "false_process_contested_rate": float(false_contested / false_n) if false_n else float("nan"),
        "n_true_processes": true_n,
        "n_false_processes": false_n,
        "n_challenge_detected_true_processes": challenge_tp,
        "n_challenge_detected_false_processes": challenge_fp,
        "n_unique_true_processes": unique_tp,
        "n_unique_false_processes": unique_fp,
        "n_false_required": false_required,
        "n_true_contested": true_contested,
        "n_false_contested": false_contested,
        "n_replaceable": int(attribution_status.eq("replaceable_under_evidence_contract").sum()),
        "n_contributory": int(attribution_status.eq(CONTRIBUTORY).sum()),
        "n_required": int(attribution_status.eq(REQUIRED).sum()),
        "n_contested_shared": int(contested.sum()),
        "n_unresolved": int(attribution_status.eq("unresolved").sum()),
    }


def _fit_family(family: str, dev: dict, base: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    if family not in tuple(dev["families"]):
        raise ValueError(f"family is outside v3 development denominator: {family}")
    sim_cfg = base["simulation"]
    learner_cfg = base["learner"]
    attr_cfg = dev["shared_carrier_attribution"]
    ecological_predictors = tuple(str(x) for x in base["ecological_predictors"])
    observation_predictors = tuple(str(x) for x in base["observation_predictors"])
    process_universe = tuple(str(x) for x in base["process_universe"])
    registry = pd.DataFrame(base["process_registry"])[["predictor", "process", "role"]].copy()
    truth = _truth_for_family(family)

    process_rows: list[pd.DataFrame] = []
    case_rows: list[dict[str, object]] = []
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

        # v3.1 attribution uses predictor/background rows only. It receives no
        # occurrence labels, suitability values, answer-check rows or truth.
        attribution = fit_shared_carrier_attribution(
            fit,
            background.loc[:, list(ecological_predictors)],
            registry,
            groups=inner.background_blocks,
            n_splits=int(attr_cfg["proxy_audit_n_splits"]),
            degree=int(attr_cfg["proxy_audit_degree"]),
            minimum_univariate_cv_r2=float(attr_cfg["minimum_univariate_cv_r2"]),
            minimum_abs_spearman=float(attr_cfg["minimum_abs_spearman"]),
        )

        p = attribution.process_summary.copy()
        p.insert(0, "seed", seed)
        p.insert(0, "family", family)
        p["expected_true_process"] = p["process"].astype(str).isin(truth)
        process_rows.append(p)
        case_rows.append(
            {
                "family": family,
                "seed": seed,
                "selection_receipt": fit.selection_receipt,
                "attribution_receipt": attribution.selection_receipt,
                "prediction_model_label": fit.prediction_model_label,
                "n_model_pool_occurrences": len(model_presence),
                "n_answer_check_occurrences": len(split.answer_check_ids),
                "answer_check_used_in_fit": False,
                "proxy_audit_used_outcome": False,
                "proxy_audit_modified_registry": False,
            }
        )
    return pd.concat(process_rows, ignore_index=True), pd.DataFrame(case_rows)


def _write_bundle(process: pd.DataFrame, cases: pd.DataFrame, output_dir: str | Path, *, n_cases: int, dev: dict) -> dict[str, object]:
    overall = _metrics(process)
    family_rows = []
    for family, group in process.groupby("family", sort=True):
        row = {"family": family}
        row.update(_metrics(group))
        family_rows.append(row)
    family_metrics = pd.DataFrame(family_rows)
    attr_cfg = dev["shared_carrier_attribution"]
    decision = {
        "purpose": "process_challenge_v31_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(n_cases),
        "relative_noninferiority_margin": float(dev["relative_noninferiority_margin"]),
        "shared_carrier_minimum_univariate_cv_r2": float(attr_cfg["minimum_univariate_cv_r2"]),
        "shared_carrier_minimum_abs_spearman": float(attr_cfg["minimum_abs_spearman"]),
        "shared_carrier_threshold_status": str(attr_cfg["threshold_status"]),
        "overall_metrics": overall,
        "product_a_reopened": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    process.sort_values(["family", "seed", "process"], kind="mergesort").to_csv(out / "process_evaluation.csv", index=False)
    cases.sort_values(["family", "seed"], kind="mergesort").to_csv(out / "case_summary.csv", index=False)
    family_metrics.to_csv(out / "family_metrics.csv", index=False)
    (out / "development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def run_family(family: str, output_dir: str | Path) -> dict[str, object]:
    dev, base = _load()
    process, cases = _fit_family(family, dev, base)
    decision = _write_bundle(process, cases, output_dir, n_cases=len(cases), dev=dev)
    decision["family"] = family
    (Path(output_dir) / "development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    dev, _ = _load()
    root = Path(input_dir)
    process_files = list(root.rglob("process_evaluation.csv"))
    case_files = list(root.rglob("case_summary.csv"))
    if len(process_files) != len(dev["families"]) or len(case_files) != len(dev["families"]):
        raise ValueError("aggregate requires exactly one artifact per development family")
    process = pd.concat([pd.read_csv(path) for path in process_files], ignore_index=True)
    cases = pd.concat([pd.read_csv(path) for path in case_files], ignore_index=True)
    expected_pairs = {(str(f), int(s)) for f in dev["families"] for s in dev["seeds"]}
    observed_pairs = set(zip(cases["family"].astype(str), cases["seed"].astype(int), strict=True))
    if observed_pairs != expected_pairs or len(cases) != int(dev["n_cases"]):
        raise ValueError("development aggregate denominator changed")
    if cases["answer_check_used_in_fit"].astype(bool).any():
        raise ValueError("sealed answer-check leaked into development fit")
    if cases["proxy_audit_used_outcome"].astype(bool).any():
        raise ValueError("outcome leaked into shared-carrier proxy audit")
    if cases["proxy_audit_modified_registry"].astype(bool).any():
        raise ValueError("shared-carrier proxy audit modified the process registry")
    return _write_bundle(process, cases, output_dir, n_cases=int(dev["n_cases"]), dev=dev)


def run(output_dir: str | Path) -> dict[str, object]:
    dev, base = _load()
    process_parts = []
    case_parts = []
    for family in dev["families"]:
        process, cases = _fit_family(str(family), dev, base)
        process_parts.append(process)
        case_parts.append(cases)
    return _write_bundle(
        pd.concat(process_parts, ignore_index=True),
        pd.concat(case_parts, ignore_index=True),
        output_dir,
        n_cases=int(dev["n_cases"]),
        dev=dev,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--family", choices=KNOWN_TRUTH_FAMILIES)
    parser.add_argument("--input-dir")
    args = parser.parse_args(argv)
    if args.family and args.input_dir:
        raise ValueError("choose either --family or --input-dir")
    if args.family:
        decision = run_family(args.family, args.output_dir)
    elif args.input_dir:
        decision = aggregate(args.input_dir, args.output_dir)
    else:
        decision = run(args.output_dir)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
