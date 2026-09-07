"""Independent 70-case replication of the frozen counterfactual process rule."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .counterfactual_process_recovery import classify_counterfactual_processes
from .counterfactual_process_validation import _exact, _processes_for_candidate, _summarize_process
from .ecological_inference_certificate import build_ecological_inference_certificate
from .factorial_process_recovery_experiment import (
    PROCESSES,
    evaluate_factorial_perturbations,
    factorial_candidates,
    process_set_label,
)
from .known_truth_perturbation import KnownTruthPerturbationSpec
from .known_truth_perturbation_experiment import _metric_winner
from .known_truth_response import DEFAULT_PROCESS_ALIASES
from .niche_recovery_selection import select_generalization_gated_niche_recovery_protocol

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "configs" / "product_a_counterfactual_process_replication_contract.json"
FACTORIAL_CONTRACT_PATH = Path(__file__).resolve().parents[2] / "configs" / "product_a_factorial_process_recovery_contract.json"


def load_contract(path: str | Path = CONTRACT_PATH) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_counterfactual_process_replication_preoutcome_contract":
        raise ValueError("wrong counterfactual replication contract")
    if payload.get("frozen_before_replication_outcome") is not True:
        raise ValueError("replication was not frozen before outcome")
    if payload.get("method_changes_after_validation") is not False:
        raise ValueError("replication must use the already validated method unchanged")
    if tuple(int(x) for x in payload["seeds"]) != tuple(range(4401, 4411)):
        raise ValueError("replication seed set changed")
    if int(payload["n_cases"]) != 70:
        raise ValueError("replication denominator changed")
    return payload


def run_replication(output_dir: str | Path, *, contract_path: str | Path = CONTRACT_PATH) -> dict[str, object]:
    contract = load_contract(contract_path)
    factorial = json.loads(FACTORIAL_CONTRACT_PATH.read_text(encoding="utf-8"))
    sim = factorial["simulation"]
    candidates = factorial_candidates(random_state=0)
    perturbations = tuple(KnownTruthPerturbationSpec(**row) for row in factorial["perturbations"])
    thresholds = {p: float(contract["frozen_thresholds"][p]) for p in PROCESSES}

    rows = []
    score_frames = []
    for process_row in contract["process_sets"]:
        truth = tuple(str(x) for x in process_row)
        label = process_set_label(truth)
        for seed in tuple(int(x) for x in contract["seeds"]):
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
            predicted, scores = classify_counterfactual_processes(
                metrics, candidates, thresholds, processes=PROCESSES
            )
            scores["process_set"] = label
            scores["seed"] = seed
            scores["true"] = scores["process"].map(lambda p: p in set(truth))
            score_frames.append(scores)

            canonical = metrics.loc[metrics["perturbation"].astype(str).eq("sampling_standard")]
            auc_name = _metric_winner(canonical, "presence_rank", ascending=False)
            canonical_name = select_generalization_gated_niche_recovery_protocol(canonical).candidate
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
                    "counterfactual_processes": ",".join(predicted),
                    "old_stable_processes": ",".join(old_stable),
                    "auc_processes": ",".join(auc_processes),
                    "counterfactual_exact": _exact(predicted, truth),
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
    if len(cases) != int(contract["n_cases"]):
        raise ValueError("replication denominator incomplete")

    summaries = []
    for method, col in (
        ("counterfactual", "counterfactual_processes"),
        ("old_stable_core", "old_stable_processes"),
        ("auc_winner", "auc_processes"),
    ):
        frame = _summarize_process(cases, col)
        frame["method"] = method
        summaries.append(frame)
    process_summary = pd.concat(summaries, ignore_index=True)
    counter = process_summary.loc[process_summary["method"].eq("counterfactual")].set_index("process")

    exact = float(cases["counterfactual_exact"].mean())
    old_exact = float(cases["old_stable_exact"].mean())
    auc_exact = float(cases["auc_exact"].mean())
    gate = contract["primary_support_gate"]
    checks = {"complete_denominator": len(cases) == int(contract["n_cases"])}
    checks["exact_process_set_recovery"] = exact >= float(gate["exact_process_set_recovery_min"])
    for p in PROCESSES:
        checks[f"{p}_sensitivity"] = float(counter.loc[p, "sensitivity"]) >= float(gate[f"{p}_sensitivity_min"])
        checks[f"{p}_specificity"] = float(counter.loc[p, "specificity"]) >= float(gate[f"{p}_specificity_min"])

    disagreement = cases.loc[~cases["model_consensus"].astype(bool)]
    paired = {
        "both_exact": int((cases.counterfactual_exact & cases.auc_exact).sum()),
        "counterfactual_only_exact": int((cases.counterfactual_exact & ~cases.auc_exact).sum()),
        "auc_only_exact": int((~cases.counterfactual_exact & cases.auc_exact).sum()),
        "both_wrong": int((~cases.counterfactual_exact & ~cases.auc_exact).sum()),
    }
    decision = {
        "purpose": "product_a_counterfactual_process_replication_decision",
        "supported": bool(all(checks.values())),
        "checks": checks,
        "n_cases": len(cases),
        "counterfactual_exact_process_set_recovery": exact,
        "old_stable_exact_process_set_recovery": old_exact,
        "auc_exact_process_set_recovery": auc_exact,
        "model_disagreement_n": int(len(disagreement)),
        "counterfactual_exact_when_ecological_models_disagree": (
            float(disagreement["counterfactual_exact"].mean()) if len(disagreement) else float("nan")
        ),
        "paired_exact_counts": paired,
        "frozen_thresholds": thresholds,
        "method_changed_after_4301_4305_validation": False,
        "v2_8_4_empirical_endpoint_unchanged": True,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases.to_csv(out / "counterfactual_replication_cases.csv", index=False)
    scores.to_csv(out / "counterfactual_replication_scores.csv", index=False)
    process_summary.to_csv(out / "counterfactual_replication_process_summary.csv", index=False)
    (out / "counterfactual_replication_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    args = parser.parse_args(argv)
    print(json.dumps(run_replication(args.output_dir, contract_path=args.contract), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
