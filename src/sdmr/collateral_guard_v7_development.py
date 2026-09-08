"""Development-only evaluator for v7 collateral-information guarding.

The 15001-15010 generating-process labels were already opened by the frozen v6
prospective endpoint. They are therefore consumed and are used here only to
diagnose the v7 successor. No metric from this module is eligible for a
prospective performance claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .collateral_guard_process_challenge import fit_collateral_guard_process_challenge
from .known_truth_response import infer_true_processes
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .model import ModelSpec
from .process_challenge_learner import CONTRIBUTORY
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition


ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG = ROOT / "configs" / "collateral_information_guard_v7_development.json"
V6_CONFIG = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation_successor_v2.json"


def _load() -> tuple[dict, dict]:
    dev = json.loads(DEV_CONFIG.read_text(encoding="utf-8"))
    v6 = json.loads(V6_CONFIG.read_text(encoding="utf-8"))
    if dev.get("purpose") != "collateral_information_guard_v7_development_only":
        raise ValueError("wrong v7 development contract")
    if dev.get("development_only") is not True or dev.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v7 consumed denominator must remain development-only")
    if tuple(dev.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v7 development family denominator changed")
    seeds = tuple(int(x) for x in dev.get("consumed_seed_denominator", ()))
    if seeds != tuple(range(15001, 15011)):
        raise ValueError("v7 development must use exactly the consumed 15001-15010 denominator")
    if tuple(v6.get("seeds", ())) != seeds:
        raise ValueError("v7 development denominator no longer matches frozen v6 endpoint")
    if dev.get("post_outcome_threshold_relaxation_allowed") is not False:
        raise ValueError("v7 development threshold relaxation must remain forbidden")
    return dev, v6


def _specs(v6: dict) -> tuple[ModelSpec, ...]:
    return tuple(
        ModelSpec(
            C=float(x["C"]),
            degree=int(x["degree"]),
            penalty=str(x["penalty"]),
            random_state=int(x["random_state"]),
        )
        for x in v6["model_specs"]
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


def _binary_metrics(frame: pd.DataFrame, detected_col: str) -> dict[str, float | int]:
    truth = frame["expected_true_process"].astype(bool).to_numpy()
    detected = frame[detected_col].astype(bool).to_numpy()
    tp = int(np.sum(truth & detected))
    fp = int(np.sum((~truth) & detected))
    fn = int(np.sum(truth & (~detected)))
    tn = int(np.sum((~truth) & (~detected)))
    pos_denom = 2 * tp + fp + fn
    neg_denom = 2 * tn + fn + fp
    pos_f1 = float(2 * tp / pos_denom) if pos_denom else float("nan")
    neg_f1 = float(2 * tn / neg_denom) if neg_denom else float("nan")
    return {
        "true_process_recall": float(tp / int(truth.sum())) if truth.any() else float("nan"),
        "false_process_detection_rate": float(fp / int((~truth).sum())) if (~truth).any() else float("nan"),
        "macro_f1": float(np.nanmean([pos_f1, neg_f1])),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "n_true_processes": int(truth.sum()),
        "n_false_processes": int((~truth).sum()),
    }


def _fit_family(family: str, dev: dict, v6: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sim = v6["simulation"]
    learner = v6["learner"]
    ecological = tuple(str(x) for x in v6["ecological_predictors"])
    observation = tuple(str(x) for x in v6["observation_predictors"])
    processes = tuple(str(x) for x in v6["process_universe"])
    registry = pd.DataFrame(v6["process_registry"])[["predictor", "process", "role"]].copy()
    truth = _truth_for_family(family)

    process_parts: list[pd.DataFrame] = []
    audit_parts: list[pd.DataFrame] = []
    route_parts: list[pd.DataFrame] = []
    case_rows: list[dict[str, object]] = []
    for seed in tuple(int(x) for x in dev["consumed_seed_denominator"]):
        simulation = simulate_known_truth_plant_niche(
            family,
            seed=seed,
            n_cells=int(sim["n_cells"]),
            n_occurrences=int(sim["n_occurrences"]),
            n_target_group=int(sim["n_target_group"]),
        )
        occurrences, background = _selection_frames(simulation, family=family, seed=seed)
        split = freeze_occurrence_answer_check_split(
            occurrences,
            id_col="occurrence_id",
            lon_col="longitude",
            lat_col="latitude",
            n_blocks=int(sim["outer_n_blocks"]),
            holdout_fraction=float(sim["answer_check_fraction"]),
            random_state=int(sim["outer_random_state_offset"]) + seed,
        )
        model_presence = split.model_pool(occurrences)
        inner = make_spatial_partition(
            model_presence["longitude"].to_numpy(float),
            model_presence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float),
            background["latitude"].to_numpy(float),
            n_blocks=int(sim["inner_n_blocks"]),
            holdout_fraction=0.20,
            random_state=int(sim["inner_random_state_offset"]) + seed,
        )
        fit = fit_collateral_guard_process_challenge(
            model_presence,
            background,
            inner.presence_blocks,
            inner.background_blocks,
            ecological_predictors=ecological,
            observation_predictors=observation,
            process_registry=registry,
            process_universe=processes,
            model_specs=_specs(v6),
            n_splits=int(sim["inner_n_splits"]),
            chance_score=float(learner["chance_score"]),
            minimum_margin=float(learner["minimum_margin"]),
            sem_multiplier=float(learner["sem_multiplier"]),
            relative_noninferiority_margin=float(learner["relative_noninferiority_margin"]),
            relative_sem_multiplier=float(learner["relative_sem_multiplier"]),
            density_noninferiority_margin=float(learner["density_noninferiority_margin"]),
            density_sem_multiplier=float(learner["density_sem_multiplier"]),
            density_probability_epsilon=float(learner["density_probability_epsilon"]),
            purge_degree=int(learner["purge_degree"]),
            purge_ridge_alpha=float(learner["purge_ridge_alpha"]),
            collateral_sem_multiplier=float(dev["collateral_guard"]["sem_multiplier"]),
            observation_signal_chance=float(learner["observation_signal_chance"]),
            observation_signal_margin=float(learner["observation_signal_margin"]),
            observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
            observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
            observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
            occurrence_split=split,
            occurrence_id_col="occurrence_id",
        )
        p = fit.process_summary.copy()
        p.insert(0, "seed", seed)
        p.insert(0, "family", family)
        p["expected_true_process"] = p["process"].astype(str).isin(truth)
        p["v7_detected"] = p["status"].astype(str).eq(CONTRIBUTORY)
        p["v7_unguarded_detected"] = p["process_specific_unguarded_status"].astype(str).eq(CONTRIBUTORY)
        p["v6_detected"] = p["v6_status"].astype(str).eq(CONTRIBUTORY)
        process_parts.append(p)

        a = fit.specificity_audit.copy()
        a.insert(0, "seed", seed)
        a.insert(0, "family", family)
        audit_parts.append(a)
        r = fit.process_specific_route_summary.copy()
        r.insert(0, "seed", seed)
        r.insert(0, "family", family)
        route_parts.append(r)
        case_rows.append(
            {
                "family": family,
                "seed": seed,
                "selection_receipt": fit.selection_receipt,
                "n_model_pool_occurrences": int(len(model_presence)),
                "n_answer_check_occurrences": int(len(split.answer_check_ids)),
                "generating_truth_used_by_purge_or_guard": False,
                "consumed_truth_opened_only_for_development_scoring": True,
            }
        )
    return (
        pd.concat(process_parts, ignore_index=True),
        pd.concat(audit_parts, ignore_index=True),
        pd.concat(route_parts, ignore_index=True),
        pd.DataFrame(case_rows),
    )


def _write(process: pd.DataFrame, audit: pd.DataFrame, routes: pd.DataFrame, cases: pd.DataFrame, output_dir: str | Path, dev: dict) -> dict[str, object]:
    v7 = _binary_metrics(process, "v7_detected")
    unguarded = _binary_metrics(process, "v7_unguarded_detected")
    v6 = _binary_metrics(process, "v6_detected")
    family_rows = []
    for family, group in process.groupby("family", sort=True):
        row = {"family": str(family)}
        row.update(_binary_metrics(group, "v7_detected"))
        family_rows.append(row)
    family_metrics = pd.DataFrame(family_rows)

    exact_rows = []
    for (family, seed), group in process.groupby(["family", "seed"], sort=True):
        truth = set(group.loc[group["expected_true_process"].astype(bool), "process"].astype(str))
        v7_set = set(group.loc[group["v7_detected"].astype(bool), "process"].astype(str))
        u_set = set(group.loc[group["v7_unguarded_detected"].astype(bool), "process"].astype(str))
        v6_set = set(group.loc[group["v6_detected"].astype(bool), "process"].astype(str))
        exact_rows.append(
            {
                "family": str(family),
                "seed": int(seed),
                "v7_exact": v7_set == truth,
                "v7_unguarded_exact": u_set == truth,
                "v6_exact": v6_set == truth,
            }
        )
    exact = pd.DataFrame(exact_rows)
    seasonality = process.loc[process["process"].astype(str).eq("seasonality")]
    false_seasonality = seasonality.loc[~seasonality["expected_true_process"].astype(bool)]
    guard_by_process = (
        process.groupby("process", as_index=False)
        .agg(
            n_cells=("process", "size"),
            guard_pass_n=("collateral_guard_pass", "sum"),
            v7_detected_n=("v7_detected", "sum"),
            v7_unguarded_detected_n=("v7_unguarded_detected", "sum"),
            v6_detected_n=("v6_detected", "sum"),
        )
    )
    decision = {
        "purpose": "collateral_information_guard_v7_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(len(cases)),
        "n_process_cells": int(len(process)),
        "v7_guarded_metrics": v7,
        "v7_process_specific_unguarded_metrics": unguarded,
        "v6_same_case_metrics": v6,
        "v7_exact_complete_process_sets": int(exact["v7_exact"].sum()),
        "v7_unguarded_exact_complete_process_sets": int(exact["v7_unguarded_exact"].sum()),
        "v6_exact_complete_process_sets": int(exact["v6_exact"].sum()),
        "v7_false_seasonality_n": int(false_seasonality["v7_detected"].sum()),
        "v7_unguarded_false_seasonality_n": int(false_seasonality["v7_unguarded_detected"].sum()),
        "v6_false_seasonality_n": int(false_seasonality["v6_detected"].sum()),
        "fresh_known_truth_validation_required_before_promotion": True,
        "fresh_empirical_validation_authorized": False,
        "post_outcome_threshold_relaxation_allowed": False,
        "product_a_reopened": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    process.sort_values(["family", "seed", "process"], kind="mergesort").to_csv(out / "process_evaluation.csv", index=False)
    audit.sort_values(["family", "seed", "target_process", "audited_process", "audited_predictor"], kind="mergesort").to_csv(out / "specificity_audit.csv", index=False)
    routes.sort_values(["family", "seed", "process", "model_label"], kind="mergesort").to_csv(out / "route_summary.csv", index=False)
    cases.sort_values(["family", "seed"], kind="mergesort").to_csv(out / "case_summary.csv", index=False)
    family_metrics.to_csv(out / "family_metrics.csv", index=False)
    exact.to_csv(out / "exact_process_sets.csv", index=False)
    guard_by_process.to_csv(out / "guard_by_process.csv", index=False)
    (out / "development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def run_family(family: str, output_dir: str | Path) -> dict[str, object]:
    dev, v6 = _load()
    if family not in dev["families"]:
        raise ValueError("family outside v7 development denominator")
    process, audit, routes, cases = _fit_family(family, dev, v6)
    return _write(process, audit, routes, cases, output_dir, dev)


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    dev, _ = _load()
    root = Path(input_dir)
    files = {
        name: list(root.rglob(name))
        for name in ("process_evaluation.csv", "specificity_audit.csv", "route_summary.csv", "case_summary.csv")
    }
    if any(len(paths) != len(dev["families"]) for paths in files.values()):
        raise ValueError("v7 aggregate requires exactly one artifact per frozen development family")
    process = pd.concat([pd.read_csv(p) for p in files["process_evaluation.csv"]], ignore_index=True)
    audit = pd.concat([pd.read_csv(p) for p in files["specificity_audit.csv"]], ignore_index=True)
    routes = pd.concat([pd.read_csv(p) for p in files["route_summary.csv"]], ignore_index=True)
    cases = pd.concat([pd.read_csv(p) for p in files["case_summary.csv"]], ignore_index=True)
    expected_pairs = {(str(f), int(s)) for f in dev["families"] for s in dev["consumed_seed_denominator"]}
    observed_pairs = set(zip(cases["family"].astype(str), cases["seed"].astype(int), strict=True))
    if observed_pairs != expected_pairs or len(cases) != int(dev["n_cases"]):
        raise ValueError("v7 consumed development denominator changed")
    if cases["generating_truth_used_by_purge_or_guard"].astype(bool).any():
        raise ValueError("truth leaked into v7 purge/guard")
    return _write(process, audit, routes, cases, output_dir, dev)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    fit = sub.add_parser("fit-family")
    fit.add_argument("--family", required=True, choices=KNOWN_TRUTH_FAMILIES)
    fit.add_argument("--output-dir", required=True)
    agg = sub.add_parser("aggregate")
    agg.add_argument("--input-dir", required=True)
    agg.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "fit-family":
        decision = run_family(args.family, args.output_dir)
    else:
        decision = aggregate(args.input_dir, args.output_dir)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
