"""Prospective known-truth validation for proxy-closed matched-route v6.

The family jobs create all occurrence/process outputs without opening generating-
process labels.  Truth is opened only by the terminal evaluator after two complete
independent executions exist for every frozen family.  The consumed empirical
positive-control labels are not inputs to this module.
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
from .process_challenge_learner import CONTRIBUTORY, REQUIRED
from .prospective_identification_validation import _selection_frames
from .proxy_closed_route_process_challenge import fit_proxy_closed_route_process_challenge
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .transport_parity import assert_transport_frame_parity
from .validation import make_spatial_partition


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation.json"


def load_contract(path: str | Path = CONFIG) -> dict:
    c = json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("purpose") != "proxy_closed_route_process_challenge_v6_prospective_known_truth_validation":
        raise ValueError("wrong v6 known-truth validation contract")
    if c.get("scientific_run_authorized") is not True:
        raise ValueError("v6 known-truth scientific run is not authorized")
    if tuple(c.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v6 family denominator changed")
    if tuple(int(x) for x in c.get("seeds", ())) != tuple(range(14001, 14011)):
        raise ValueError("v6 validation seed denominator changed")
    if int(c.get("n_cases", -1)) != 60 or int(c.get("n_process_cells", -1)) != 300:
        raise ValueError("v6 validation denominator changed")
    for flag in ("post_outcome_changes_allowed", "threshold_relaxation_allowed", "seed_replacement_allowed", "family_replacement_allowed"):
        if c.get(flag) is not False:
            raise ValueError(f"v6 validation governance changed: {flag}")
    if c.get("consumed_real_positive_controls_are_excluded_from_validation") is not True:
        raise ValueError("consumed empirical controls entered v6 validation")
    return c


def _specs(c: dict) -> tuple[ModelSpec, ...]:
    specs = tuple(
        ModelSpec(C=float(x["C"]), degree=int(x["degree"]), penalty=str(x["penalty"]), random_state=int(x["random_state"]))
        for x in c["model_specs"]
    )
    if len(specs) != 6 or len({x.label for x in specs}) != 6:
        raise ValueError("v6 model grid changed")
    return specs


def _registry(c: dict) -> pd.DataFrame:
    return pd.DataFrame(c["process_registry"])[["predictor", "process", "role"]].copy()


def _failure_frames(family: str, seed: int, replicate: int, processes: tuple[str, ...], error: BaseException) -> dict[str, pd.DataFrame]:
    case = pd.DataFrame([{
        "replicate": replicate,
        "family": family,
        "seed": seed,
        "case_available": False,
        "failure_class": type(error).__name__,
        "selection_receipt": "",
        "prediction_model_label": "",
        "n_model_pool_occurrences": 0,
        "n_answer_check_occurrences": 0,
    }])
    process = pd.DataFrame([{
        "replicate": replicate,
        "family": family,
        "seed": seed,
        "process": p,
        "status": "unresolved",
        "process_detected": False,
        "v5_status": "unresolved",
        "n_expected_routes": 0,
        "n_absolute_adequate_routes": 0,
        "n_noninferior_routes": 0,
        "n_inferior_viable_routes": 0,
        "n_indeterminate_viable_routes": 0,
        "n_incomplete_routes": 0,
    } for p in processes])
    return {
        "case_summary": case,
        "process_status": process,
        "purged_route_summary": pd.DataFrame(),
        "leakage_diagnostic": pd.DataFrame(),
    }


def fit_case_nontruth(family: str, seed: int, *, replicate: int, contract: dict) -> dict[str, pd.DataFrame]:
    sim = contract["simulation"]
    learner = contract["learner"]
    ecological = tuple(str(x) for x in contract["ecological_predictors"])
    observation = tuple(str(x) for x in contract["observation_predictors"])
    processes = tuple(str(x) for x in contract["process_universe"])

    simulation = simulate_known_truth_plant_niche(
        family,
        seed=int(seed),
        n_cells=int(sim["n_cells"]),
        n_occurrences=int(sim["n_occurrences"]),
        n_target_group=int(sim["n_target_group"]),
    )
    occurrences, background = _selection_frames(simulation, family=family, seed=int(seed))
    split = freeze_occurrence_answer_check_split(
        occurrences,
        id_col="occurrence_id",
        lon_col="longitude",
        lat_col="latitude",
        n_blocks=int(sim["outer_n_blocks"]),
        holdout_fraction=float(sim["answer_check_fraction"]),
        random_state=int(sim["outer_random_state_offset"]) + int(seed),
    )
    model_presence = split.model_pool(occurrences)
    inner = make_spatial_partition(
        model_presence["longitude"].to_numpy(float),
        model_presence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=int(sim["inner_n_blocks"]),
        holdout_fraction=0.20,
        random_state=int(sim["inner_random_state_offset"]) + int(seed),
    )
    fit = fit_proxy_closed_route_process_challenge(
        model_presence,
        background,
        inner.presence_blocks,
        inner.background_blocks,
        ecological_predictors=ecological,
        observation_predictors=observation,
        process_registry=_registry(contract),
        process_universe=processes,
        model_specs=_specs(contract),
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
        observation_signal_chance=float(learner["observation_signal_chance"]),
        observation_signal_margin=float(learner["observation_signal_margin"]),
        observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
        observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
        observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
        occurrence_split=split,
        occurrence_id_col="occurrence_id",
    )

    case = pd.DataFrame([{
        "replicate": int(replicate),
        "family": str(family),
        "seed": int(seed),
        "case_available": True,
        "failure_class": "",
        "selection_receipt": fit.selection_receipt,
        "prediction_model_label": fit.prediction_model_label,
        "n_model_pool_occurrences": int(len(model_presence)),
        "n_answer_check_occurrences": int(len(split.answer_check_ids)),
    }])
    process = fit.process_summary.copy()
    process.insert(0, "seed", int(seed))
    process.insert(0, "family", str(family))
    process.insert(0, "replicate", int(replicate))
    routes = fit.purged_route_summary.copy()
    routes.insert(0, "seed", int(seed))
    routes.insert(0, "family", str(family))
    routes.insert(0, "replicate", int(replicate))
    leakage = fit.leakage_diagnostic.copy()
    leakage.insert(0, "seed", int(seed))
    leakage.insert(0, "family", str(family))
    leakage.insert(0, "replicate", int(replicate))
    return {
        "case_summary": case,
        "process_status": process,
        "purged_route_summary": routes,
        "leakage_diagnostic": leakage,
    }


def fit_family(family: str, replicate: int, output_dir: str | Path) -> None:
    c = load_contract()
    if family not in c["families"]:
        raise ValueError("family outside frozen v6 denominator")
    if int(replicate) not in (1, 2):
        raise ValueError("replicate must be 1 or 2")
    processes = tuple(str(x) for x in c["process_universe"])
    accumulated = {k: [] for k in ("case_summary", "process_status", "purged_route_summary", "leakage_diagnostic")}
    for seed in tuple(int(x) for x in c["seeds"]):
        try:
            frames = fit_case_nontruth(family, seed, replicate=int(replicate), contract=c)
        except Exception as error:
            frames = _failure_frames(family, seed, int(replicate), processes, error)
        for key in accumulated:
            if not frames[key].empty:
                accumulated[key].append(frames[key])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for key, pieces in accumulated.items():
        frame = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
        if len(frame):
            sort_cols = [x for x in ("replicate", "family", "seed", "process", "model_label", "route", "process_predictor", "fold") if x in frame.columns]
            frame = frame.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        frame.to_csv(out / f"{key}.csv", index=False)
    receipt = {
        "purpose": "proxy_closed_route_v6_known_truth_family_nontruth_fit",
        "family": str(family),
        "replicate": int(replicate),
        "seeds": list(c["seeds"]),
        "hidden_generating_process_truth_used_by_learner": False,
        "consumed_empirical_positive_control_labels_used": False,
        "answer_check_occurrences_used_for_tuning": False,
        "post_outcome_changes_allowed": False,
    }
    (out / "run_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _discover(root: Path) -> dict[tuple[int, str], Path]:
    found: dict[tuple[int, str], Path] = {}
    for path in root.rglob("run_receipt.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != "proxy_closed_route_v6_known_truth_family_nontruth_fit":
            continue
        key = (int(payload["replicate"]), str(payload["family"]))
        if key in found:
            raise ValueError(f"duplicate v6 validation artifact: {key}")
        found[key] = path.parent
    return found


def _load(path: Path, name: str) -> pd.DataFrame:
    p = path / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _binary_metrics(frame: pd.DataFrame, detected_col: str) -> dict[str, float | int]:
    truth = frame["expected_true_process"].astype(bool).to_numpy()
    detected = frame[detected_col].astype(bool).to_numpy()
    status = frame["status"].astype(str).to_numpy()
    tp = int(np.sum(truth & detected))
    fp = int(np.sum((~truth) & detected))
    fn = int(np.sum(truth & (~detected)))
    tn = int(np.sum((~truth) & (~detected)))
    true_n = int(truth.sum())
    false_n = int((~truth).sum())
    false_required = int(np.sum((~truth) & (status == REQUIRED)))

    def f1(a: int, b: int, c: int) -> float:
        d = 2 * a + b + c
        return float(2 * a / d) if d else float("nan")

    pos_f1 = f1(tp, fp, fn)
    neg_f1 = f1(tn, fn, fp)
    return {
        "true_process_recall": float(tp / true_n) if true_n else float("nan"),
        "false_process_detection_rate": float(fp / false_n) if false_n else float("nan"),
        "false_required_rate": float(false_required / false_n) if false_n else float("nan"),
        "positive_f1": pos_f1,
        "negative_f1": neg_f1,
        "macro_f1": float(np.nanmean([pos_f1, neg_f1])),
        "n_true_processes": true_n,
        "n_false_processes": false_n,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "n_false_required": false_required,
        "n_unresolved": int(np.sum(status == "unresolved")),
    }


def evaluate_terminal(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    c = load_contract()
    root = Path(input_dir)
    runs = _discover(root)
    expected = {(r, f) for r in (1, 2) for f in c["families"]}
    if set(runs) != expected:
        raise ValueError(f"terminal v6 evaluator requires all family replicates; missing={sorted(expected-set(runs))}, extra={sorted(set(runs)-expected)}")

    det = c["determinism"]
    parity = {}
    for family in c["families"]:
        for name in ("case_summary", "process_status", "purged_route_summary", "leakage_diagnostic"):
            a = _load(runs[(1, family)], name).drop(columns="replicate", errors="ignore")
            b = _load(runs[(2, family)], name).drop(columns="replicate", errors="ignore")
            parity[f"{family}/{name}"] = assert_transport_frame_parity(
                a, b,
                rtol=float(det["numeric_relative_tolerance"]),
                atol=float(det["numeric_absolute_tolerance"]),
            ).as_dict()

    cases = pd.concat([_load(runs[(1, f)], "case_summary") for f in c["families"]], ignore_index=True)
    process = pd.concat([_load(runs[(1, f)], "process_status") for f in c["families"]], ignore_index=True)
    cases = cases.sort_values(["family", "seed"], kind="mergesort").reset_index(drop=True)
    process = process.sort_values(["family", "seed", "process"], kind="mergesort").reset_index(drop=True)
    full_denominator = bool(len(cases) == int(c["n_cases"]) and cases["case_available"].astype(bool).all() and len(process) == int(c["n_process_cells"]))

    truth_values = []
    for row in process[["family", "seed", "process"]].itertuples(index=False):
        truth_frame = pd.DataFrame({"scenario": [str(row.family)], "temperature": [0.0], "water": [0.0], "soil": [0.0]})
        truth_values.append(str(row.process) in set(infer_true_processes(truth_frame)))
    evaluation = process.copy()
    evaluation["expected_true_process"] = truth_values
    evaluation["v6_detected"] = evaluation["process_detected"].astype(bool)
    evaluation["v5_detected"] = evaluation["v5_status"].astype(str).isin({CONTRIBUTORY, REQUIRED})

    v6_metrics = _binary_metrics(evaluation, "v6_detected")
    v5_metrics = _binary_metrics(evaluation.assign(status=evaluation["v5_status"]), "v5_detected")
    family_rows = []
    for family, group in evaluation.groupby("family", sort=True):
        row = {"family": str(family)}
        row.update(_binary_metrics(group, "v6_detected"))
        family_rows.append(row)
    family_metrics = pd.DataFrame(family_rows)

    exact_rows = []
    for (family, seed), group in evaluation.groupby(["family", "seed"], sort=True):
        truth_set = set(group.loc[group["expected_true_process"].astype(bool), "process"].astype(str))
        v6_set = set(group.loc[group["v6_detected"].astype(bool), "process"].astype(str))
        v5_set = set(group.loc[group["v5_detected"].astype(bool), "process"].astype(str))
        exact_rows.append({
            "family": str(family),
            "seed": int(seed),
            "true_processes": ",".join(sorted(truth_set)),
            "v6_processes": ",".join(sorted(v6_set)),
            "v5_processes": ",".join(sorted(v5_set)),
            "v6_exact": v6_set == truth_set,
            "v5_exact": v5_set == truth_set,
        })
    exact = pd.DataFrame(exact_rows)

    required_rows = evaluation.loc[evaluation["status"].astype(str).eq(REQUIRED)]
    required_complete = bool(
        len(required_rows) == 0
        or (
            required_rows["n_expected_routes"].astype(int).gt(0)
            & required_rows["n_incomplete_routes"].astype(int).eq(0)
        ).all()
    )
    gate = c["primary_process_thresholds"]
    family_recall_pass = bool(
        np.isfinite(family_metrics["true_process_recall"]).all()
        and (family_metrics["true_process_recall"] >= float(gate["family_true_process_recall_min"])).all()
    )
    checks = {
        "complete_full_denominator": full_denominator,
        "determinism": True,
        "false_required_rate": float(v6_metrics["false_required_rate"]) <= float(gate["false_required_rate_max"]),
        "true_process_recall": float(v6_metrics["true_process_recall"]) >= float(gate["true_process_recall_min"]),
        "process_status_macro_f1": float(v6_metrics["macro_f1"]) >= float(gate["process_status_macro_f1_min"]),
        "all_family_true_process_recall": family_recall_pass,
        "required_claim_evidence_complete": required_complete,
    }
    supported = bool(all(checks.values()))
    decision = {
        "purpose": "proxy_closed_route_process_challenge_v6_prospective_known_truth_decision",
        "known_truth_supported": supported,
        "checks": checks,
        "v6_process_metrics": v6_metrics,
        "v5_same_cases_descriptive_metrics": v5_metrics,
        "v6_exact_complete_process_sets": int(exact["v6_exact"].astype(bool).sum()),
        "v5_exact_complete_process_sets": int(exact["v5_exact"].astype(bool).sum()),
        "n_cases": int(len(exact)),
        "consumed_empirical_positive_controls_used_for_validation": False,
        "comparative_superiority_gate_predeclared": False,
        "fresh_empirical_validation_required": True,
        "product_a_reopened": False,
        "post_outcome_changes_allowed": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases.to_csv(out / "case_summary.csv", index=False)
    process.to_csv(out / "process_status_pretruth.csv", index=False)
    evaluation.to_csv(out / "truth_evaluation.csv", index=False)
    family_metrics.to_csv(out / "family_process_metrics.csv", index=False)
    exact.to_csv(out / "exact_process_sets.csv", index=False)
    (out / "determinism_decision.json").write_text(json.dumps({"determinism_passed": True, "frame_summaries": parity}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "scientific_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    fit = sub.add_parser("fit-family")
    fit.add_argument("--family", required=True, choices=KNOWN_TRUTH_FAMILIES)
    fit.add_argument("--replicate", required=True, type=int, choices=(1, 2))
    fit.add_argument("--output-dir", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--input-dir", required=True)
    evaluate.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "fit-family":
        fit_family(args.family, args.replicate, args.output_dir)
    else:
        decision = evaluate_terminal(args.input_dir, args.output_dir)
        print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
