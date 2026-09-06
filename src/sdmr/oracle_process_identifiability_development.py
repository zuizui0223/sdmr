"""Development-only oracle observational-identifiability benchmark.

The oracle itself uses only the complete true suitability surface, the frozen
predictor/process representation, and spatial coordinates. Occurrence samples,
learner outputs and generating-process membership are not inputs to oracle
classification. Generating membership is opened only after each oracle result to
quantify how often a generating process is observationally identifiable under the
declared predictor system.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .known_truth_response import infer_true_processes
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .oracle_process_identifiability import (
    ORACLE_CONTESTED,
    ORACLE_CONTRIBUTORY,
    ORACLE_REPLACEABLE,
    ORACLE_REQUIRED,
    ORACLE_UNAVAILABLE,
    oracle_process_identifiability,
)
from .validation import lonlat_to_unit_xyz


ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG = ROOT / "configs" / "oracle_process_identifiability_development.json"
BASE_CONFIG = ROOT / "configs" / "ecological_identification_learner_validation_successor_v2.json"


def _load() -> tuple[dict, dict]:
    dev = json.loads(DEV_CONFIG.read_text(encoding="utf-8"))
    base = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    if dev.get("purpose") != "oracle_observational_identifiability_development_only":
        raise ValueError("wrong oracle development config")
    if dev.get("development_only") is not True:
        raise ValueError("oracle benchmark must remain development-only")
    if dev.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("oracle development cannot become prospective evidence")
    if tuple(dev.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("oracle development families changed")
    seeds = tuple(int(x) for x in dev.get("seeds", ()))
    if seeds != tuple(range(13001, 13011)):
        raise ValueError("oracle development seeds changed")
    if int(dev.get("n_cases", -1)) != len(KNOWN_TRUTH_FAMILIES) * len(seeds):
        raise ValueError("oracle development denominator changed")
    if dev.get("occurrence_outcomes_used_by_oracle") is not False:
        raise ValueError("oracle cannot read occurrence outcomes")
    if dev.get("learner_outputs_used_by_oracle") is not False:
        raise ValueError("oracle cannot read learner outputs")
    if dev.get("generating_process_membership_used_by_oracle") is not False:
        raise ValueError("oracle cannot use generating-process labels for classification")
    return dev, base


def _spatial_groups(environment: pd.DataFrame, config: dict) -> np.ndarray:
    xyz = lonlat_to_unit_xyz(
        environment["longitude"].to_numpy(float),
        environment["latitude"].to_numpy(float),
    )
    n_groups = int(config["n_groups"])
    if n_groups < 2 or n_groups > len(environment):
        raise ValueError("invalid oracle spatial-group count")
    return KMeans(
        n_clusters=n_groups,
        n_init=20,
        random_state=int(config["random_state"]),
    ).fit_predict(xyz)


def _metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    generating = frame["generating_process"].astype(bool).to_numpy()
    identifiable = frame["oracle_identifiable_signal"].astype(bool).to_numpy()
    status = frame["oracle_status"].astype(str)
    true_n = int(generating.sum())
    false_n = int((~generating).sum())
    true_identifiable = int(np.sum(generating & identifiable))
    false_identifiable = int(np.sum((~generating) & identifiable))
    true_replaceable = int(np.sum(generating & status.eq(ORACLE_REPLACEABLE).to_numpy()))
    true_contested = int(np.sum(generating & status.eq(ORACLE_CONTESTED).to_numpy()))
    true_unavailable = int(np.sum(generating & status.eq(ORACLE_UNAVAILABLE).to_numpy()))
    return {
        "generating_process_oracle_identifiable_recall": float(true_identifiable / true_n) if true_n else float("nan"),
        "nongenerating_process_oracle_identifiable_rate": float(false_identifiable / false_n) if false_n else float("nan"),
        "generating_process_replaceable_rate": float(true_replaceable / true_n) if true_n else float("nan"),
        "generating_process_contested_rate": float(true_contested / true_n) if true_n else float("nan"),
        "generating_process_unavailable_rate": float(true_unavailable / true_n) if true_n else float("nan"),
        "n_generating_processes": true_n,
        "n_nongenerating_processes": false_n,
        "n_generating_oracle_identifiable": true_identifiable,
        "n_nongenerating_oracle_identifiable": false_identifiable,
        "n_generating_replaceable": true_replaceable,
        "n_generating_contested": true_contested,
        "n_generating_unavailable": true_unavailable,
        "n_oracle_replaceable": int(status.eq(ORACLE_REPLACEABLE).sum()),
        "n_oracle_contributory": int(status.eq(ORACLE_CONTRIBUTORY).sum()),
        "n_oracle_required": int(status.eq(ORACLE_REQUIRED).sum()),
        "n_oracle_contested": int(status.eq(ORACLE_CONTESTED).sum()),
        "n_oracle_unavailable": int(status.eq(ORACLE_UNAVAILABLE).sum()),
    }


def _fit_family(family: str, dev: dict, base: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    if family not in tuple(dev["families"]):
        raise ValueError(f"family outside oracle development denominator: {family}")
    sim_cfg = base["simulation"]
    predictors = tuple(str(x) for x in base["ecological_predictors"])
    processes = tuple(str(x) for x in base["process_universe"])
    registry = pd.DataFrame(base["process_registry"])[["predictor", "process", "role"]].copy()
    oracle_cfg = dev["oracle"]

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
        environment = simulation.environment.copy()
        groups = _spatial_groups(environment, dev["spatial_grouping"])
        oracle = oracle_process_identifiability(
            environment,
            environment["true_suitability"].to_numpy(float),
            groups,
            registry,
            predictor_universe=predictors,
            process_universe=processes,
            n_splits=int(oracle_cfg["n_splits"]),
            relative_loss_margin=float(oracle_cfg["relative_loss_margin"]),
            sem_multiplier=float(oracle_cfg["sem_multiplier"]),
            baseline_r2_floor=float(oracle_cfg["baseline_r2_floor"]),
            required_r2_ceiling=float(oracle_cfg["required_r2_ceiling"]),
            max_iter=int(oracle_cfg["max_iter"]),
            max_leaf_nodes=int(oracle_cfg["max_leaf_nodes"]),
            min_samples_leaf=int(oracle_cfg["min_samples_leaf"]),
            learning_rate=float(oracle_cfg["learning_rate"]),
            l2_regularization=float(oracle_cfg["l2_regularization"]),
        )

        # Generating membership is opened only after oracle classification.
        generating = set(infer_true_processes(environment))
        p = oracle.process_summary.copy()
        p.insert(0, "seed", seed)
        p.insert(0, "family", family)
        p["generating_process"] = p["process"].astype(str).isin(generating)
        process_rows.append(p)

        baseline = oracle.baseline_summary.iloc[0]
        case_rows.append(
            {
                "family": family,
                "seed": seed,
                "oracle_receipt": oracle.selection_receipt,
                "baseline_complete": bool(baseline["complete"]),
                "baseline_adequate": bool(baseline["baseline_adequate"]),
                "mean_truth_surface_r2": float(baseline["mean_truth_surface_r2"]),
                "lower_truth_surface_r2": float(baseline["lower_truth_surface_r2"]),
                "occurrence_outcomes_used_by_oracle": False,
                "learner_outputs_used_by_oracle": False,
                "generating_membership_used_by_oracle": False,
            }
        )
    return pd.concat(process_rows, ignore_index=True), pd.DataFrame(case_rows)


def _write_bundle(process: pd.DataFrame, cases: pd.DataFrame, output_dir: str | Path, *, dev: dict) -> dict[str, object]:
    family_rows = []
    for family, group in process.groupby("family", sort=True):
        row = {"family": family}
        row.update(_metrics(group))
        family_rows.append(row)
    family_metrics = pd.DataFrame(family_rows)
    oracle_cfg = dev["oracle"]
    decision = {
        "purpose": "oracle_observational_identifiability_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(len(cases)),
        "oracle_threshold_status": str(oracle_cfg["threshold_status"]),
        "relative_loss_margin": float(oracle_cfg["relative_loss_margin"]),
        "baseline_r2_floor": float(oracle_cfg["baseline_r2_floor"]),
        "required_r2_ceiling": float(oracle_cfg["required_r2_ceiling"]),
        "overall_metrics": _metrics(process),
        "product_a_reopened": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    process.sort_values(["family", "seed", "process"], kind="mergesort").to_csv(out / "oracle_process_evaluation.csv", index=False)
    cases.sort_values(["family", "seed"], kind="mergesort").to_csv(out / "oracle_case_summary.csv", index=False)
    family_metrics.to_csv(out / "oracle_family_metrics.csv", index=False)
    (out / "oracle_development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def run_family(family: str, output_dir: str | Path) -> dict[str, object]:
    dev, base = _load()
    process, cases = _fit_family(family, dev, base)
    decision = _write_bundle(process, cases, output_dir, dev=dev)
    decision["family"] = family
    (Path(output_dir) / "oracle_development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    dev, _ = _load()
    root = Path(input_dir)
    process_files = list(root.rglob("oracle_process_evaluation.csv"))
    case_files = list(root.rglob("oracle_case_summary.csv"))
    if len(process_files) != len(dev["families"]) or len(case_files) != len(dev["families"]):
        raise ValueError("oracle aggregate requires exactly one artifact per family")
    process = pd.concat([pd.read_csv(path) for path in process_files], ignore_index=True)
    cases = pd.concat([pd.read_csv(path) for path in case_files], ignore_index=True)
    expected_pairs = {(str(f), int(s)) for f in dev["families"] for s in dev["seeds"]}
    observed_pairs = set(zip(cases["family"].astype(str), cases["seed"].astype(int), strict=True))
    if observed_pairs != expected_pairs or len(cases) != int(dev["n_cases"]):
        raise ValueError("oracle development aggregate denominator changed")
    for column in (
        "occurrence_outcomes_used_by_oracle",
        "learner_outputs_used_by_oracle",
        "generating_membership_used_by_oracle",
    ):
        if cases[column].astype(bool).any():
            raise ValueError(f"oracle information barrier failed: {column}")
    return _write_bundle(process, cases, output_dir, dev=dev)


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
