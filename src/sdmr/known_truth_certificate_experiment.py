"""Known-truth audit for consensus-first ecological inference certificates.

The ecological certificate itself never sees hidden truth.  This development-only
module opens the generating processes *after* canonical and robust ecological
selectors have chosen candidates, then asks whether the certificate's stable
process core is a trustworthy strong claim and whether the union of supported
processes appropriately captures sensitivity.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .ecological_inference_certificate import build_ecological_inference_certificate
from .known_truth_response import DEFAULT_PROCESS_ALIASES
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, standard_known_truth_candidates
from .niche_recovery_cv import RecoveryCandidate


CANONICAL_ECOLOGY_SELECTOR = "canonical_replicated_observation_niche_recovery"
ROBUST_ECOLOGY_SELECTOR = "replicated_observation_perturbation_robust_niche_recovery"


def _true_processes_for_family(family: str) -> tuple[str, ...]:
    family = str(family)
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError(f"unknown known-truth family: {family!r}")
    if family == "omitted_driver":
        return ("soil", "temperature", "water")
    return ("temperature", "water")


def _process_profile(
    selected_processes: tuple[str, ...],
    true_processes: tuple[str, ...],
) -> dict[str, float]:
    selected = set(selected_processes)
    truth = set(true_processes)
    tp = len(selected & truth)
    precision = float(tp / len(selected)) if selected else 0.0
    recall = float(tp / len(truth)) if truth else float("nan")
    f1 = (
        float(2 * precision * recall / (precision + recall))
        if precision + recall > 0
        else 0.0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def audit_ecological_inference_certificates(
    selector_choices: pd.DataFrame,
    *,
    candidates: Mapping[str, RecoveryCandidate] | None = None,
    process_groups: Mapping[str, str] = DEFAULT_PROCESS_ALIASES,
    scenario_col: str = "scenario",
    seed_col: str = "seed",
    selector_col: str = "selector",
    candidate_col: str = "candidate",
) -> pd.DataFrame:
    """Build certificates from selector choices, then audit them against truth.

    ``selector_choices`` is expected to be the truth-free output of a known-truth
    selector experiment.  Hidden generating process sets are introduced only
    after the canonical/robust choices are pivoted and the certificate is built.
    """

    candidates = dict(candidates or standard_known_truth_candidates())
    required = {scenario_col, seed_col, selector_col, candidate_col}
    missing = required - set(selector_choices.columns)
    if missing:
        raise KeyError(f"selector choices missing columns: {sorted(missing)}")

    subset = selector_choices.loc[
        selector_choices[selector_col].isin(
            (CANONICAL_ECOLOGY_SELECTOR, ROBUST_ECOLOGY_SELECTOR)
        ),
        [scenario_col, seed_col, selector_col, candidate_col],
    ].copy()
    pivot = subset.pivot(
        index=[scenario_col, seed_col], columns=selector_col, values=candidate_col
    ).reset_index()
    rows: list[dict[str, object]] = []
    for _, row in pivot.iterrows():
        scenario = str(row[scenario_col])
        canonical = row.get(CANONICAL_ECOLOGY_SELECTOR)
        robust = row.get(ROBUST_ECOLOGY_SELECTOR)
        canonical_name = None if pd.isna(canonical) else str(canonical)
        robust_name = None if pd.isna(robust) else str(robust)
        certificate = build_ecological_inference_certificate(
            canonical_name,
            robust_name,
            candidates,
            process_groups=process_groups,
        )

        # Hidden truth is opened only here, after the certificate exists.
        true_processes = _true_processes_for_family(scenario)
        core = _process_profile(certificate.stable_process_core, true_processes)
        union = _process_profile(certificate.process_union, true_processes)
        contested_true = tuple(sorted(set(certificate.contested_processes) & set(true_processes)))
        contested_false = tuple(sorted(set(certificate.contested_processes) - set(true_processes)))
        rows.append(
            {
                scenario_col: scenario,
                seed_col: int(row[seed_col]),
                **certificate.as_dict(),
                "true_processes": true_processes,
                "stable_core_precision": core["precision"],
                "stable_core_recall": core["recall"],
                "stable_core_f1": core["f1"],
                "process_union_precision": union["precision"],
                "process_union_recall": union["recall"],
                "process_union_f1": union["f1"],
                "contested_true_processes": contested_true,
                "contested_false_processes": contested_false,
            }
        )
    return pd.DataFrame(rows)
