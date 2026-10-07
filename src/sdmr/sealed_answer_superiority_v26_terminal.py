"""Terminal known-truth scoring for prospective sealed-answer superiority v26."""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

import pandas as pd


FAMILIES = (
    "gaussian", "asymmetric", "soft_threshold", "interaction",
    "omitted_driver", "observation_confounded",
)
SEEDS = tuple(range(20001, 20021))
BLOCKS = tuple(range(8))
TRUE_PROCESSES = frozenset({"temperature", "water"})
SEPARATOR_ID = "sealed_answer_superiority_v26"
CONTEXT_KEY = ("family", "seed", "target_block")


def _members(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {part for part in text.split("+") if part}


def _as_bool(value: object, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    raise ValueError(f"{name} must be boolean")


def _authorize_truth_open(gate: Mapping[str, object]) -> None:
    if gate.get("purpose") != "sealed_answer_superiority_v26_determinism_gate":
        raise ValueError("truth opening requires the v26 determinism gate")
    if gate.get("deterministic_match") is not True or gate.get("truth_open_authorized") is not True:
        raise ValueError("truth opening is not authorized by deterministic reproduction")


def _validate_refinement_denominator(refinements: pd.DataFrame) -> pd.DataFrame:
    required = {
        "family", "seed", "target_block", "base_supported_set",
        "refined_supported_set", "removed_set",
    }
    missing = sorted(required - set(refinements.columns))
    if missing:
        raise KeyError("terminal refinements missing columns: " + ", ".join(missing))
    frame = refinements.copy()
    frame["family"] = frame["family"].astype(str)
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    if frame.duplicated(list(CONTEXT_KEY)).any():
        raise ValueError("duplicate terminal context")
    if len(frame) != 960:
        raise ValueError("terminal scoring requires exactly 960 frozen contexts")
    if set(frame["family"]) != set(FAMILIES):
        raise ValueError("terminal family denominator changed")
    if set(frame["seed"]) != set(SEEDS):
        raise ValueError("terminal seed denominator changed")
    observed = set(
        zip(
            frame["family"].astype(str),
            frame["seed"].astype(int),
            frame["target_block"].astype(int),
            strict=True,
        )
    )
    expected = {(family, seed, block) for family in FAMILIES for seed in SEEDS for block in BLOCKS}
    if observed != expected:
        raise ValueError("terminal context roster changed from frozen 6x20x8 denominator")
    return frame


def score_prospective_terminal(
    refinements: pd.DataFrame,
    separator_evidence: pd.DataFrame,
    determinism_gate: Mapping[str, object],
) -> dict[str, object]:
    """Open known truth only after reproduction and score the frozen v26 gate."""
    _authorize_truth_open(determinism_gate)
    frame = _validate_refinement_denominator(refinements)

    evidence_required = {
        "family", "seed", "target_block", "target_process", "separator_id",
        "evidence_state", "qualified", "source_disjoint_from_v21_support_inputs",
        "decision_rule_frozen_before_separator_outcomes",
    }
    missing = sorted(evidence_required - set(separator_evidence.columns))
    if missing:
        raise KeyError("terminal separator evidence missing columns: " + ", ".join(missing))
    evidence = separator_evidence.copy()
    evidence["family"] = evidence["family"].astype(str)
    evidence["seed"] = pd.to_numeric(evidence["seed"], errors="raise").astype(int)
    evidence["target_block"] = pd.to_numeric(evidence["target_block"], errors="raise").astype(int)
    evidence["target_process"] = evidence["target_process"].astype(str)
    evidence["separator_id"] = evidence["separator_id"].astype(str)
    key = [*CONTEXT_KEY, "target_process", "separator_id"]
    if evidence.duplicated(key).any():
        raise ValueError("duplicate terminal context-process-separator evidence")
    lookup = {
        (str(row.family), int(row.seed), int(row.target_block), str(row.target_process)): row
        for row in evidence.itertuples(index=False)
        if str(row.separator_id) == SEPARATOR_ID
    }

    base_true = base_false = removed_true = removed_false = 0
    true_deletion_contexts = 0
    removed_total = 0
    qualified_removal_total = 0
    exact_truth_after = 0

    for row in frame.itertuples(index=False):
        context = (str(row.family), int(row.seed), int(row.target_block))
        base = _members(row.base_supported_set)
        refined = _members(row.refined_supported_set)
        removed_reported = _members(row.removed_set)
        if not refined.issubset(base):
            raise ValueError("terminal refined set is not a subset of base set")
        removed = base - refined
        if removed != removed_reported:
            raise ValueError("terminal removed_set disagrees with base/refined set difference")

        base_true += len(base & TRUE_PROCESSES)
        base_false += len(base - TRUE_PROCESSES)
        removed_true += len(removed & TRUE_PROCESSES)
        removed_false += len(removed - TRUE_PROCESSES)
        true_deletion_contexts += int(bool(removed & TRUE_PROCESSES))
        exact_truth_after += int(refined == TRUE_PROCESSES)
        removed_total += len(removed)

        for process in removed:
            ev = lookup.get((*context, process))
            if ev is None:
                continue
            qualified = _as_bool(ev.qualified, name="qualified")
            disjoint = _as_bool(
                ev.source_disjoint_from_v21_support_inputs,
                name="source_disjoint_from_v21_support_inputs",
            )
            frozen = _as_bool(
                ev.decision_rule_frozen_before_separator_outcomes,
                name="decision_rule_frozen_before_separator_outcomes",
            )
            if (
                qualified
                and disjoint
                and frozen
                and str(ev.evidence_state) == "exclude"
                and str(ev.separator_id) == SEPARATOR_ID
            ):
                qualified_removal_total += 1

    all_removals_qualified = bool(qualified_removal_total == removed_total)
    passed = bool(
        removed_true == 0
        and true_deletion_contexts == 0
        and removed_false >= 1
        and all_removals_qualified
    )
    return {
        "purpose": "sealed_answer_superiority_v26_prospective_terminal_decision",
        "truth_opened": True,
        "n_contexts": int(len(frame)),
        "n_base_true_members": int(base_true),
        "n_base_false_members": int(base_false),
        "n_removed_true_members": int(removed_true),
        "n_removed_false_members": int(removed_false),
        "n_contexts_with_true_member_deletion": int(true_deletion_contexts),
        "n_reported_removals": int(removed_total),
        "n_qualified_removals": int(qualified_removal_total),
        "all_removals_qualified": all_removals_qualified,
        "exact_truth_set_rate_after_refinement": float(exact_truth_after / len(frame)),
        "prospective_gate_passed": passed,
        "terminal_status": "pass" if passed else "fail",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--refinements", required=True)
    parser.add_argument("--separator-evidence", required=True)
    parser.add_argument("--determinism-gate", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    refinements = pd.read_csv(args.refinements)
    evidence = pd.read_csv(args.separator_evidence)
    gate = json.loads(Path(args.determinism_gate).read_text(encoding="utf-8"))
    result = score_prospective_terminal(refinements, evidence, gate)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "prospective_decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
