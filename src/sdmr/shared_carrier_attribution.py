"""Shared-carrier attribution for ecological process challenges.

The baseline-relative process challenge learner can show that removing the
predictors declared for process P causes a material loss. That loss is not
uniquely attributable to P, however, when a removed predictor also carries
information about another declared process Q *and Q itself has an outcome-level
challenge signal in the same fitted evidence set*.

The predictor-sharing audit remains outcome-blind: it uses only the frozen
many-to-many registry and/or a predictor-only :class:`ProcessProxyAudit`. The
outcome-level v3 challenge result is consulted only afterwards to decide whether
a statistically shared process is relevant to attribution of the observed loss.
Answer-check rows and known truth never enter this layer.
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
    require_other_process_challenge_signal: bool
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
    require_other_process_challenge_signal: bool = True,
) -> SharedCarrierAttribution:
    """Downgrade non-unique challenge signals to ``contested_shared_information``.

    The numerical defaults are development heuristics, not prospectively
    validated performance thresholds. They must be frozen before any future
    validation denominator is run.

    A challenged process P is contested when its v3 status is ``contributory``
    or ``required`` and at least one predictor removed by that challenge either:

    1. is already declared to carry another process Q in the many-to-many
       registry; or
    2. reconstructs Q's anchor in the outcome-blind proxy audit with CV R2 >=
       ``minimum_univariate_cv_r2`` or absolute Spearman >=
       ``minimum_abs_spearman``;

    and, by default, Q itself has a ``contributory`` or ``required`` challenge
    signal in the same evidence set. The last condition distinguishes mere
    predictor covariance from shared information that can plausibly explain the
    observed challenge loss.

    ``replaceable`` and ``unresolved`` statuses are never upgraded or downgraded
    by this layer because they do not make a uniquely attributed contribution or
    necessity claim in the first place.
    """
    if not 0.0 <= float(minimum_univariate_cv_r2) <= 1.0:
        raise ValueError("minimum_univariate_cv_r2 must be in [0, 1]")
    if not 0.0 <= float(minimum_abs_spearman) <= 1.0:
        raise ValueError("minimum_abs_spearman must be in [0, 1]")
    if not isinstance(require_other_process_challenge_signal, bool):
        raise TypeError("require_other_process_challenge_signal must be a literal boolean")

    required_columns = {"process", "status"}
    missing = sorted(required_columns - set(process_summary.columns))
    if missing:
        raise KeyError("process_summary missing columns: " + ", ".join(missing))

    processes = tuple(str(x).strip() for x in process_universe)
    predictors = tuple(str(x).strip() for x in predictor_universe)
    if not processes or any(not x for x in processes) or len(set(processes)) != len(processes):
        raise ValueError("process_universe must contain unique non-empty values")
    if not predictors or any(not x for x in predictors) or len(set(predictors)) != len(predictors):
        raise ValueError("predictor_universe must contain unique non-empty values")

    summary = process_summary.copy(deep=True)
    summary["process"] = summary["process"].astype(str)
    summary["status"] = summary["status"].astype(str)
    if summary["process"].duplicated().any():
        raise ValueError("process_summary must contain one row per process")
    unknown = sorted(set(summary["process"]) - set(processes))
    if unknown:
        raise ValueError("process_summary contains undeclared processes: " + ", ".join(unknown))

    challenge_signal_by_process = {
        str(row.process): str(row.status) in {CONTRIBUTORY, REQUIRED}
        for row in summary[["process", "status"]].itertuples(index=False)
    }
    # Declared processes absent from the summary have no demonstrated challenge
    # signal and therefore cannot make shared information attribution-relevant.
    for process in processes:
        challenge_signal_by_process.setdefault(process, False)

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
                other_signal = bool(challenge_signal_by_process.get(other_process, False))
                relevant = bool((not require_other_process_challenge_signal) or other_signal)
                evidence_rows.append(
                    {
                        "challenged_process": process,
                        "carrier_predictor": predictor,
                        "other_process": other_process,
                        "evidence_source": "declared_many_to_many",
                        "univariate_cv_r2": float("nan"),
                        "abs_spearman": float("nan"),
                        "qualifies": True,
                        "other_process_challenge_signal": other_signal,
                        "attribution_relevant": relevant,
                    }
                )

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
                other_process = str(candidate.target_process)
                other_signal = bool(challenge_signal_by_process.get(other_process, False))
                relevant = bool(
                    qualifies
                    and ((not require_other_process_challenge_signal) or other_signal)
                )
                evidence_rows.append(
                    {
                        "challenged_process": process,
                        "carrier_predictor": str(candidate.candidate_predictor),
                        "other_process": other_process,
                        "evidence_source": "predictor_only_reconstruction",
                        "univariate_cv_r2": r2,
                        "abs_spearman": rho,
                        "qualifies": bool(qualifies),
                        "other_process_challenge_signal": other_signal,
                        "attribution_relevant": relevant,
                    }
                )

        current_evidence = [x for x in evidence_rows if x["challenged_process"] == process]
        qualifying = [x for x in current_evidence if _literal_bool(x["qualifies"])]
        relevant = [x for x in current_evidence if _literal_bool(x["attribution_relevant"])]
        shared_contested = bool(relevant and challenge_status in {CONTRIBUTORY, REQUIRED})
        attribution_status = CONTESTED_SHARED if shared_contested else challenge_status

        qualifying_other_processes = sorted({str(x["other_process"]) for x in qualifying})
        relevant_other_processes = sorted({str(x["other_process"]) for x in relevant})
        qualifying_carriers = sorted({str(x["carrier_predictor"]) for x in qualifying})
        relevant_carriers = sorted({str(x["carrier_predictor"]) for x in relevant})
        r2_values = [
            float(x["univariate_cv_r2"])
            for x in relevant
            if np.isfinite(float(x["univariate_cv_r2"]))
        ]
        rho_values = [
            float(x["abs_spearman"])
            for x in relevant
            if np.isfinite(float(x["abs_spearman"]))
        ]

        enriched = dict(row)
        enriched.update(
            {
                "challenge_status": challenge_status,
                "attribution_status": attribution_status,
                "challenge_signal_detected": challenge_status in {CONTRIBUTORY, REQUIRED},
                "shared_information_contested": shared_contested,
                "unique_process_evidence": attribution_status in {CONTRIBUTORY, REQUIRED},
                "n_qualifying_shared_carriers": len(qualifying),
                "n_attribution_relevant_shared_carriers": len(relevant),
                "qualifying_shared_carrier_predictors": ",".join(qualifying_carriers),
                "qualifying_shared_with_processes": ",".join(qualifying_other_processes),
                "shared_carrier_predictors": ",".join(relevant_carriers),
                "shared_with_processes": ",".join(relevant_other_processes),
                "max_shared_univariate_cv_r2": max(r2_values) if r2_values else float("nan"),
                "max_shared_abs_spearman": max(rho_values) if rho_values else float("nan"),
            }
        )
        output_rows.append(enriched)

    evidence = pd.DataFrame(evidence_rows)
    if not evidence.empty:
        evidence = evidence.sort_values(
            [
                "challenged_process",
                "attribution_relevant",
                "qualifies",
                "univariate_cv_r2",
                "abs_spearman",
                "carrier_predictor",
                "other_process",
            ],
            ascending=[True, False, False, False, False, True, True],
            kind="mergesort",
        ).reset_index(drop=True)

    output = pd.DataFrame(output_rows)
    receipt_payload = "\n".join(
        [
            f"minimum_univariate_cv_r2={float(minimum_univariate_cv_r2):.12g}",
            f"minimum_abs_spearman={float(minimum_abs_spearman):.12g}",
            f"require_other_process_challenge_signal={int(require_other_process_challenge_signal)}",
            "attribution_status=" + output[["process", "attribution_status"]].to_csv(index=False),
            "relevant_shared_evidence="
            + (
                evidence.loc[evidence["attribution_relevant"].astype(bool)].to_csv(index=False)
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
        require_other_process_challenge_signal=bool(require_other_process_challenge_signal),
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
    require_other_process_challenge_signal: bool = True,
) -> SharedCarrierAttribution:
    """Run predictor-only proxy audit, then attribute a fitted v3 challenge."""
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
        require_other_process_challenge_signal=require_other_process_challenge_signal,
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
        require_other_process_challenge_signal=attributed.require_other_process_challenge_signal,
        selection_receipt=receipt,
    )
