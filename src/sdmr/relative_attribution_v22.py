"""Symmetric within-context relative attribution for v22 development.

This module is deliberately small. It consumes a frozen manifest of unordered
co-supported process pairs and two directional conditional-necessity results
for every pair. It does not inspect generating-process truth and does not tune
scientific thresholds.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations

import pandas as pd

P_FAVORED = "P_favored"
Q_FAVORED = "Q_favored"
COESSENTIAL = "coessential"
EXCHANGEABLE = "exchangeable"
UNRESOLVED = "unresolved"

DIRECTIONAL_POSITIVE = "conditional_contribution"
DIRECTIONAL_NEGATIVE = "no_revealed_conditional_contribution"
DIRECTIONAL_UNRESOLVED = "unresolved"


PAIR_COLUMNS = (
    "family",
    "seed",
    "target_block",
    "process_a",
    "process_b",
    "a_high_confidence_supported",
    "b_high_confidence_supported",
)


def build_supported_pair_manifest(
    context_decisions: pd.DataFrame,
    *,
    process_order: Sequence[str] = ("temperature", "water", "seasonality", "noise"),
) -> pd.DataFrame:
    """Build the frozen unordered-pair denominator from v21 support calls only.

    Generating truth is intentionally ignored even when present in the input.
    A context contributes C(k, 2) rows when k >= 2 processes are `supported`.
    """
    required = {
        "family",
        "seed",
        "target_process",
        "target_block",
        "supported",
        "high_confidence_supported",
    }
    missing = sorted(required - set(context_decisions.columns))
    if missing:
        raise KeyError("context decisions missing columns: " + ", ".join(missing))

    order = {str(p): i for i, p in enumerate(process_order)}
    rows: list[dict[str, object]] = []
    keys = ["family", "seed", "target_block"]
    frame = context_decisions.copy()
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    frame["supported"] = frame["supported"].astype(bool)
    frame["high_confidence_supported"] = frame["high_confidence_supported"].astype(bool)

    for (family, seed, target_block), group in frame.groupby(keys, sort=True):
        supported = group.loc[group["supported"]].copy()
        if len(supported) < 2:
            continue
        if supported["target_process"].astype(str).duplicated().any():
            raise ValueError("duplicate process row within context")
        unknown = sorted(set(supported["target_process"].astype(str)) - set(order))
        if unknown:
            raise ValueError("process outside frozen order: " + ", ".join(unknown))
        by_process = {str(r.target_process): r for r in supported.itertuples(index=False)}
        processes = sorted(by_process, key=order.__getitem__)
        for a, b in combinations(processes, 2):
            ra = by_process[a]
            rb = by_process[b]
            rows.append({
                "family": str(family),
                "seed": int(seed),
                "target_block": int(target_block),
                "process_a": a,
                "process_b": b,
                "a_high_confidence_supported": bool(ra.high_confidence_supported),
                "b_high_confidence_supported": bool(rb.high_confidence_supported),
            })
    return pd.DataFrame(rows, columns=PAIR_COLUMNS)


def classify_symmetric_pair(
    a_given_b: str,
    b_given_a: str,
) -> str:
    """Combine the two directional conditional-necessity results.

    `a_given_b` asks whether A still contributes after B is removed.
    `b_given_a` asks the exact mirror question. Any incomplete/ambiguous direction
    fails closed to `unresolved`.
    """
    allowed = {DIRECTIONAL_POSITIVE, DIRECTIONAL_NEGATIVE, DIRECTIONAL_UNRESOLVED}
    if str(a_given_b) not in allowed or str(b_given_a) not in allowed:
        raise ValueError("unknown directional evidence state")
    if DIRECTIONAL_UNRESOLVED in (str(a_given_b), str(b_given_a)):
        return UNRESOLVED
    a_pos = str(a_given_b) == DIRECTIONAL_POSITIVE
    b_pos = str(b_given_a) == DIRECTIONAL_POSITIVE
    if a_pos and b_pos:
        return COESSENTIAL
    if a_pos and not b_pos:
        return P_FAVORED
    if b_pos and not a_pos:
        return Q_FAVORED
    return EXCHANGEABLE


def extract_symmetric_pairwise_evidence(
    pair_manifest: pd.DataFrame,
    directional_evidence: pd.DataFrame,
) -> pd.DataFrame:
    """Require exactly one directional result in each direction for every pair.

    Directional evidence columns:
      family, seed, target_block, target_process, conditioned_on_process, state

    The returned table preserves the frozen unordered manifest and appends the
    two mirrored states plus a five-level symmetric pair status.
    """
    manifest_required = set(PAIR_COLUMNS[:5])
    missing = sorted(manifest_required - set(pair_manifest.columns))
    if missing:
        raise KeyError("pair manifest missing columns: " + ", ".join(missing))
    evidence_required = {
        "family",
        "seed",
        "target_block",
        "target_process",
        "conditioned_on_process",
        "state",
    }
    missing = sorted(evidence_required - set(directional_evidence.columns))
    if missing:
        raise KeyError("directional evidence missing columns: " + ", ".join(missing))

    evidence = directional_evidence.copy()
    evidence["seed"] = pd.to_numeric(evidence["seed"], errors="raise").astype(int)
    evidence["target_block"] = pd.to_numeric(evidence["target_block"], errors="raise").astype(int)
    key = ["family", "seed", "target_block", "target_process", "conditioned_on_process"]
    if evidence.duplicated(key).any():
        raise ValueError("duplicate directional evidence row")
    lookup: Mapping[tuple[object, ...], str] = {
        tuple(r[k] for k in key): str(r["state"])
        for _, r in evidence.iterrows()
    }

    rows: list[dict[str, object]] = []
    for _, pair in pair_manifest.iterrows():
        family = str(pair["family"])
        seed = int(pair["seed"])
        block = int(pair["target_block"])
        a = str(pair["process_a"])
        b = str(pair["process_b"])
        ka = (family, seed, block, a, b)
        kb = (family, seed, block, b, a)
        if ka not in lookup or kb not in lookup:
            raise ValueError(f"missing mirrored directional evidence for {family}/{seed}/{block}/{a}/{b}")
        a_state = lookup[ka]
        b_state = lookup[kb]
        row = dict(pair)
        row.update({
            "a_given_b_state": a_state,
            "b_given_a_state": b_state,
            "pair_status": classify_symmetric_pair(a_state, b_state),
        })
        rows.append(row)
    return pd.DataFrame(rows)
