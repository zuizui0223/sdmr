"""Independent-evidence contraction of frozen v23 co-supported process sets.

v24 is deliberately not a ranker.  It starts from the set produced by v23 and
permits deletion only when a separate evidence stream explicitly acts on every
member of a multi-member set.  Truth-like columns are never consulted.
"""
from __future__ import annotations

from collections.abc import Collection

import pandas as pd


_CONTEXT_COLUMNS = (
    "family",
    "seed",
    "target_block",
    "supported_set",
    "supported_set_size",
)
_EVIDENCE_COLUMNS = (
    "family",
    "seed",
    "target_block",
    "target_process",
    "action",
    "evidence_source_id",
    "evidence_is_new",
    "evidence_is_separating",
)
_ALLOWED_ACTIONS = frozenset({"retain", "remove", "abstain"})
_DEFAULT_FORBIDDEN_SOURCE_IDS = frozenset(
    {
        "v21_supported",
        "v21_high_confidence_supported",
        "v22_pairwise_ranker",
        "v22_pairwise_winner",
    }
)


def _strict_bool(value: object, *, column: str) -> bool:
    """Parse booleans without Python's truthiness trap for strings."""
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        raise ValueError(f"{column} must be an explicit boolean")
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "t", "yes", "y", "1"}:
        return True
    if text in {"false", "f", "no", "n", "0"}:
        return False
    raise ValueError(f"{column} must be an explicit boolean")


def _members(value: object) -> tuple[str, ...]:
    if value is None or pd.isna(value):
        return ()
    text = str(value).strip()
    if not text:
        return ()
    members = tuple(part.strip() for part in text.split("+") if part.strip())
    if len(set(members)) != len(members):
        raise ValueError("supported_set contains duplicate members")
    return members


def _normalize_contexts(context_sets: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(_CONTEXT_COLUMNS) - set(context_sets.columns))
    if missing:
        raise KeyError("context sets missing columns: " + ", ".join(missing))
    frame = context_sets.loc[:, _CONTEXT_COLUMNS].copy()
    frame["family"] = frame["family"].astype(str)
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    frame["supported_set"] = frame["supported_set"].fillna("").astype(str)
    frame["supported_set_size"] = pd.to_numeric(
        frame["supported_set_size"], errors="raise"
    ).astype(int)
    keys = ["family", "seed", "target_block"]
    if frame.duplicated(keys).any():
        raise ValueError("duplicate v23 context key")
    for row in frame.itertuples(index=False):
        members = _members(row.supported_set)
        if int(row.supported_set_size) != len(members):
            raise ValueError("supported_set_size does not match supported_set members")
    return frame


def _normalize_evidence(
    evidence: pd.DataFrame,
    *,
    forbidden_source_ids: Collection[str],
) -> pd.DataFrame:
    missing = sorted(set(_EVIDENCE_COLUMNS) - set(evidence.columns))
    if missing:
        raise KeyError("separating evidence missing columns: " + ", ".join(missing))
    frame = evidence.loc[:, _EVIDENCE_COLUMNS].copy()
    frame["family"] = frame["family"].astype(str)
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    frame["target_process"] = frame["target_process"].astype(str).str.strip()
    frame["action"] = frame["action"].astype(str).str.strip().str.lower()
    frame["evidence_source_id"] = frame["evidence_source_id"].astype(str).str.strip()

    unknown_actions = sorted(set(frame["action"]) - _ALLOWED_ACTIONS)
    if unknown_actions:
        raise ValueError("action must be one of retain, remove, abstain")
    if frame["target_process"].eq("").any():
        raise ValueError("target_process must be nonempty")
    if frame["evidence_source_id"].eq("").any():
        raise ValueError("evidence_source_id must be nonempty")

    forbidden = {str(x) for x in forbidden_source_ids}
    reused = sorted(set(frame["evidence_source_id"]) & forbidden)
    if reused:
        raise ValueError("forbidden evidence source: " + ", ".join(reused))

    frame["evidence_is_new"] = [
        _strict_bool(v, column="evidence_is_new") for v in frame["evidence_is_new"]
    ]
    frame["evidence_is_separating"] = [
        _strict_bool(v, column="evidence_is_separating")
        for v in frame["evidence_is_separating"]
    ]
    if not frame["evidence_is_new"].all():
        raise ValueError("set contraction requires genuinely new evidence")
    if not frame["evidence_is_separating"].all():
        raise ValueError("set contraction requires separating evidence")
    return frame


