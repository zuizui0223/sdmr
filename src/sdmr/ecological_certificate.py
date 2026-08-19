"""Set-valued ecological niche certificates for Product-A v2.3.

The certificate is constructed from a non-empty set of complete, predictively
adequate and ecologically non-dominated procedure × M fits. It deliberately does
not choose one member. Exact intersection/union semantics identify necessary,
possible, contested and unsupported process groups, while response optima and
limits are returned as min–max identified intervals.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .candidate_outer_fold_evidence import (
    CandidateOuterEvidenceResult,
    require_complete_outer_fold_evidence,
)
from .niche_recovery import _weighted_quantile
from .niche_recovery_selection import (
    RECOVERY_DIRECTIONS,
    select_generalization_gated_niche_recovery_protocol,
)


RESPONSE_QUANTITIES = ("optimum", "lower_limit", "upper_limit")


@dataclass(frozen=True)
class EcologicalCandidateSets:
    complete_candidates: tuple[str, ...]
    adequate_candidates: tuple[str, ...]
    ecological_pareto_candidates: tuple[str, ...]
    complete_evidence: CandidateOuterEvidenceResult


@dataclass(frozen=True)
class EcologicalCertificate:
    member_ids: tuple[str, ...]
    necessary_processes: tuple[str, ...]
    possible_processes: tuple[str, ...]
    contested_processes: tuple[str, ...]
    unsupported_processes: tuple[str, ...]
    boundary_intervals: pd.DataFrame

    @property
    def n_members(self) -> int:
        return len(self.member_ids)

    def process_summary(self) -> dict[str, object]:
        return {
            "n_members": self.n_members,
            "necessary_processes": ",".join(self.necessary_processes),
            "possible_processes": ",".join(self.possible_processes),
            "contested_processes": ",".join(self.contested_processes),
            "unsupported_processes": ",".join(self.unsupported_processes),
            "n_necessary_processes": len(self.necessary_processes),
            "n_possible_processes": len(self.possible_processes),
            "n_contested_processes": len(self.contested_processes),
            "n_unsupported_processes": len(self.unsupported_processes),
        }


def select_ecological_candidate_sets(
    metrics: pd.DataFrame,
    *,
    discovery_taxa: Sequence[str],
    perturbations: Sequence[str],
    expected_outer_folds: int,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
) -> EcologicalCandidateSets:
    """Return complete, adequate and ecological-Pareto candidate sets.

    The selected single candidate embedded in the legacy selector result is
    ignored. Product-A v2.3 retains the entire recovery Pareto front.
    """

    required = ("presence_rank", *tuple(RECOVERY_DIRECTIONS))
    complete = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=tuple(discovery_taxa),
        perturbations=tuple(perturbations),
        required_columns=required,
        expected_outer_folds=int(expected_outer_folds),
    )
    if not complete.eligible_candidates:
        return EcologicalCandidateSets((), (), (), complete)

    complete_set = set(complete.eligible_candidates)
    eligible_metrics = metrics.loc[
        metrics["candidate"].astype(str).isin(complete_set)
    ].copy()
    try:
        staged = select_generalization_gated_niche_recovery_protocol(
            eligible_metrics,
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
            max_mean_or10=max_mean_or10,
        )
    except ValueError:
        return EcologicalCandidateSets(
            tuple(sorted(complete_set)),
            (),
            (),
            complete,
        )
    adequate = tuple(sorted(str(x) for x in staged.eligible_candidates))
    pareto = tuple(
        sorted(str(x) for x in staged.recovery_selection.pareto_front)
    )
    return EcologicalCandidateSets(
        tuple(sorted(complete_set)),
        adequate,
        pareto,
        complete,
    )


def _quantile_bin_optimum(
    values: np.ndarray,
    suitability: np.ndarray,
    *,
    n_bins: int,
) -> float:
    if int(n_bins) < 4:
        raise ValueError("n_bins must be >= 4")
    edges = np.unique(np.quantile(values, np.linspace(0.0, 1.0, n_bins + 1)))
    if len(edges) < 3:
        return float(np.average(values, weights=suitability))
    edges = edges.astype(float)
    edges[0] -= 1e-12 * max(1.0, abs(float(edges[0])))
    edges[-1] += 1e-12 * max(1.0, abs(float(edges[-1])))
    centers: list[float] = []
    means: list[float] = []
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (values >= lower) & (values < upper)
        if not np.any(mask):
            continue
        centers.append(float(np.mean(values[mask])))
        means.append(float(np.mean(suitability[mask])))
    if not means:
        return float(np.average(values, weights=suitability))
    return centers[int(np.argmax(means))]


def response_point_estimates(
    environment: pd.DataFrame,
    suitability: Sequence[float] | np.ndarray,
    response_predictors: Sequence[str],
    *,
    member_id: str,
    lower_mass: float = 0.05,
    upper_mass: float = 0.95,
    n_bins: int = 20,
) -> pd.DataFrame:
    """Return optimum and lower/upper response limits for one fitted member."""

    if not 0 <= float(lower_mass) < float(upper_mass) <= 1:
        raise ValueError("response masses must satisfy 0 <= lower < upper <= 1")
    predictors = tuple(dict.fromkeys(str(x) for x in response_predictors))
    missing = sorted(set(predictors) - set(environment.columns))
    if missing:
        raise KeyError(f"environment missing response predictors: {missing}")
    weights = np.asarray(suitability, dtype=float)
    if weights.ndim != 1 or len(weights) != len(environment):
        raise ValueError("suitability must align with environment")

    rows: list[dict[str, object]] = []
    for predictor in predictors:
        values = pd.to_numeric(environment[predictor], errors="coerce").to_numpy(
            float
        )
        keep = np.isfinite(values) & np.isfinite(weights) & (weights >= 0)
        x = values[keep]
        w = weights[keep]
        if len(x) < 5 or float(w.sum()) <= 0:
            for quantity in RESPONSE_QUANTITIES:
                rows.append(
                    {
                        "member_id": str(member_id),
                        "predictor": predictor,
                        "quantity": quantity,
                        "estimate": float("nan"),
                        "environment_span": float("nan"),
                    }
                )
            continue
        span = float(np.max(x) - np.min(x))
        normalized = w / w.sum()
        lower, upper = _weighted_quantile(
            x,
            normalized,
            (float(lower_mass), float(upper_mass)),
        )
        optimum = _quantile_bin_optimum(x, w, n_bins=int(n_bins))
        for quantity, estimate in (
            ("optimum", optimum),
            ("lower_limit", float(lower)),
            ("upper_limit", float(upper)),
        ):
            rows.append(
                {
                    "member_id": str(member_id),
                    "predictor": predictor,
                    "quantity": quantity,
                    "estimate": float(estimate),
                    "environment_span": span,
                }
            )
    return pd.DataFrame(rows)


def build_ecological_certificate(
    member_processes: Mapping[str, Sequence[str]],
    member_response_estimates: pd.DataFrame,
    *,
    process_universe: Sequence[str],
) -> EcologicalCertificate:
    """Build exact process sets and response intervals without a winner."""

    members = tuple(sorted(str(x) for x in member_processes))
    if not members:
        raise ValueError("certificate requires at least one retained member")
    universe = set(str(x) for x in process_universe)
    process_sets = {
        member: set(str(x) for x in member_processes[member])
        for member in members
    }
    unknown = sorted(set().union(*process_sets.values()) - universe)
    if unknown:
        raise ValueError(f"member processes absent from universe: {unknown}")

    necessary = set.intersection(*(process_sets[member] for member in members))
    possible = set.union(*(process_sets[member] for member in members))
    contested = possible - necessary
    unsupported = universe - possible

    required_columns = {
        "member_id",
        "predictor",
        "quantity",
        "estimate",
        "environment_span",
    }
    missing_columns = sorted(required_columns - set(member_response_estimates.columns))
    if missing_columns:
        raise KeyError(
            f"member response estimates missing columns: {missing_columns}"
        )
    response = member_response_estimates.copy()
    response["member_id"] = response["member_id"].astype(str)
    response = response.loc[response["member_id"].isin(set(members))].copy()
    response["estimate"] = pd.to_numeric(response["estimate"], errors="coerce")
    response["environment_span"] = pd.to_numeric(
        response["environment_span"], errors="coerce"
    )
    intervals = (
        response.groupby(["predictor", "quantity"], as_index=False)
        .agg(
            lower_bound=("estimate", "min"),
            upper_bound=("estimate", "max"),
            environment_span=("environment_span", "max"),
            n_members_evaluable=("estimate", lambda values: int(np.isfinite(values).sum())),
        )
        .sort_values(["predictor", "quantity"], kind="mergesort")
        .reset_index(drop=True)
    )
    intervals["normalized_width"] = (
        (intervals["upper_bound"] - intervals["lower_bound"])
        / intervals["environment_span"].where(
            intervals["environment_span"] > 0,
            np.nan,
        )
    )
    intervals["n_retained_members"] = len(members)
    intervals["all_members_evaluable"] = (
        intervals["n_members_evaluable"] == len(members)
    )
    return EcologicalCertificate(
        member_ids=members,
        necessary_processes=tuple(sorted(necessary)),
        possible_processes=tuple(sorted(possible)),
        contested_processes=tuple(sorted(contested)),
        unsupported_processes=tuple(sorted(unsupported)),
        boundary_intervals=intervals,
    )


def audit_certificate_against_truth(
    certificate: EcologicalCertificate,
    *,
    true_processes: Sequence[str],
    truth_response_estimates: pd.DataFrame,
) -> tuple[dict[str, object], pd.DataFrame]:
    """Audit process identification, boundary coverage and certificate width."""

    truth_process = set(str(x) for x in true_processes)
    necessary = set(certificate.necessary_processes)
    possible = set(certificate.possible_processes)
    false_core = necessary - truth_process
    possible_true = possible & truth_process
    process_recall = (
        float(len(possible_true) / len(truth_process))
        if truth_process
        else float("nan")
    )
    process_precision = (
        float(len(possible_true) / len(possible)) if possible else 0.0
    )

    required_truth = {"predictor", "quantity", "estimate"}
    missing = sorted(required_truth - set(truth_response_estimates.columns))
    if missing:
        raise KeyError(f"truth response estimates missing columns: {missing}")
    truth = truth_response_estimates[list(required_truth)].copy()
    truth = truth.rename(columns={"estimate": "truth_estimate"})
    audit = certificate.boundary_intervals.merge(
        truth,
        on=["predictor", "quantity"],
        how="outer",
        validate="one_to_one",
    )
    audit["covered"] = (
        np.isfinite(pd.to_numeric(audit["truth_estimate"], errors="coerce"))
        & np.isfinite(pd.to_numeric(audit["lower_bound"], errors="coerce"))
        & np.isfinite(pd.to_numeric(audit["upper_bound"], errors="coerce"))
        & (
            pd.to_numeric(audit["truth_estimate"], errors="coerce")
            >= pd.to_numeric(audit["lower_bound"], errors="coerce") - 1e-12
        )
        & (
            pd.to_numeric(audit["truth_estimate"], errors="coerce")
            <= pd.to_numeric(audit["upper_bound"], errors="coerce") + 1e-12
        )
    )
    summary = {
        **certificate.process_summary(),
        "n_true_processes": len(truth_process),
        "n_false_necessary_processes": len(false_core),
        "false_necessary_processes": ",".join(sorted(false_core)),
        "possible_process_recall": process_recall,
        "possible_process_precision": process_precision,
        "n_boundaries": int(len(audit)),
        "n_boundaries_covered": int(audit["covered"].sum()),
        "boundary_coverage_fraction": (
            float(audit["covered"].mean()) if len(audit) else float("nan")
        ),
        "mean_normalized_interval_width": float(
            pd.to_numeric(audit["normalized_width"], errors="coerce").mean()
        ),
        "all_retained_members_boundary_evaluable": bool(
            audit["all_members_evaluable"].fillna(False).all()
        ),
    }
    return summary, audit


def audit_point_response_against_truth(
    point_response_estimates: pd.DataFrame,
    truth_response_estimates: pd.DataFrame,
) -> tuple[dict[str, object], pd.DataFrame]:
    """Return normalized absolute response error for one point-model comparator."""

    point = point_response_estimates[
        ["predictor", "quantity", "estimate", "environment_span"]
    ].rename(columns={"estimate": "point_estimate"})
    truth = truth_response_estimates[
        ["predictor", "quantity", "estimate"]
    ].rename(columns={"estimate": "truth_estimate"})
    audit = point.merge(
        truth,
        on=["predictor", "quantity"],
        how="outer",
        validate="one_to_one",
    )
    audit["normalized_absolute_error"] = (
        (
            pd.to_numeric(audit["point_estimate"], errors="coerce")
            - pd.to_numeric(audit["truth_estimate"], errors="coerce")
        ).abs()
        / pd.to_numeric(audit["environment_span"], errors="coerce").where(
            pd.to_numeric(audit["environment_span"], errors="coerce") > 0,
            np.nan,
        )
    )
    finite = np.isfinite(
        pd.to_numeric(audit["normalized_absolute_error"], errors="coerce")
    )
    return (
        {
            "n_point_boundaries": int(len(audit)),
            "n_point_boundaries_evaluable": int(finite.sum()),
            "mean_normalized_absolute_error": float(
                pd.to_numeric(
                    audit.loc[finite, "normalized_absolute_error"],
                    errors="coerce",
                ).mean()
            ),
        },
        audit,
    )
