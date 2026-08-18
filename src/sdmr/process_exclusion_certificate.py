"""Falsification-first process and boundary certificates for Product-A v2.4.

The v2.3 certificate treated the intersection of retained fitted process sets as
necessity and the min--max spread among final members as an uncertainty interval.
Known-truth validation showed that both operations can be anti-conservative.

This module implements the v2.4 replacements without reading validation truth:

* explicit process knockouts rerun each base procedure after every predictor and
  proxy assigned to one ecological process has been removed;
* complete outer-fold evidence and an absolute prediction-adequacy gate freeze
  which knockouts are admissible from discovery data;
* process necessity is refuted by a complete transferred knockout witness, while
  missing evidence remains unresolved rather than being converted to necessity;
* response intervals use every expected procedure x M x spatial-refit member;
* interval expansion is calibrated from discovery truth only and then applied to
  validation envelopes without access to validation outcomes.

``required_by_frozen_evidence_contract`` is deliberately contract-relative.  It
is not a physiological, causal or fundamental-niche necessity claim.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence


KNOCKOUT_SEPARATOR = "::exclude::"
DISCOVERY_PROCESS_STATES = (
    "exclusion_witness_frozen",
    "required_by_frozen_discovery_contract",
    "unresolved_discovery_evidence",
)
VALIDATION_PROCESS_STATES = (
    "refuted_as_necessary",
    "required_by_frozen_evidence_contract",
    "unresolved",
)
RESPONSE_QUANTITIES = ("optimum", "lower_limit", "upper_limit")


@dataclass(frozen=True)
class KnockoutDiscoveryEvidence:
    registry: pd.DataFrame
    candidate_summary: pd.DataFrame
    process_summary: pd.DataFrame
    cell_ledger: pd.DataFrame
    chance_auc: float
    auc_mean_floor: float
    auc_sem_multiplier: float


def _unique_strings(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(str(value) for value in values))
    if not result:
        raise ValueError(f"{name} must be non-empty")
    if len(result) != len(tuple(values)):
        raise ValueError(f"{name} must not contain duplicates")
    if any(not value for value in result):
        raise ValueError(f"{name} must not contain empty strings")
    return result


def knockout_candidate_label(
    base_candidate: str,
    excluded_process: str,
    *,
    separator: str = KNOCKOUT_SEPARATOR,
) -> str:
    """Return the deterministic label for one base-procedure process knockout."""

    base = str(base_candidate)
    process = str(excluded_process)
    if not base or not process:
        raise ValueError("base_candidate and excluded_process must be non-empty")
    if separator in base or separator in process:
        raise ValueError("knockout label components contain the reserved separator")
    return f"{base}{separator}{process}"


def freeze_process_knockout_registry(
    *,
    base_candidates: Sequence[str],
    ecological_predictors: Sequence[str],
    process_aliases: Mapping[str, str],
    process_universe: Sequence[str],
    observation_predictors: Sequence[str] = (),
) -> pd.DataFrame:
    """Construct the complete pre-outcome base x process knockout registry.

    Every ecological predictor must map to exactly one declared ecological
    process.  Observation predictors must map to ``observation_process`` and are
    retained in every knockout.  Unknown roles fail closed.
    """

    bases = _unique_strings(base_candidates, name="base_candidates")
    ecological = _unique_strings(ecological_predictors, name="ecological_predictors")
    processes = _unique_strings(process_universe, name="process_universe")
    observation = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    overlap = sorted(set(ecological) & set(observation))
    if overlap:
        raise ValueError(
            "predictors cannot be both ecological and observational: "
            + ", ".join(overlap)
        )

    aliases = {str(key): str(value) for key, value in process_aliases.items()}
    missing_aliases = sorted(set(ecological) - set(aliases))
    if missing_aliases:
        raise KeyError(
            "ecological predictors missing frozen process aliases: "
            + ", ".join(missing_aliases)
        )
    unknown_processes = sorted({aliases[p] for p in ecological} - set(processes))
    if unknown_processes:
        raise ValueError(
            "ecological predictors map outside the frozen process universe: "
            + ", ".join(unknown_processes)
        )
    bad_observation = sorted(
        predictor
        for predictor in observation
        if aliases.get(predictor) != "observation_process"
    )
    if bad_observation:
        raise ValueError(
            "observation predictors must map to observation_process: "
            + ", ".join(bad_observation)
        )

    predictors_by_process = {
        process: tuple(p for p in ecological if aliases[p] == process)
        for process in processes
    }
    empty_processes = [
        process for process, predictors in predictors_by_process.items() if not predictors
    ]
    if empty_processes:
        raise ValueError(
            "every frozen process requires at least one predictor: "
            + ", ".join(empty_processes)
        )

    rows: list[dict[str, object]] = []
    for base in bases:
        if KNOCKOUT_SEPARATOR in base:
            raise ValueError(
                f"base candidate contains reserved separator {KNOCKOUT_SEPARATOR!r}: {base}"
            )
        for process in processes:
            excluded = predictors_by_process[process]
            retained = tuple(p for p in ecological if p not in set(excluded))
            if not retained:
                raise ValueError(
                    f"excluding process {process!r} leaves no ecological predictor"
                )
            rows.append(
                {
                    "candidate": knockout_candidate_label(base, process),
                    "base_candidate": base,
                    "excluded_process": process,
                    "excluded_predictors": ",".join(excluded),
                    "retained_ecological_predictors": ",".join(retained),
                    "observation_predictors": ",".join(observation),
                    "n_excluded_predictors": len(excluded),
                    "n_retained_ecological_predictors": len(retained),
                }
            )
    registry = pd.DataFrame(rows)
    expected = len(bases) * len(processes)
    if len(registry) != expected or registry["candidate"].nunique() != expected:
        raise AssertionError("knockout registry is not a complete unique Cartesian product")
    return registry


def summarize_knockout_discovery_evidence(
    metrics: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    discovery_taxa: Sequence[str],
    perturbations: Sequence[str],
    expected_outer_folds: int,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    candidate_col: str = "candidate",
    auc_col: str = "presence_rank",
    fold_col: str = "fold",
) -> KnockoutDiscoveryEvidence:
    """Freeze complete and absolutely adequate process-knockout routes.

    A knockout is admitted when it has complete evidence in every discovery
    taxon x perturbation x outer-fold cell, its mean rank is at least chance plus
    the fixed margin, and its mean minus the fixed SEM multiple is at least
    chance.  It is never compared with the best AUC candidate.
    """

    chance_auc = float(chance_auc)
    minimum_auc_margin = float(minimum_auc_margin)
    auc_sem_multiplier = float(auc_sem_multiplier)
    if not 0 <= chance_auc < 1:
        raise ValueError("chance_auc must lie in [0, 1)")
    if minimum_auc_margin < 0 or chance_auc + minimum_auc_margin > 1:
        raise ValueError("minimum_auc_margin produces an invalid AUC floor")
    if auc_sem_multiplier < 0:
        raise ValueError("auc_sem_multiplier must be >= 0")

    registry_required = {
        "candidate",
        "base_candidate",
        "excluded_process",
        "excluded_predictors",
    }
    missing_registry = sorted(registry_required - set(registry.columns))
    if missing_registry:
        raise KeyError(f"knockout registry missing columns: {missing_registry}")
    if registry["candidate"].astype(str).duplicated().any():
        raise ValueError("knockout registry candidate labels must be unique")

    evidence = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=tuple(discovery_taxa),
        perturbations=tuple(perturbations),
        required_columns=(auc_col,),
        expected_outer_folds=int(expected_outer_folds),
        candidate_col=candidate_col,
        fold_col=fold_col,
    )
    evidence_summary = evidence.candidate_summary.rename(
        columns={candidate_col: "candidate"}
    )
    candidates = registry.copy()
    candidates["candidate"] = candidates["candidate"].astype(str)
    candidates = candidates.merge(
        evidence_summary,
        on="candidate",
        how="left",
        validate="one_to_one",
    )
    count_columns = (
        "n_required_cells",
        "n_complete_cells",
        "n_cells_with_complete_fold_ids",
        "n_cells_with_finite_required_columns",
    )
    for column in count_columns:
        if column not in candidates:
            candidates[column] = 0
        candidates[column] = (
            pd.to_numeric(candidates[column], errors="coerce").fillna(0).astype(int)
        )
    if "eligible_complete_outer_evidence" not in candidates:
        candidates["eligible_complete_outer_evidence"] = False
    candidates["complete_outer_evidence"] = candidates[
        "eligible_complete_outer_evidence"
    ].fillna(False).astype(bool)

    data = metrics.copy()
    data[candidate_col] = data[candidate_col].astype(str)
    data[auc_col] = pd.to_numeric(data[auc_col], errors="coerce")
    auc_rows: list[dict[str, object]] = []
    for candidate in candidates["candidate"]:
        values = data.loc[
            data[candidate_col].eq(candidate) & np.isfinite(data[auc_col]), auc_col
        ].to_numpy(float)
        mean_auc = float(np.mean(values)) if len(values) else float("nan")
        if len(values) >= 2:
            sem_auc = float(np.std(values, ddof=1) / np.sqrt(len(values)))
        elif len(values) == 1:
            sem_auc = 0.0
        else:
            sem_auc = float("nan")
        auc_rows.append(
            {
                "candidate": candidate,
                "mean_presence_rank": mean_auc,
                "sem_presence_rank": sem_auc,
                "n_presence_rank_values": int(len(values)),
            }
        )
    candidates = candidates.merge(
        pd.DataFrame(auc_rows),
        on="candidate",
        how="left",
        validate="one_to_one",
    )
    auc_floor = chance_auc + minimum_auc_margin
    candidates["auc_mean_floor"] = auc_floor
    candidates["auc_lower_evidence_bound"] = (
        candidates["mean_presence_rank"]
        - auc_sem_multiplier * candidates["sem_presence_rank"]
    )
    candidates["passes_auc_mean_floor"] = (
        np.isfinite(candidates["mean_presence_rank"])
        & (candidates["mean_presence_rank"] >= auc_floor - 1e-12)
    )
    candidates["passes_auc_chance_bound"] = (
        np.isfinite(candidates["auc_lower_evidence_bound"])
        & (candidates["auc_lower_evidence_bound"] >= chance_auc - 1e-12)
    )
    candidates["passes_absolute_prediction_gate"] = (
        candidates["passes_auc_mean_floor"]
        & candidates["passes_auc_chance_bound"]
    )
    candidates["admitted_knockout"] = (
        candidates["complete_outer_evidence"]
        & candidates["passes_absolute_prediction_gate"]
    )

    process_rows: list[dict[str, object]] = []
    for process, group in candidates.groupby("excluded_process", sort=True):
        declared = int(len(group))
        complete = int(group["complete_outer_evidence"].sum())
        admitted = int(group["admitted_knockout"].sum())
        if admitted > 0:
            state = "exclusion_witness_frozen"
        elif complete == declared:
            state = "required_by_frozen_discovery_contract"
        else:
            state = "unresolved_discovery_evidence"
        process_rows.append(
            {
                "process": str(process),
                "discovery_process_state": state,
                "n_declared_knockout_routes": declared,
                "n_complete_knockout_routes": complete,
                "n_admitted_knockout_routes": admitted,
                "all_declared_routes_complete": complete == declared,
                "admitted_knockout_candidates": ",".join(
                    sorted(
                        group.loc[group["admitted_knockout"], "candidate"].astype(str)
                    )
                ),
            }
        )
    process_summary = pd.DataFrame(process_rows)
    return KnockoutDiscoveryEvidence(
        registry=registry.copy(),
        candidate_summary=candidates.sort_values(
            ["excluded_process", "base_candidate"], kind="mergesort"
        ).reset_index(drop=True),
        process_summary=process_summary,
        cell_ledger=evidence.cell_ledger,
        chance_auc=chance_auc,
        auc_mean_floor=auc_floor,
        auc_sem_multiplier=auc_sem_multiplier,
    )


def classify_validation_process_exclusion(
    discovery: KnockoutDiscoveryEvidence,
    validation_fits: pd.DataFrame,
    *,
    validation_taxa: Sequence[str],
    perturbations: Sequence[str],
    candidate_col: str = "candidate",
    species_col: str = "species",
    perturbation_col: str = "perturbation",
    fit_status_col: str = "fit_status",
    success_value: str = "success",
) -> pd.DataFrame:
    """Return refuted, contract-required or unresolved status per taxon/process."""

    taxa = _unique_strings(validation_taxa, name="validation_taxa")
    specs = _unique_strings(perturbations, name="perturbations")
    required = {candidate_col, species_col, perturbation_col, fit_status_col}
    missing = sorted(required - set(validation_fits.columns))
    if missing:
        raise KeyError(f"validation fit ledger missing columns: {missing}")

    fits = validation_fits.copy()
    for column in (candidate_col, species_col, perturbation_col, fit_status_col):
        fits[column] = fits[column].astype(str)
    expected_specs = set(specs)
    candidate_summary = discovery.candidate_summary.copy()
    process_summary = discovery.process_summary.set_index("process")
    processes = tuple(process_summary.index.astype(str))

    rows: list[dict[str, object]] = []
    for species in taxa:
        for process in processes:
            admitted = tuple(
                sorted(
                    candidate_summary.loc[
                        candidate_summary["excluded_process"].astype(str).eq(process)
                        & candidate_summary["admitted_knockout"].astype(bool),
                        "candidate",
                    ].astype(str)
                )
            )
            complete_witnesses: list[str] = []
            incomplete_witnesses: list[str] = []
            for candidate in admitted:
                subset = fits.loc[
                    fits[candidate_col].eq(candidate)
                    & fits[species_col].eq(species)
                ]
                successful_specs = set(
                    subset.loc[
                        subset[fit_status_col].eq(str(success_value)),
                        perturbation_col,
                    ].astype(str)
                )
                if successful_specs == expected_specs:
                    complete_witnesses.append(candidate)
                else:
                    incomplete_witnesses.append(candidate)

            discovery_state = str(
                process_summary.loc[process, "discovery_process_state"]
            )
            if complete_witnesses:
                status = "refuted_as_necessary"
            elif discovery_state == "required_by_frozen_discovery_contract":
                status = "required_by_frozen_evidence_contract"
            else:
                status = "unresolved"
            rows.append(
                {
                    "species": species,
                    "process": process,
                    "process_status": status,
                    "discovery_process_state": discovery_state,
                    "n_admitted_knockout_routes": len(admitted),
                    "n_complete_transfer_witnesses": len(complete_witnesses),
                    "complete_transfer_witnesses": ",".join(complete_witnesses),
                    "incomplete_transfer_witnesses": ",".join(
                        incomplete_witnesses
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_complete_refit_envelope(
    response_estimates: pd.DataFrame,
    expected_members: pd.DataFrame,
    *,
    expected_response_keys: pd.DataFrame | None = None,
    species_col: str = "species",
    member_col: str = "member_id",
    predictor_col: str = "predictor",
    quantity_col: str = "quantity",
    estimate_col: str = "estimate",
    span_col: str = "environment_span",
) -> pd.DataFrame:
    """Build fail-closed min--max envelopes over every expected refit member.

    ``expected_members`` freezes the complete procedure x M x spatial-refit
    denominator.  ``expected_response_keys`` can additionally freeze the expected
    predictor x quantity rows per taxon; when omitted, keys are inferred from the
    supplied estimates.  Missing/non-finite members make that interval unavailable
    instead of narrowing it silently.
    """

    estimate_required = {
        species_col,
        member_col,
        predictor_col,
        quantity_col,
        estimate_col,
        span_col,
    }
    missing_estimate = sorted(estimate_required - set(response_estimates.columns))
    if missing_estimate:
        raise KeyError(f"response estimates missing columns: {missing_estimate}")
    member_required = {species_col, member_col}
    missing_members = sorted(member_required - set(expected_members.columns))
    if missing_members:
        raise KeyError(f"expected member ledger missing columns: {missing_members}")

    estimates = response_estimates.copy()
    members = expected_members[[species_col, member_col]].copy()
    for frame, columns in (
        (estimates, (species_col, member_col, predictor_col, quantity_col)),
        (members, (species_col, member_col)),
    ):
        for column in columns:
            frame[column] = frame[column].astype(str)
    if members.duplicated([species_col, member_col]).any():
        raise ValueError("expected member ledger contains duplicate member IDs")
    if estimates.duplicated(
        [species_col, member_col, predictor_col, quantity_col]
    ).any():
        raise ValueError("response estimates contain duplicate member response rows")

    if expected_response_keys is None:
        keys = estimates[[species_col, predictor_col, quantity_col]].drop_duplicates()
    else:
        key_required = {species_col, predictor_col, quantity_col}
        missing_keys = sorted(key_required - set(expected_response_keys.columns))
        if missing_keys:
            raise KeyError(f"expected response keys missing columns: {missing_keys}")
        keys = expected_response_keys[
            [species_col, predictor_col, quantity_col]
        ].copy()
        for column in (species_col, predictor_col, quantity_col):
            keys[column] = keys[column].astype(str)
        if keys.duplicated([species_col, predictor_col, quantity_col]).any():
            raise ValueError("expected response key ledger contains duplicates")

    required_rows = members.merge(keys, on=species_col, how="inner", validate="many_to_many")
    joined = required_rows.merge(
        estimates,
        on=[species_col, member_col, predictor_col, quantity_col],
        how="left",
        validate="one_to_one",
    )
    joined[estimate_col] = pd.to_numeric(joined[estimate_col], errors="coerce")
    joined[span_col] = pd.to_numeric(joined[span_col], errors="coerce")

    rows: list[dict[str, object]] = []
    group_columns = [species_col, predictor_col, quantity_col]
    for key, group in joined.groupby(group_columns, sort=True, dropna=False):
        species, predictor, quantity = (str(x) for x in key)
        finite_estimate = np.isfinite(group[estimate_col].to_numpy(float))
        finite_spans = group.loc[
            np.isfinite(group[span_col].to_numpy(float)), span_col
        ].to_numpy(float)
        span_consistent = bool(
            len(finite_spans) == len(group)
            and len(finite_spans) > 0
            and np.allclose(finite_spans, finite_spans[0], rtol=1e-9, atol=1e-12)
            and finite_spans[0] > 0
        )
        complete = bool(finite_estimate.all() and span_consistent)
        values = group.loc[finite_estimate, estimate_col].to_numpy(float)
        span = float(finite_spans[0]) if span_consistent else float("nan")
        lower = float(np.min(values)) if complete else float("nan")
        upper = float(np.max(values)) if complete else float("nan")
        rows.append(
            {
                "species": species,
                "predictor": predictor,
                "quantity": quantity,
                "interval_status": "complete" if complete else "unavailable_incomplete_refits",
                "n_expected_members": int(len(group)),
                "n_evaluable_members": int(finite_estimate.sum()),
                "all_expected_members_evaluable": complete,
                "environment_span": span,
                "lower_bound": lower,
                "upper_bound": upper,
                "normalized_width": (
                    float((upper - lower) / span) if complete else float("nan")
                ),
                "missing_member_ids": ",".join(
                    sorted(group.loc[~finite_estimate, member_col].astype(str))
                ),
            }
        )
    return pd.DataFrame(rows)


def calibrate_discovery_interval_expansion(
    discovery_envelopes: pd.DataFrame,
    discovery_truth: pd.DataFrame,
    *,
    species_col: str = "species",
    predictor_col: str = "predictor",
    quantity_col: str = "quantity",
    truth_col: str = "estimate",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Freeze maximum normalized outside-envelope miss from discovery truth only."""

    envelope_required = {
        species_col,
        predictor_col,
        quantity_col,
        "interval_status",
        "lower_bound",
        "upper_bound",
        "environment_span",
    }
    missing_envelope = sorted(envelope_required - set(discovery_envelopes.columns))
    if missing_envelope:
        raise KeyError(f"discovery envelopes missing columns: {missing_envelope}")
    truth_required = {species_col, predictor_col, quantity_col, truth_col}
    missing_truth = sorted(truth_required - set(discovery_truth.columns))
    if missing_truth:
        raise KeyError(f"discovery truth missing columns: {missing_truth}")

    envelope = discovery_envelopes.copy()
    truth = discovery_truth[
        [species_col, predictor_col, quantity_col, truth_col]
    ].copy()
    for frame in (envelope, truth):
        for column in (species_col, predictor_col, quantity_col):
            frame[column] = frame[column].astype(str)
    if truth.duplicated([species_col, predictor_col, quantity_col]).any():
        raise ValueError("discovery truth contains duplicate response keys")
    truth = truth.rename(columns={truth_col: "truth_estimate"})
    audit = envelope.merge(
        truth,
        on=[species_col, predictor_col, quantity_col],
        how="outer",
        validate="one_to_one",
    )
    for column in (
        "lower_bound",
        "upper_bound",
        "environment_span",
        "truth_estimate",
    ):
        audit[column] = pd.to_numeric(audit[column], errors="coerce")
    complete = (
        audit["interval_status"].astype(str).eq("complete")
        & np.isfinite(audit["lower_bound"])
        & np.isfinite(audit["upper_bound"])
        & np.isfinite(audit["environment_span"])
        & (audit["environment_span"] > 0)
        & np.isfinite(audit["truth_estimate"])
    )
    below = audit["truth_estimate"] < audit["lower_bound"]
    above = audit["truth_estimate"] > audit["upper_bound"]
    miss = np.zeros(len(audit), dtype=float)
    miss[below.fillna(False)] = (
        audit.loc[below.fillna(False), "lower_bound"]
        - audit.loc[below.fillna(False), "truth_estimate"]
    ) / audit.loc[below.fillna(False), "environment_span"]
    miss[above.fillna(False)] = (
        audit.loc[above.fillna(False), "truth_estimate"]
        - audit.loc[above.fillna(False), "upper_bound"]
    ) / audit.loc[above.fillna(False), "environment_span"]
    miss[~complete.to_numpy(bool)] = np.nan
    audit["normalized_outside_interval_miss"] = miss
    audit["raw_interval_covers_truth"] = complete & ~below & ~above

    calibration_rows: list[dict[str, object]] = []
    for key, group in audit.groupby([predictor_col, quantity_col], sort=True):
        predictor, quantity = (str(x) for x in key)
        values = pd.to_numeric(
            group["normalized_outside_interval_miss"], errors="coerce"
        ).to_numpy(float)
        finite = np.isfinite(values)
        available = bool(len(values) > 0 and finite.all())
        calibration_rows.append(
            {
                "predictor": predictor,
                "quantity": quantity,
                "calibration_status": (
                    "complete" if available else "unavailable_incomplete_discovery_envelope"
                ),
                "n_discovery_keys": int(len(values)),
                "n_evaluable_discovery_keys": int(finite.sum()),
                "normalized_expansion_radius": (
                    float(np.max(values)) if available else float("nan")
                ),
                "calibration_uses_validation_truth": False,
            }
        )
    return pd.DataFrame(calibration_rows), audit


