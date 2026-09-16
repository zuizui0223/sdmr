"""Monotone refinement of v23 co-supported process sets with new evidence.

This module does not define how a separator is learned.  It enforces the inferential
contract after a separator has been frozen: v23 members can only be removed, never
added, and only when every predeclared required separator independently supplies a
qualified `exclude` state.  Missing, unavailable, indeterminate, unqualified or
compatible evidence preserves the member.
"""
from __future__ import annotations

from collections.abc import Sequence
import math

import pandas as pd

EVIDENCE_STATES = {"exclude", "compatible", "indeterminate", "unavailable"}
PROCESS_ORDER = ("temperature", "water", "seasonality", "noise")
CONTEXT_KEY = ("family", "seed", "target_block")


def _members(value: object) -> tuple[str, ...]:
    text = str(value)
    if not text or text == "nan":
        return ()
    return tuple(x for x in text.split("+") if x)


def _as_bool(value: object, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    raise ValueError(f"{name} must be boolean")


def refine_context_sets(
    base_sets: pd.DataFrame,
    separator_evidence: pd.DataFrame,
    *,
    required_separator_ids: Sequence[str],
    process_order: Sequence[str] = PROCESS_ORDER,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Refine frozen v23 sets under unanimous qualified exclusion.

    Returns `(context_refinements, member_audit)`.  Truth is not an accepted input.
    """
    base_required = {
        "family", "seed", "target_block", "supported_set", "supported_set_size"
    }
    missing = sorted(base_required - set(base_sets.columns))
    if missing:
        raise KeyError("base sets missing columns: " + ", ".join(missing))

    evidence_required = {
        "family", "seed", "target_block", "target_process", "separator_id",
        "evidence_state", "qualified", "source_disjoint_from_v21_support_inputs",
        "decision_rule_frozen_before_separator_outcomes",
    }
    missing = sorted(evidence_required - set(separator_evidence.columns))
    if missing:
        raise KeyError("separator evidence missing columns: " + ", ".join(missing))

    required_ids = tuple(str(x) for x in required_separator_ids)
    if not required_ids or len(set(required_ids)) != len(required_ids):
        raise ValueError("required_separator_ids must be a nonempty unique sequence")

    order = {str(p): i for i, p in enumerate(process_order)}
    base = base_sets.copy()
    base["family"] = base["family"].astype(str)
    base["seed"] = pd.to_numeric(base["seed"], errors="raise").astype(int)
    base["target_block"] = pd.to_numeric(base["target_block"], errors="raise").astype(int)
    if base.duplicated(list(CONTEXT_KEY)).any():
        raise ValueError("duplicate base context")

    evidence = separator_evidence.copy()
    evidence["family"] = evidence["family"].astype(str)
    evidence["seed"] = pd.to_numeric(evidence["seed"], errors="raise").astype(int)
    evidence["target_block"] = pd.to_numeric(evidence["target_block"], errors="raise").astype(int)
    evidence["target_process"] = evidence["target_process"].astype(str)
    evidence["separator_id"] = evidence["separator_id"].astype(str)
    evidence["evidence_state"] = evidence["evidence_state"].astype(str)

    unknown_states = sorted(set(evidence["evidence_state"]) - EVIDENCE_STATES)
    if unknown_states:
        raise ValueError("unknown evidence state: " + ", ".join(unknown_states))
    unknown_processes = sorted(set(evidence["target_process"]) - set(order))
    if unknown_processes:
        raise ValueError("process outside frozen universe: " + ", ".join(unknown_processes))
    if evidence.duplicated(list(CONTEXT_KEY) + ["target_process", "separator_id"]).any():
        raise ValueError("duplicate context-process-separator evidence row")

    # Evidence streams that were not designed independently of the v21 support input
    # or not frozen before their outcomes are never authorized for refinement.
    for row in evidence.itertuples(index=False):
        if not _as_bool(
            row.source_disjoint_from_v21_support_inputs,
            name="source_disjoint_from_v21_support_inputs",
        ):
            raise ValueError("separator evidence reuses v21 support inputs")
        if not _as_bool(
            row.decision_rule_frozen_before_separator_outcomes,
            name="decision_rule_frozen_before_separator_outcomes",
        ):
            raise ValueError("separator decision rule was not frozen before outcomes")

    lookup = {
        (
            str(row.family), int(row.seed), int(row.target_block),
            str(row.target_process), str(row.separator_id),
        ): row
        for row in evidence.itertuples(index=False)
    }

    context_rows: list[dict[str, object]] = []
    member_rows: list[dict[str, object]] = []
    for base_row in base.itertuples(index=False):
        key = (str(base_row.family), int(base_row.seed), int(base_row.target_block))
        members = _members(base_row.supported_set)
        if int(base_row.supported_set_size) != len(members):
            raise ValueError(f"base supported_set_size mismatch for {key}")
        if any(p not in order for p in members):
            raise ValueError(f"base set contains process outside frozen universe for {key}")
        if len(set(members)) != len(members):
            raise ValueError(f"base set contains duplicate process for {key}")

        retained: list[str] = []
        removed: list[str] = []
        unresolved: list[str] = []
        for process in members:
            rows = []
            missing_ids = []
            for separator_id in required_ids:
                row = lookup.get((*key, process, separator_id))
                if row is None:
                    missing_ids.append(separator_id)
                else:
                    rows.append(row)

            if missing_ids:
                decision = "retain_missing_separator"
                retained.append(process)
                unresolved.append(process)
            else:
                states = [str(r.evidence_state) for r in rows]
                qualified = [
                    _as_bool(r.qualified, name="qualified")
                    for r in rows
                ]
                if not all(qualified):
                    decision = "retain_unqualified_separator"
                    retained.append(process)
                    unresolved.append(process)
                elif all(state == "exclude" for state in states):
                    decision = "remove_unanimous_exclusion"
                    removed.append(process)
                else:
                    decision = "retain_nonexclusion"
                    retained.append(process)
                    if any(state in {"indeterminate", "unavailable"} for state in states):
                        unresolved.append(process)

            member_rows.append({
                "family": key[0],
                "seed": key[1],
                "target_block": key[2],
                "target_process": process,
                "member_decision": decision,
                "required_separator_count": len(required_ids),
                "missing_separator_count": len(missing_ids),
            })

        retained = sorted(retained, key=order.__getitem__)
        removed = sorted(removed, key=order.__getitem__)
        unresolved = sorted(set(unresolved), key=order.__getitem__)
        if set(retained) | set(removed) != set(members):
            raise AssertionError("refinement failed to partition base set")
        if set(retained) & set(removed):
            raise AssertionError("retained and removed sets overlap")

        context_rows.append({
            "family": key[0],
            "seed": key[1],
            "target_block": key[2],
            "base_supported_set": "+".join(members),
            "refined_supported_set": "+".join(retained),
            "removed_set": "+".join(removed),
            "retained_unresolved_set": "+".join(unresolved),
            "base_set_size": len(members),
            "refined_set_size": len(retained),
            "set_contraction": len(members) - len(retained),
            "contracted": bool(len(retained) < len(members)),
            "refinement_state": (
                "unchanged" if len(retained) == len(members)
                else "emptied" if not retained and members
                else "contracted"
            ),
        })

    return pd.DataFrame(context_rows), pd.DataFrame(member_rows)


def score_known_truth_refinement(
    refinements: pd.DataFrame,
    context_truth: pd.DataFrame,
) -> dict[str, float | int]:
    """Development-only truth score applied after refinement has been frozen."""
    truth_required = {"family", "seed", "target_block", "target_process", "generating_process_true"}
    missing = sorted(truth_required - set(context_truth.columns))
    if missing:
        raise KeyError("truth input missing columns: " + ", ".join(missing))

    truth = context_truth.copy()
    truth["family"] = truth["family"].astype(str)
    truth["seed"] = pd.to_numeric(truth["seed"], errors="raise").astype(int)
    truth["target_block"] = pd.to_numeric(truth["target_block"], errors="raise").astype(int)
    truth["target_process"] = truth["target_process"].astype(str)
    truth["generating_process_true"] = [
        _as_bool(value, name="generating_process_true")
        for value in truth["generating_process_true"]
    ]
    truth_map = {
        (str(k[0]), int(k[1]), int(k[2])): set(
            g.loc[g["generating_process_true"], "target_process"].astype(str)
        )
        for k, g in truth.groupby(list(CONTEXT_KEY), sort=True)
    }

    base_true = base_false = removed_true = removed_false = 0
    any_true_deletion = 0
    exact_after = 0
    contracted = 0
    total_contraction = 0
    n = int(len(refinements))
    for row in refinements.itertuples(index=False):
        key = (str(row.family), int(row.seed), int(row.target_block))
        if key not in truth_map:
            raise ValueError(f"missing truth context {key}")
        active = truth_map[key]
        base_set = set(_members(row.base_supported_set))
        refined = set(_members(row.refined_supported_set))
        removed = base_set - refined
        if not refined.issubset(base_set):
            raise ValueError("refined set is not a subset of base set")

        base_true += len(base_set & active)
        base_false += len(base_set - active)
        removed_true += len(removed & active)
        removed_false += len(removed - active)
        any_true_deletion += int(bool(removed & active))
        exact_after += int(refined == active)
        contracted += int(bool(removed))
        total_contraction += len(removed)

    return {
        "n_contexts": n,
        "mean_set_size_contraction": float(total_contraction / n) if n else math.nan,
        "fraction_of_contexts_contracted": float(contracted / n) if n else math.nan,
        "n_base_true_members": int(base_true),
        "n_base_false_members": int(base_false),
        "n_removed_true_members": int(removed_true),
        "n_removed_false_members": int(removed_false),
        "true_base_member_false_deletion_rate": (
            float(removed_true / base_true) if base_true else 0.0
        ),
        "false_base_member_removal_rate": (
            float(removed_false / base_false) if base_false else 0.0
        ),
        "context_any_true_deletion_rate": float(any_true_deletion / n) if n else math.nan,
        "exact_truth_set_rate_after_refinement": float(exact_after / n) if n else math.nan,
    }