def contract_supported_sets(
    context_sets: pd.DataFrame,
    evidence: pd.DataFrame,
    *,
    forbidden_source_ids: Collection[str] = _DEFAULT_FORBIDDEN_SOURCE_IDS,
) -> pd.DataFrame:
    """Contract v23 multi-member sets using only independent separating evidence.

    The function is fail-closed.  It cannot add a process, cannot act on an
    empty/singleton set, and cannot delete every member of a set.  Known-truth
    columns, if present in either input, are intentionally excluded before any
    decision is made.
    """
    contexts = _normalize_contexts(context_sets)
    ev = _normalize_evidence(evidence, forbidden_source_ids=forbidden_source_ids)
    keys = ["family", "seed", "target_block"]

    context_members: dict[tuple[str, int, int], tuple[str, ...]] = {}
    for row in contexts.itertuples(index=False):
        key = (str(row.family), int(row.seed), int(row.target_block))
        context_members[key] = _members(row.supported_set)

    # Reject evidence for unknown/ineligible contexts or unsupported processes
    # before checking completeness, so no new process can enter the v23 set.
    for row in ev.itertuples(index=False):
        key = (str(row.family), int(row.seed), int(row.target_block))
        members = context_members.get(key)
        if members is None or str(row.target_process) not in set(members):
            raise ValueError("evidence targets a process outside v23 supported set")
        if len(members) < 2:
            raise ValueError("separating evidence may act only on multi-member v23 sets")

    grouped = {
        (str(key[0]), int(key[1]), int(key[2])): group.copy()
        for key, group in ev.groupby(keys, sort=False)
    }

    rows: list[dict[str, object]] = []
    for row in contexts.itertuples(index=False):
        key = (str(row.family), int(row.seed), int(row.target_block))
        members = context_members[key]
        set_before = "+".join(members)

        if len(members) == 0:
            rows.append(
                {
                    "family": key[0],
                    "seed": key[1],
                    "target_block": key[2],
                    "set_before": set_before,
                    "contracted_set": set_before,
                    "removed_members": "",
                    "set_size_before": 0,
                    "set_size_after": 0,
                    "contraction_state": "unchanged_empty",
                    "evidence_source_id": "",
                }
            )
            continue

        if len(members) == 1:
            rows.append(
                {
                    "family": key[0],
                    "seed": key[1],
                    "target_block": key[2],
                    "set_before": set_before,
                    "contracted_set": set_before,
                    "removed_members": "",
                    "set_size_before": 1,
                    "set_size_after": 1,
                    "contraction_state": "unchanged_singleton",
                    "evidence_source_id": "",
                }
            )
            continue

        group = grouped.get(key)
        if group is None:
            raise ValueError("multi-member context requires exactly one action per supported member")
        counts = group["target_process"].value_counts()
        if set(counts.index) != set(members) or not counts.eq(1).all():
            raise ValueError("multi-member context requires exactly one action per supported member")
        source_ids = tuple(dict.fromkeys(group["evidence_source_id"].astype(str)))
        if len(source_ids) != 1:
            raise ValueError("one evidence_source_id is required per contracted context")
        source_id = source_ids[0]
        action_by_process = dict(zip(group["target_process"], group["action"], strict=True))
        removed = tuple(m for m in members if action_by_process[m] == "remove")
        kept = tuple(m for m in members if action_by_process[m] != "remove")
        has_abstention = any(action_by_process[m] == "abstain" for m in members)

        if not kept:
            contracted = members
            removed_effective: tuple[str, ...] = ()
            state = "fail_closed_all_remove"
        else:
            contracted = kept
            removed_effective = removed
            if removed:
                state = "contracted_with_abstention" if has_abstention else "contracted"
            elif has_abstention:
                state = "abstained"
            else:
                state = "unchanged_retained"

        rows.append(
            {
                "family": key[0],
                "seed": key[1],
                "target_block": key[2],
                "set_before": set_before,
                "contracted_set": "+".join(contracted),
                "removed_members": "+".join(removed_effective),
                "set_size_before": len(members),
                "set_size_after": len(contracted),
                "contraction_state": state,
                "evidence_source_id": source_id,
            }
        )

    return pd.DataFrame(rows)
