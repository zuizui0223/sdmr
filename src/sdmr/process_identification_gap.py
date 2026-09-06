"""Compare occurrence-only process challenges with a truth-surface oracle.

The truth-surface oracle answers a representation-conditioned question using the
complete simulated suitability surface. The occurrence learner sees only its
allowed occurrence/background evidence. Their disagreement therefore defines an
*identification gap*; it is not automatically an algorithm error because the
sampling design and estimator can both limit what occurrence data identify.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import hashlib

import numpy as np
import pandas as pd

from .oracle_process_identifiability import (
    ORACLE_CONTESTED,
    ORACLE_CONTRIBUTORY,
    ORACLE_REPLACEABLE,
    ORACLE_REQUIRED,
    ORACLE_UNAVAILABLE,
)


@dataclass(frozen=True)
class ProcessIdentificationGap:
    comparison: pd.DataFrame
    overall_metrics: dict[str, float | int]
    by_process: pd.DataFrame
    by_family: pd.DataFrame
    selection_receipt: str


def _rate(num: int, den: int) -> float:
    return float(num / den) if den else float("nan")


def _metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    assessable = frame["oracle_assessable"].astype(bool).to_numpy()
    oracle_identifiable = frame["oracle_identifiable_signal"].astype(bool).to_numpy()
    oracle_replaceable = frame["oracle_status"].astype(str).eq(ORACLE_REPLACEABLE).to_numpy()
    challenge = frame["learner_challenge_signal"].astype(bool).to_numpy()
    unique = frame["learner_unique_attribution"].astype(bool).to_numpy()

    oracle_identifiable_n = int(np.sum(assessable & oracle_identifiable))
    oracle_replaceable_n = int(np.sum(assessable & oracle_replaceable))
    challenge_recovered = int(np.sum(assessable & oracle_identifiable & challenge))
    challenge_gap = int(np.sum(assessable & oracle_identifiable & ~challenge))
    challenge_over = int(np.sum(assessable & oracle_replaceable & challenge))
    unique_recovered = int(np.sum(assessable & oracle_identifiable & unique))
    unique_gap = int(np.sum(assessable & oracle_identifiable & ~unique))
    unique_over = int(np.sum(assessable & oracle_replaceable & unique))

    return {
        "n_rows": int(len(frame)),
        "n_oracle_assessable": int(assessable.sum()),
        "n_oracle_identifiable": oracle_identifiable_n,
        "n_oracle_replaceable": oracle_replaceable_n,
        "challenge_recovered_oracle_identifiable": challenge_recovered,
        "challenge_identification_gap": challenge_gap,
        "challenge_recall_against_oracle": _rate(challenge_recovered, oracle_identifiable_n),
        "challenge_gap_rate": _rate(challenge_gap, oracle_identifiable_n),
        "challenge_overchallenge": challenge_over,
        "challenge_overchallenge_rate": _rate(challenge_over, oracle_replaceable_n),
        "unique_recovered_oracle_identifiable": unique_recovered,
        "unique_identification_gap": unique_gap,
        "unique_recall_against_oracle": _rate(unique_recovered, oracle_identifiable_n),
        "unique_gap_rate": _rate(unique_gap, oracle_identifiable_n),
        "unique_overattribution": unique_over,
        "unique_overattribution_rate": _rate(unique_over, oracle_replaceable_n),
    }


def compare_process_identification_to_oracle(
    learner_process_evaluation: pd.DataFrame,
    oracle_process_evaluation: pd.DataFrame,
    *,
    key_columns: Sequence[str] = ("family", "seed", "process"),
) -> ProcessIdentificationGap:
    """Crosswalk occurrence-learner outputs against representation oracle labels."""
    keys = tuple(str(x) for x in key_columns)
    if not keys:
        raise ValueError("key_columns must be non-empty")
    learner_required = set(keys) | {"challenge_signal_detected", "unique_process_evidence"}
    oracle_required = set(keys) | {"oracle_status", "oracle_identifiable_signal"}
    missing_learner = sorted(learner_required - set(learner_process_evaluation.columns))
    missing_oracle = sorted(oracle_required - set(oracle_process_evaluation.columns))
    if missing_learner:
        raise KeyError("learner evaluation missing columns: " + ", ".join(missing_learner))
    if missing_oracle:
        raise KeyError("oracle evaluation missing columns: " + ", ".join(missing_oracle))

    learner = learner_process_evaluation.copy(deep=True)
    oracle = oracle_process_evaluation.copy(deep=True)
    if learner.duplicated(list(keys)).any():
        raise ValueError("learner evaluation contains duplicate process keys")
    if oracle.duplicated(list(keys)).any():
        raise ValueError("oracle evaluation contains duplicate process keys")

    learner_keep = list(keys) + ["challenge_signal_detected", "unique_process_evidence"]
    optional = [
        "attribution_status",
        "challenge_status",
        "expected_true_process",
    ]
    learner_keep += [column for column in optional if column in learner.columns]
    oracle_keep = list(keys) + ["oracle_status", "oracle_identifiable_signal"]
    optional_oracle = [
        "mean_paired_r2_loss",
        "mean_process_free_r2",
        "generating_process",
    ]
    oracle_keep += [column for column in optional_oracle if column in oracle.columns]

    merged = learner[learner_keep].merge(
        oracle[oracle_keep],
        on=list(keys),
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        bad = merged.loc[~merged["_merge"].eq("both"), list(keys) + ["_merge"]]
        raise ValueError("learner/oracle key universes differ:\n" + bad.to_csv(index=False))
    merged = merged.drop(columns="_merge")
    merged = merged.rename(
        columns={
            "challenge_signal_detected": "learner_challenge_signal",
            "unique_process_evidence": "learner_unique_attribution",
        }
    )
    merged["learner_challenge_signal"] = merged["learner_challenge_signal"].astype(bool)
    merged["learner_unique_attribution"] = merged["learner_unique_attribution"].astype(bool)
    merged["oracle_identifiable_signal"] = merged["oracle_identifiable_signal"].astype(bool)
    merged["oracle_assessable"] = ~merged["oracle_status"].astype(str).isin(
        {ORACLE_CONTESTED, ORACLE_UNAVAILABLE}
    )
    merged["challenge_identification_gap"] = (
        merged["oracle_assessable"]
        & merged["oracle_identifiable_signal"]
        & ~merged["learner_challenge_signal"]
    )
    merged["unique_identification_gap"] = (
        merged["oracle_assessable"]
        & merged["oracle_identifiable_signal"]
        & ~merged["learner_unique_attribution"]
    )
    merged["challenge_overchallenge"] = (
        merged["oracle_assessable"]
        & merged["oracle_status"].astype(str).eq(ORACLE_REPLACEABLE)
        & merged["learner_challenge_signal"]
    )
    merged["unique_overattribution"] = (
        merged["oracle_assessable"]
        & merged["oracle_status"].astype(str).eq(ORACLE_REPLACEABLE)
        & merged["learner_unique_attribution"]
    )

    overall = _metrics(merged)
    process_rows = []
    if "process" in merged.columns:
        for process, group in merged.groupby("process", sort=True):
            row = {"process": process}
            row.update(_metrics(group))
            process_rows.append(row)
    family_rows = []
    if "family" in merged.columns:
        for family, group in merged.groupby("family", sort=True):
            row = {"family": family}
            row.update(_metrics(group))
            family_rows.append(row)

    comparison = merged.sort_values(list(keys), kind="mergesort").reset_index(drop=True)
    receipt_payload = "\n".join(
        [
            "keys=" + ",".join(keys),
            "comparison=" + comparison.to_csv(index=False),
            "overall=" + pd.Series(overall).to_json(),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return ProcessIdentificationGap(
        comparison=comparison,
        overall_metrics=overall,
        by_process=pd.DataFrame(process_rows),
        by_family=pd.DataFrame(family_rows),
        selection_receipt=receipt,
    )