def apply_discovery_interval_calibration(
    raw_envelopes: pd.DataFrame,
    calibration: pd.DataFrame,
) -> pd.DataFrame:
    """Apply frozen discovery radii to raw envelopes without validation truth."""

    envelope_required = {
        "species",
        "predictor",
        "quantity",
        "interval_status",
        "lower_bound",
        "upper_bound",
        "environment_span",
    }
    missing_envelope = sorted(envelope_required - set(raw_envelopes.columns))
    if missing_envelope:
        raise KeyError(f"raw envelopes missing columns: {missing_envelope}")
    calibration_required = {
        "predictor",
        "quantity",
        "calibration_status",
        "normalized_expansion_radius",
        "calibration_uses_validation_truth",
    }
    missing_calibration = sorted(calibration_required - set(calibration.columns))
    if missing_calibration:
        raise KeyError(f"interval calibration missing columns: {missing_calibration}")
    if calibration.duplicated(["predictor", "quantity"]).any():
        raise ValueError("interval calibration contains duplicate response keys")
    if calibration["calibration_uses_validation_truth"].fillna(True).astype(bool).any():
        raise ValueError("validation-truth calibration is forbidden")

    result = raw_envelopes.copy()
    result = result.merge(
        calibration,
        on=["predictor", "quantity"],
        how="left",
        validate="many_to_one",
    )
    for column in (
        "lower_bound",
        "upper_bound",
        "environment_span",
        "normalized_expansion_radius",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    available = (
        result["interval_status"].astype(str).eq("complete")
        & result["calibration_status"].astype(str).eq("complete")
        & np.isfinite(result["lower_bound"])
        & np.isfinite(result["upper_bound"])
        & np.isfinite(result["environment_span"])
        & (result["environment_span"] > 0)
        & np.isfinite(result["normalized_expansion_radius"])
    )
    expansion = (
        result["normalized_expansion_radius"] * result["environment_span"]
    )
    result["calibrated_lower_bound"] = np.where(
        available,
        result["lower_bound"] - expansion,
        np.nan,
    )
    result["calibrated_upper_bound"] = np.where(
        available,
        result["upper_bound"] + expansion,
        np.nan,
    )
    result["calibrated_interval_status"] = np.where(
        available,
        "complete",
        "unavailable_raw_or_calibration",
    )
    result["calibrated_normalized_width"] = np.where(
        available,
        (
            result["calibrated_upper_bound"]
            - result["calibrated_lower_bound"]
        )
        / result["environment_span"],
        np.nan,
    )
    result["calibration_uses_validation_truth"] = False
    return result
