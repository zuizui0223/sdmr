"""Discovery-only diagnostics for the frozen 4201-4205 factorial experiment.

This script does not refit models. It reads the truth-free fold metrics already
produced by the prospective 35-case experiment and evaluates candidate
process-status rules. Any rule developed here must be frozen and evaluated on
new seeds before it can support a scientific claim.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from sdmr.factorial_process_recovery_experiment import PROCESSES, factorial_candidates
from sdmr.known_truth_response import DEFAULT_PROCESS_ALIASES
from sdmr.niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from sdmr.niche_recovery_selection import select_generalization_gated_niche_recovery_protocol


def parse_processes(text: str) -> set[str]:
    text = "" if pd.isna(text) else str(text)
    return {x for x in text.split(",") if x}


def candidate_processes(name: str, candidates) -> set[str]:
    c = candidates[name]
    return {
        str(DEFAULT_PROCESS_ALIASES.get(str(p), str(p)))
        for p in c.predictors
        if p not in c.observation_predictors
    }


def score_rule(predicted: list[set[str]], truth: list[set[str]], name: str) -> dict[str, object]:
    rows: dict[str, object] = {
        "rule": name,
        "n_cases": len(truth),
        "exact_n": sum(p == t for p, t in zip(predicted, truth, strict=True)),
    }
    rows["exact_rate"] = rows["exact_n"] / len(truth)
    for process in PROCESSES:
        tr = [process in t for t in truth]
        pr = [process in p for p in predicted]
        tp = sum(a and b for a, b in zip(tr, pr, strict=True))
        fn = sum(a and not b for a, b in zip(tr, pr, strict=True))
        tn = sum((not a) and (not b) for a, b in zip(tr, pr, strict=True))
        fp = sum((not a) and b for a, b in zip(tr, pr, strict=True))
        rows[f"{process}_sensitivity"] = tp / (tp + fn)
        rows[f"{process}_specificity"] = tn / (tn + fp)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cases = pd.read_csv(args.input_dir / "factorial_case_results.csv")
    metrics = pd.read_csv(args.input_dir / "factorial_fold_metrics.csv")
    candidates = factorial_candidates(random_state=0)

    truth = [parse_processes(x) for x in cases["true_processes"]]
    current = [parse_processes(x) for x in cases["stable_process_core"]]
    auc = [parse_processes(x) for x in cases["auc_processes"]]
    robust = [parse_processes(x) for x in cases["robust_processes"]]

    vote3_sets: list[set[str]] = []
    vote4_sets: list[set[str]] = []
    vote5_sets: list[set[str]] = []
    exclusion_required_sets: list[set[str]] = []
    vote_rows = []
    exclusion_rows = []

    for _, case in cases.iterrows():
        label = str(case["process_set"])
        seed = int(case["seed"])
        block = metrics.loc[
            metrics["process_set"].astype(str).eq(label)
            & metrics["seed"].astype(int).eq(seed)
        ].copy()
        if block.empty:
            raise ValueError(f"missing fold metrics for {label} seed {seed}")

        perturbation_winners: list[str] = []
        for perturbation, group in block.groupby("perturbation", sort=True):
            try:
                winner = select_generalization_gated_niche_recovery_protocol(group).candidate
            except ValueError:
                winner = ""
            perturbation_winners.append(winner)
            vote_rows.append(
                {
                    "process_set": label,
                    "seed": seed,
                    "perturbation": perturbation,
                    "winner": winner,
                    "winner_processes": ",".join(sorted(candidate_processes(winner, candidates))) if winner else "",
                }
            )
        available_winners = [x for x in perturbation_winners if x]
        if len(available_winners) != 5:
            raise ValueError(f"expected five perturbation-specific winners for {label} seed {seed}")
        counts = {p: sum(p in candidate_processes(w, candidates) for w in available_winners) for p in PROCESSES}
        vote3_sets.append({p for p, n in counts.items() if n >= 3})
        vote4_sets.append({p for p, n in counts.items() if n >= 4})
        vote5_sets.append({p for p, n in counts.items() if n == 5})

        required = set()
        full_robust_available = bool(case["robust_available"])
        for process in PROCESSES:
            excluded_names = {
                name for name in candidates if process not in candidate_processes(name, candidates)
            }
            subset = block.loc[block["candidate"].astype(str).isin(excluded_names)].copy()
            survives = False
            selected_without = ""
            error = ""
            if full_robust_available and not subset.empty:
                try:
                    selected = select_perturbation_robust_niche_recovery_protocol(subset)
                    survives = True
                    selected_without = selected.candidate
                except ValueError as exc:
                    error = str(exc)
            elif not full_robust_available:
                error = "full_robust_unavailable"
            if full_robust_available and not survives:
                required.add(process)
            exclusion_rows.append(
                {
                    "process_set": label,
                    "seed": seed,
                    "process": process,
                    "full_robust_available": full_robust_available,
                    "exclusion_alternative_survives": survives,
                    "selected_without_process": selected_without,
                    "error": error,
                }
            )
        exclusion_required_sets.append(required)

    robust_auc = [r & a for r, a in zip(robust, auc, strict=True)]
    stable_required = [s & req for s, req in zip(current, exclusion_required_sets, strict=True)]
    vote4_required = [v & req for v, req in zip(vote4_sets, exclusion_required_sets, strict=True)]

    rules = [
        score_rule(current, truth, "current_ecological_intersection"),
        score_rule(auc, truth, "auc_winner_processes"),
        score_rule(robust_auc, truth, "robust_ecological_intersect_auc"),
        score_rule(vote3_sets, truth, "perturbation_vote_3of5"),
        score_rule(vote4_sets, truth, "perturbation_vote_4of5"),
        score_rule(vote5_sets, truth, "perturbation_vote_5of5"),
        score_rule(exclusion_required_sets, truth, "robust_exclusion_required"),
        score_rule(stable_required, truth, "current_stable_and_exclusion_required"),
        score_rule(vote4_required, truth, "vote4_and_exclusion_required"),
    ]
    rule_summary = pd.DataFrame(rules).sort_values(
        ["exact_rate", "temperature_specificity", "water_specificity", "soil_specificity"],
        ascending=False,
    )
    rule_summary.to_csv(args.output_dir / "factorial_discovery_rule_summary.csv", index=False)
    pd.DataFrame(vote_rows).to_csv(args.output_dir / "factorial_perturbation_winners.csv", index=False)
    pd.DataFrame(exclusion_rows).to_csv(args.output_dir / "factorial_process_exclusion_discovery.csv", index=False)
    print(rule_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
