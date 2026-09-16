"""Development runner for v23 set-valued attribution on the consumed v21 endpoint.

The build stage is deliberately truth-blind: it selects only the frozen v21 support
columns before constructing or summarizing context sets.  Known-truth scoring is a
separate command and may only be run after the set representation has been written.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path

import pandas as pd

from .set_valued_attribution_v23 import build_context_sets, score_known_truth_sets

FAMILIES = (
    "gaussian",
    "asymmetric",
    "soft_threshold",
    "interaction",
    "omitted_driver",
    "observation_confounded",
)
SEEDS = tuple(range(17001, 17011))
BLOCKS = tuple(range(8))
PROCESSES = ("temperature", "water", "seasonality", "noise")
BLIND_COLUMNS = (
    "family",
    "seed",
    "target_block",
    "target_process",
    "supported",
    "high_confidence_supported",
)


def _members(value: object) -> tuple[str, ...]:
    text = str(value)
    if not text or text == "nan":
        return ()
    return tuple(x for x in text.split("+") if x)


def validate_v21_denominator(frame: pd.DataFrame) -> pd.DataFrame:
    """Fail closed unless the input is exactly the consumed v21 denominator.

    The returned frame contains no known-truth column.  This makes it possible to
    inspect the set geometry without giving the set builder access to truth.
    """
    missing = sorted(set(BLIND_COLUMNS) - set(frame.columns))
    if missing:
        raise KeyError("v21 context decisions missing columns: " + ", ".join(missing))

    blind = frame.loc[:, BLIND_COLUMNS].copy()
    blind["family"] = blind["family"].astype(str)
    blind["target_process"] = blind["target_process"].astype(str)
    blind["seed"] = pd.to_numeric(blind["seed"], errors="raise").astype(int)
    blind["target_block"] = pd.to_numeric(blind["target_block"], errors="raise").astype(int)

    if len(blind) != 1920:
        raise ValueError(f"v21 denominator must contain 1920 context-process rows, got {len(blind)}")
    if tuple(sorted(blind["family"].unique())) != tuple(sorted(FAMILIES)):
        raise ValueError("v21 family denominator drift")
    if tuple(sorted(blind["seed"].unique())) != SEEDS:
        raise ValueError("v21 seed denominator drift")
    if tuple(sorted(blind["target_block"].unique())) != BLOCKS:
        raise ValueError("v21 target-block denominator drift")
    if tuple(sorted(blind["target_process"].unique())) != tuple(sorted(PROCESSES)):
        raise ValueError("v21 process denominator drift")

    keys = ["family", "seed", "target_block"]
    contexts = blind.groupby(keys, sort=True)
    if contexts.ngroups != 480:
        raise ValueError(f"v21 denominator must contain 480 contexts, got {contexts.ngroups}")
    for key, group in contexts:
        got = tuple(sorted(group["target_process"].tolist()))
        if got != tuple(sorted(PROCESSES)) or len(group) != len(PROCESSES):
            raise ValueError(f"v21 context {key} does not contain each frozen process exactly once")
    if blind.duplicated(keys + ["target_process"]).any():
        raise ValueError("duplicate v21 context-process key")
    return blind


def summarize_context_sets(context_sets: pd.DataFrame) -> dict[str, object]:
    """Truth-blind description of how sharp the v21 support representation is."""
    required = {
        "supported_set",
        "high_confidence_subset",
        "supported_set_size",
        "high_confidence_subset_size",
        "attribution_state",
    }
    missing = sorted(required - set(context_sets.columns))
    if missing:
        raise KeyError("context sets missing columns: " + ", ".join(missing))

    n = int(len(context_sets))
    state_counts = Counter(context_sets["attribution_state"].astype(str))
    size_counts = Counter(int(x) for x in context_sets["supported_set_size"])
    high_size_counts = Counter(int(x) for x in context_sets["high_confidence_subset_size"])
    member_counts: Counter[str] = Counter()
    high_member_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()

    for row in context_sets.itertuples(index=False):
        members = _members(row.supported_set)
        high = _members(row.high_confidence_subset)
        member_counts.update(members)
        high_member_counts.update(high)
        for left, right in combinations(members, 2):
            pair_counts[(left, right)] += 1

    nonempty = n - int(state_counts.get("empty", 0))
    singleton = int(state_counts.get("singleton", 0))
    multi = int(state_counts.get("partial_identification_set", 0))
    total_pair_instances = int(sum(pair_counts.values()))
    return {
        "purpose": "set_valued_attribution_v23_truth_blind_development_readout",
        "source": "consumed_v21_context_decisions",
        "truth_columns_used": False,
        "n_contexts": n,
        "n_nonempty_contexts": nonempty,
        "n_empty_contexts": int(state_counts.get("empty", 0)),
        "n_singleton_contexts": singleton,
        "n_multi_member_contexts": multi,
        "empty_context_rate": float(state_counts.get("empty", 0) / n) if n else float("nan"),
        "singleton_context_rate": float(singleton / n) if n else float("nan"),
        "multi_member_context_rate": float(multi / n) if n else float("nan"),
        "mean_supported_set_size": float(context_sets["supported_set_size"].mean()) if n else float("nan"),
        "mean_high_confidence_subset_size": float(context_sets["high_confidence_subset_size"].mean()) if n else float("nan"),
        "supported_set_size_distribution": {str(k): int(v) for k, v in sorted(size_counts.items())},
        "high_confidence_subset_size_distribution": {str(k): int(v) for k, v in sorted(high_size_counts.items())},
        "supported_member_counts": {k: int(member_counts.get(k, 0)) for k in PROCESSES},
        "high_confidence_member_counts": {k: int(high_member_counts.get(k, 0)) for k in PROCESSES},
        "co_support_pair_counts": {
            f"{left}+{right}": int(count)
            for (left, right), count in sorted(pair_counts.items())
        },
        "n_co_support_pair_instances": total_pair_instances,
        "fresh_empirical_claim": False,
    }


def build_from_v21(input_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    frame = pd.read_csv(input_csv)
    blind = validate_v21_denominator(frame)
    sets = build_context_sets(blind, process_order=PROCESSES)
    summary = summarize_context_sets(sets)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    sets.to_csv(out / "context_sets.csv", index=False)
    (out / "truth_blind_set_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def score_after_freeze(
    context_sets_csv: str | Path,
    context_decisions_csv: str | Path,
    output_json: str | Path,
) -> dict[str, object]:
    """Score an already-written set representation against known truth."""
    sets = pd.read_csv(context_sets_csv, keep_default_na=False)
    decisions = pd.read_csv(context_decisions_csv)
    # Revalidate the source denominator before opening its truth column to scoring.
    validate_v21_denominator(decisions)
    if "generating_process_true" not in decisions.columns:
        raise KeyError("known-truth scoring requires generating_process_true")

    score = score_known_truth_sets(sets, decisions)
    truth = decisions.copy()
    truth["generating_process_true"] = truth["generating_process_true"].astype(bool)
    selected = truth["supported"].astype(bool)
    actual = truth["generating_process_true"]
    tp = int((selected & actual).sum())
    fp = int((selected & ~actual).sum())
    nt = int(actual.sum())
    nf = int((~actual).sum())
    score.update({
        "purpose": "set_valued_attribution_v23_known_truth_development_score",
        "set_construction_used_truth": False,
        "n_true_process_memberships": nt,
        "n_false_process_memberships": nf,
        "n_supported_true_memberships": tp,
        "n_supported_false_memberships": fp,
        "true_member_recall": float(tp / nt) if nt else float("nan"),
        "false_member_positive_rate": float(fp / nf) if nf else float("nan"),
        "positive_member_precision": float(tp / (tp + fp)) if (tp + fp) else float("nan"),
        "fresh_empirical_claim": False,
    })
    path = Path(output_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return score


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--input", required=True)
    build.add_argument("--output-dir", required=True)
    score = sub.add_parser("score")
    score.add_argument("--context-sets", required=True)
    score.add_argument("--context-decisions", required=True)
    score.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_from_v21(args.input, args.output_dir)
    else:
        result = score_after_freeze(args.context_sets, args.context_decisions, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
