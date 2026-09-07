"""Fresh validation of process-specific counterfactual ecological recovery.

Thresholds are calibrated only from factorial discovery seeds 4201-4205 and
frozen in ``product_a_counterfactual_process_validation_contract.json``. This
module evaluates the unchanged process-set universe on unused seeds 4301-4305.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .counterfactual_process_recovery import classify_counterfactual_processes
from .ecological_inference_certificate import build_ecological_inference_certificate
from .factorial_process_recovery_experiment import (
    AUC_SELECTOR,
    CANONICAL_SELECTOR,
    ROBUST_SELECTOR,
    PROCESSES,
    evaluate_factorial_perturbations,
    factorial_candidates,
    process_set_label,
)
from .known_truth_perturbation import KnownTruthPerturbationSpec
from .known_truth_perturbation_experiment import _metric_winner
from .known_truth_response import DEFAULT_PROCESS_ALIASES
from .niche_recovery_selection import select_generalization_gated_niche_recovery_protocol

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "configs" / "product_a_counterfactual_process_validation_contract.json"
FACTORIAL_CONTRACT_PATH = Path(__file__).resolve().parents[2] / "configs" / "product_a_factorial_process_recovery_contract.json"


def load_contract(path: str | Path = CONTRACT_PATH) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_counterfactual_process_validation_preoutcome_contract":
        raise ValueError("wrong counterfactual validation contract")
    if payload.get("frozen_before_validation_outcome") is not True:
        raise ValueError("counterfactual thresholds were not frozen before validation")
    seeds = tuple(int(x) for x in payload["validation"]["seeds"])
    if seeds != (4301, 4302, 4303, 4304, 4305):
        raise ValueError("fresh validation seeds changed")
    if int(payload["validation"]["n_cases"]) != 35:
        raise ValueError("fresh validation denominator changed")
    if payload["governance"].get("no_threshold_change_after_validation") is not True:
        raise ValueError("post-validation threshold changes are not prohibited")
    return payload


def _parse_thresholds(contract: dict) -> dict[str, float]:
    return {
        process: float(contract["discovery_separation"][process]["frozen_threshold"])
        for process in PROCESSES
    }


def _processes_for_candidate(name: str, candidates) -> tuple[str, ...]:
    c = candidates[name]
    observation = set(c.observation_predictors)
    return tuple(
        sorted(
            {
                str(DEFAULT_PROCESS_ALIASES.get(str(p), str(p)))
                for p in c.predictors
                if p not in observation
            }
        )
    )


def _exact(selected, truth) -> bool:
    return set(selected) == set(truth)


def _summarize_process(cases: pd.DataFrame, predicted_col: str) -> pd.DataFrame:
    rows = []
    for process in PROCESSES:
        truth = cases["true_processes"].map(
            lambda x: process in {p for p in str(x).split(",") if p}
        )
        predicted = cases[predicted_col].map(
            lambda x: process in {p for p in str(x).split(",") if p}
        )
        tp = int((truth & predicted).sum())
        fn = int((truth & ~predicted).sum())
        tn = int((~truth & ~predicted).sum())
        fp = int((~truth & predicted).sum())
        rows.append(
            {
                "process": process,
                "truth_present_n": int(truth.sum()),
                "truth_absent_n": int((~truth).sum()),
                "tp": tp,
                "fn": fn,
                "tn": tn,
                "fp": fp,
                "sensitivity": tp / (tp + fn),
                "specificity": tn / (tn + fp),
            }
        )
    return pd.DataFrame(rows)


def run_validation(output_dir: str | Path, *, contract_path: str | Path = CONTRACT_PATH) -> dict[str, object]:
    contract = load_contract(contract_path)
    factorial = json.loads(FACTORIAL_CONTRACT_PATH.read_text(encoding="utf-8"))
    sim = factorial["simulation"]
    candidates = factorial_candidates(random_state=0)
    perturbations = tuple(KnownTruthPerturbationSpec(**row) for row in factorial["perturbations"])
    thresholds = _parse_thresholds(contract)

    rows: list[dict[str, object]] = []
    score_frames: list[pd.DataFrame] = []
    metric_frames: list[pd.DataFrame] = []
    process_sets = contract["validation"]["process_sets"]
    seeds = tuple(int(x) for x in contract["validation"]["seeds"])

    for process_row in process_sets:
        truth = tuple(str(x) for x in process_row)
        label = process_set_label(truth)
        for seed in seeds:
            result = evaluate_factorial_perturbations(
                truth,
                seed,
                candidates,
                perturbations=perturbations,
                n_cells=int(sim["n_cells"]),
                n_occurrences=int(sim["n_occurrences"]),
                n_target_group=int(sim["n_target_group"]),
                n_spatial_blocks=int(sim["n_spatial_blocks"]),
                inner_folds=int(sim["inner_folds"]),
                outer_holdout_fraction=float(sim["outer_holdout_fraction"]),
                min_background=int(sim["minimum_background"]),
            )
            metrics = result.fold_metrics.assign(process_set=label, seed=seed)
            metric_frames.append(metrics)

            counterfactual, scores = classify_counterfactual_processes(
                metrics,
                candidates,
                thresholds,
                processes=PROCESSES,
            )
            scores["process_set"] = label
            scores["seed"] = seed
            scores["true"] = scores["process"].map(lambda p: p in set(truth))
            score_frames.append(scores)

            canonical_metrics = metrics.loc[
                metrics["perturbation"].astype(str).eq("sampling_standard")
            ].copy()
            auc_name = _metric_winner(canonical_metrics, "presence_rank", ascending=False)
            canonical_name = select_generalization_gated_niche_recovery_protocol(
                canonical_metrics
            ).candidate
            robust_name = result.selection.candidate if result.selection is not None else None
            certificate = build_ecological_inference_certificate(
                canonical_name,
                robust_name,
                candidates,
                process_groups=DEFAULT_PROCESS_ALIASES,
            )
            old_stable = tuple(certificate.stable_process_core)
            auc_processes = _processes_for_candidate(auc_name, candidates)

            rows.append(
                {
                    "process_set": label,
                    "seed": seed,
                    "true_processes": ",".join(truth),
                    "counterfactual_processes": ",".join(counterfactual),
                    "old_stable_processes": ",".join(old_stable),
                    "auc_processes": ",".join(auc_processes),
                    "counterfactual_exact": _exact(counterfactual, truth),
                    "old_stable_exact": _exact(old_stable, truth),
                    "auc_exact": _exact(auc_processes, truth),
                    "canonical_candidate": canonical_name,
                    "robust_candidate": robust_name or "",
                    "auc_candidate": auc_name,
                    "robust_available": robust_name is not None,
                    "model_consensus": bool(certificate.model_consensus),
                    "selection_error": result.selection_error or "",
                }
            )

    cases = pd.DataFrame(rows)
    scores = pd.concat(score_frames, ignore_index=True)
    fold_metrics = pd.concat(metric_frames, ignore_index=True)
    expected = int(contract["validation"]["n_cases"])
    if len(cases) != expected:
        raise ValueError(f"fresh denominator incomplete: {len(cases)} != {expected}")

    counter_proc = _summarize_process(cases, "counterfactual_processes")
    old_proc = _summarize_process(cases, "old_stable_processes")
    auc_proc = _summarize_process(cases, "auc_processes")
    counter_proc["method"] = "counterfactual"
    old_proc["method"] = "old_stable_core"
    auc_proc["method"] = "auc_winner"
    process_summary = pd.concat([counter_proc, old_proc, auc_proc], ignore_index=True)

    exact_rate = float(cases["counterfactual_exact"].mean())
    old_exact_rate = float(cases["old_stable_exact"].mean())
    auc_exact_rate = float(cases["auc_exact"].mean())
    gate = contract["primary_support_gate"]
    counter = process_summary.loc[process_summary["method"].eq("counterfactual")].set_index("process")
    checks = {
        "complete_denominator": len(cases) == expected,
        "exact_process_set_recovery": exact_rate >= float(gate["exact_process_set_recovery_min"]),
    }
    for process in PROCESSES:
        checks[f"{process}_sensitivity"] = (
            float(counter.loc[process, "sensitivity"])
            >= float(gate[f"{process}_sensitivity_min"])
        )
        checks[f"{process}_specificity"] = (
            float(counter.loc[process, "specificity"])
            >= float(gate[f"{process}_specificity_min"])
        )
    supported = bool(all(checks.values()))

    disagreement = cases.loc[~cases["model_consensus"].astype(bool)]
    paired = pd.DataFrame(
        {
            "counterfactual_exact": cases["counterfactual_exact"].astype(bool),
            "auc_exact": cases["auc_exact"].astype(bool),
        }
    )
    paired_counts = {
        "both_exact": int((paired.counterfactual_exact & paired.auc_exact).sum()),
        "counterfactual_only_exact": int((paired.counterfactual_exact & ~paired.auc_exact).sum()),
        "auc_only_exact": int((~paired.counterfactual_exact & paired.auc_exact).sum()),
        "both_wrong": int((~paired.counterfactual_exact & ~paired.auc_exact).sum()),
    }
    decision = {
        "purpose": "product_a_counterfactual_process_validation_decision",
        "supported": supported,
        "checks": checks,
        "n_cases": len(cases),
        "counterfactual_exact_process_set_recovery": exact_rate,
        "old_stable_exact_process_set_recovery": old_exact_rate,
        "auc_exact_process_set_recovery": auc_exact_rate,
        "model_disagreement_n": int(len(disagreement)),
        "counterfactual_exact_when_ecological_models_disagree": (
            float(disagreement["counterfactual_exact"].mean()) if len(disagreement) else float("nan")
        ),
        "paired_exact_counts": paired_counts,
        "frozen_thresholds": thresholds,
        "discovery_seeds_not_reused": True,
        "no_postoutcome_threshold_tuning_allowed": True,
        "v2_8_4_empirical_endpoint_unchanged": True,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases.to_csv(out / "counterfactual_validation_cases.csv", index=False)
    scores.to_csv(out / "counterfactual_process_scores.csv", index=False)
    process_summary.to_csv(out / "counterfactual_process_summary.csv", index=False)
    fold_metrics.to_csv(out / "counterfactual_validation_fold_metrics.csv", index=False)
    (out / "counterfactual_validation_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    args = parser.parse_args(argv)
    decision = run_validation(args.output_dir, contract_path=args.contract)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
