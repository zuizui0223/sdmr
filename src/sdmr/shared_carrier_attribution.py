"""Outcome-blind shared-carrier attribution for ecological process challenges.

The baseline-relative process challenge learner can show that removing the
predictors declared for process P causes a material loss. That loss is not
uniquely attributable to P, however, when one of the removed predictors also
carries information about another declared process Q.

This module therefore separates a *challenge signal* from *unique process
attribution*. Shared-carrier evidence comes only from the frozen many-to-many
process registry and/or a predictor-only :class:`ProcessProxyAudit`. Ecological
outcomes, answer-check rows, suitability values and known truth never enter the
proxy audit itself.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

from .process_challenge_learner import CONTRIBUTORY, REQUIRED, ProcessChallengeFit
from .process_information_closure import normalize_process_information_registry
from .process_proxy_audit import ProcessProxyAudit, audit_process_proxy_reconstructability


CONTESTED_SHARED = "contested_shared_information"


@dataclass(frozen=True)
class SharedCarrierAttribution:
    """Attribution audit layered on top of a process challenge result."""

    process_summary: pd.DataFrame
    evidence: pd.DataFrame
    proxy_audit: ProcessProxyAudit | None
    minimum_univariate_cv_r2: float
    minimum_abs_spearman: float
    selection_receipt: str


def _literal_bool(value: object) -> bool:
    return bool(value) if isinstance(value, (bool, np.bool_)) else False


def _statistical_shared(
    *,
    univariate_cv_r2: float,
    abs_spearman: float,
    minimum_univariate_cv_r2: float,
    minimum_abs_spearman: float,
) -> bool:
    r2_pass = np.isfinite(univariate_cv_r2) and univariate_cv_r2 >= minimum_univariate_cv_r2
    rho_pass = np.isfinite(abs_spearman) and abs_spearman >= minimum_abs_spearman
    return bool(r2_pass or rho_pass)


def attribute_shared_carrier_process_summary(
    process_summary: pd.DataFrame,
    process_registry: pd.DataFrame,
    *,
    process_universe: Sequence[str],
    predictor_universe: Sequence[str],
    proxy_candidate_summary: pd.DataFrame | None = None,
    minimum_univariate_cv_r2: float = 0.25,
    minimum_abs_spearman: float = 0.50,
) -> SharedCarrierAttribution:
    """Downgrade non-unique challenge signals to ``contested_shared_information``.

    The defaults are development heuristics, not prospectively validated
    performance thresholds. They must be frozen before any future validation
    denominator is run.

    A challenged process is contested when its v3 status is ``contributory`` or
    ``required`` and at least one predictor removed by that challenge either:

    1. is already declared to carry another process in the many-to-many registry;
       or
    2. reconstructs another process anchor in the outcome-blind proxy audit with
       CV R2 >= ``minimum_univariate_cv_r2`` or absolute Spearman >=
       ``minimum_abs_spearman``.

    ``replaceable`` and ``unresolved`` statuses are never upgraded or downgraded
    by this layer because they do not make a uniquely attributed contribution or
    necessity claim in the first place.
    """
    if not 0.0 <= float(minimum_univariate_cv_r2) <= 1.0:
        raise ValueError("minimum_univariate_cv_r2 must be in [0, 1]")
    if not 0.0 <= float(minimum_abs_spearman) <= 1.0:
        raise ValueError("minimum_abs_spearman must be in [0, 1]")

    required_columns = {"process", "status"}
    missing = sorted(required_columns - set(process_summary.columns))
    if missing:
        raise KeyError("process_summary missing columns: " + ", ".join(missing))

    processes = tuple(str(x).strip() for x in process_universe)
    predictors = tuple(str(x).strip() for x in predictor_universe)
    if not processes or len(set(processes)) != len(processes):
        raise ValueError("process_universe must contain unique non-empty values")
    if not predictors or len(set(predictors)) != len(predictors):
        raise ValueError("predictor_universe must contain unique non-empty values")

    summary = process_summary.copy(deep=True)
    if summary["process"].astype(str).duplicated().any():
        raise ValueError("process_summary must contain one row per process")
    unknown = sorted(set(summary["process"].astype(str)) - set(processes))
    if unknown:
        raise ValueError("process_summary contains undeclared processes: " + ", ".join(unknown))

    registry = normalize_process_information_registry(
        process_registry.copy(deep=True),
        process_universe=processes,
        predictor_universe=predictors,
    )

    proxy = pd.DataFrame()
    if proxy_candidate_summary is not None:
        proxy = proxy_candidate_summary.copy(deep=True)
        expected_proxy_columns = {
            "target_process",
            "candidate_predictor",
            "univariate_cv_r2",
            "abs_spearman",
        }
        missing_proxy = sorted(expected_proxy_columns - set(proxy.columns))
        if missing_proxy:
            raise KeyError("proxy_candidate_summary missing columns: " + ", ".join(missing_proxy))
        proxy["target_process"] = proxy["target_process"].astype(str)
        proxy["candidate_predictor"] = proxy["candidate_predictor"].astype(str)
        proxy["univariate_cv_r2"] = pd.to_numeric(proxy["univariate_cv_r2"], errors="coerce")
        proxy["abs_spearman"] = pd.to_numeric(proxy["abs_spearman"], errors="coerce")
        unknown_targets = sorted(set(proxy["target_process"]) - set(processes))
        if unknown_targets:
            raise ValueError("proxy audit contains undeclared target processes: " + ", ".join(unknown_targets))
        unknown_predictors = sorted(set(proxy["candidate_predictor"]) - set(predictors))
        if unknown_predictors:
            raise ValueError("proxy audit contains undeclared candidate predictors: " + ", ".join(unknown_predictors))

    evidence_rows: list[dict[str, object]] = []
    output_rows: list[dict[str, object]] = []
    for row in summary.to_dict(orient="records"):
        process = str(row["process"])
        challenge_status = str(row["status"])
        removed = tuple(
            dict.fromkeys(
                registry.loc[registry["process"].astype(str).eq(process), "predictor"].astype(str)
            )
        )

        # Registry-declared many-to-many carriers are definitive attribution
        # ambiguity: removing process P also removes a predictor explicitly
        # declared to carry process Q.
        for predictor in removed:
            declared_processes = tuple(
                sorted(
                    set(
                        registry.loc[
                            registry["predictor"].astype(str).eq(predictor), "process"
                        ].astype(str)
                    )
                    - {process}
                )
            )
            for other_process in declared_processes:
                evidence_rows.append(
                    {
                        "challenged_process": process,
                        "carrier_predictor": predictor,
                        "other_process": other_process,
                        "evidence_source": "declared_many_to_many",
                        "univariate_cv_r2": float("nan"),
                        "abs_spearman": float("nan"),
                        "qualifies": True,
                    }
                )

        # Statistical shared-carrier evidence is outcome-blind. We look for a
        # predictor removed by challenge P that reconstructs the declared anchor
        # of another process Q.
        if not proxy.empty and removed:
            candidates = proxy.loc[
                proxy["candidate_predictor"].isin(removed)
                & ~proxy["target_process"].eq(process)
            ].copy()
            for candidate in candidates.itertuples(index=False):
                r2 = float(candidate.univariate_cv_r2)
                rho = float(candidate.abs_spearman)
                qualifies = _statistical_shared(
                    univariate_cv_r2=r2,
                    abs_spearman=rho,
                    minimum_univariate_cv_r2=float(minimum_univariate_cv_r2),
                    minimum_abs_spearman=float(minimum_abs_spearman),
                )
                evidence_rows.append(
                    {
                        "challenged_process": process,
                        "carrier_predictor": str(candidate.candidate_predictor),
                        "other_process": str(candidate.target_process),
                        "evidence_source": "predictor_only_reconstruction",
                        "univariate_cv_r2": r2,
                        "abs_spearman": rho,
                        "qualifies": bool(qualifies),
                    }
                )

        current_evidence = [x for x in evidence_rows if x["challenged_process"] == process]
        qualifying = [x for x in current_evidence if _literal_bool(x["qualifies"])]
        shared_contested = bool(qualifying and challenge_status in {CONTRIBUTORY, REQUIRED})
        attribution_status = CONTESTED_SHARED if shared_contested else challenge_status
        other_processes = sorted({str(x["other_process"]) for x in qualifying})
        carriers = sorted({str(x["carrier_predictor"]) for x in qualifying})
        r2_values = [float(x["univariate_cv_r2"]) for x in qualifying if np.isfinite(float(x["univariate_cv_r2"]))]
        rho_values = [float(x["abs_spearman"]) for x in qualifying if np.isfinite(float(x["abs_spearman"]))]

        enriched = dict(row)
        enriched.update(
            {
                "challenge_status": challenge_status,
                "attribution_status": attribution_status,
                "challenge_signal_detected": challenge_status in {CONTRIBUTORY, REQUIRED},
                "shared_information_contested": shared_contested,
                "unique_process_evidence": attribution_status in {CONTRIBUTORY, REQUIRED},
                "n_qualifying_shared_carriers": len(qualifying),
                "shared_carrier_predictors": ",".join(carriers),
                "shared_with_processes": ",".join(other_processes),
                "max_shared_univariate_cv_r2": max(r2_values) if r2_values else float("nan"),
                "max_shared_abs_spearman": max(rho_values) if rho_values else float("nan"),
            }
        )
        output_rows.append(enriched)

    evidence = pd.DataFrame(evidence_rows)
    if not evidence.empty:
        evidence = evidence.sort_values(
            ["challenged_process", "qualifies", "univariate_cv_r2", "abs_spearman", "carrier_predictor", "other_process"],
            ascending=[True, False, False, False, True, True],
            kind="mergesort",
        ).reset_index(drop=True)

    output = pd.DataFrame(output_rows)
    receipt_payload = "\n".join(
        [
            f"minimum_univariate_cv_r2={float(minimum_univariate_cv_r2):.12g}",
            f"minimum_abs_spearman={float(minimum_abs_spearman):.12g}",
            "attribution_status=" + output[["process", "attribution_status"]].to_csv(index=False),
            "qualifying_evidence="
            + (
                evidence.loc[evidence["qualifies"].astype(bool)].to_csv(index=False)
                if not evidence.empty
                else ""
            ),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return SharedCarrierAttribution(
        process_summary=output,
        evidence=evidence,
        proxy_audit=None,
        minimum_univariate_cv_r2=float(minimum_univariate_cv_r2),
        minimum_abs_spearman=float(minimum_abs_spearman),
        selection_receipt=receipt,
    )


def fit_shared_carrier_attribution(
    challenge_fit: ProcessChallengeFit,
    predictor_frame: pd.DataFrame,
    process_registry: pd.DataFrame,
    *,
    groups: Sequence[object] | None = None,
    n_splits: int = 5,
    degree: int = 2,
    minimum_univariate_cv_r2: float = 0.25,
    minimum_abs_spearman: float = 0.50,
) -> SharedCarrierAttribution:
    """Run an outcome-blind proxy audit and attribute a fitted v3 challenge.

    ``predictor_frame`` should normally be the background/environment predictor
    table available before any ecological outcome is inspected. Only the
    ecological predictor universe from ``challenge_fit`` enters the proxy audit.
    """
    predictors = tuple(challenge_fit.base_fit.ecological_predictors)
    processes = tuple(challenge_fit.base_fit.process_universe)
    audit = audit_process_proxy_reconstructability(
        predictor_frame,
        process_registry,
        process_universe=processes,
        predictor_universe=predictors,
        groups=groups,
        n_splits=int(n_splits),
        degree=int(degree),
    )
    attributed = attribute_shared_carrier_process_summary(
        challenge_fit.process_summary,
        process_registry,
        process_universe=processes,
        predictor_universe=predictors,
        proxy_candidate_summary=audit.candidate_summary,
        minimum_univariate_cv_r2=float(minimum_univariate_cv_r2),
        minimum_abs_spearman=float(minimum_abs_spearman),
    )
    receipt = hashlib.sha256(
        (
            "challenge_receipt=" + challenge_fit.selection_receipt + "\n"
            + "proxy_attribution_receipt=" + attributed.selection_receipt
        ).encode("utf-8")
    ).hexdigest()
    return SharedCarrierAttribution(
        process_summary=attributed.process_summary,
        evidence=attributed.evidence,
        proxy_audit=audit,
        minimum_univariate_cv_r2=attributed.minimum_univariate_cv_r2,
        minimum_abs_spearman=attributed.minimum_abs_spearman,
        selection_receipt=receipt,
    )
