"""Generic ecological-identification primitives.

This module generalizes the inferential logic developed in Product A without
changing any frozen Product-A scientific endpoint.

Two estimands are deliberately kept separate:

* process necessity: challenge a declared process by excluding every registered
  representation that carries information about that process, then ask whether
  an adequate alternative explanation survives;
* process stability: ask which process claims persist across independently
  defined analyses/selectors, even when exact fitted-model identity differs.

The registry is many-to-many: one predictor may carry information about several
processes (for example a composite or proxy), so process-information knockouts
operate on declared closure rather than one-predictor/one-process aliases.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from .process_exclusion_certificate import knockout_candidate_label


REPRESENTATION_ROLES = (
    "direct",
    "derived",
    "proxy",
    "composite",
)

NECESSITY_STATES = (
    "refuted_as_necessary",
    "required_by_evidence_contract",
    "unresolved",
)


@dataclass(frozen=True)
class ProcessStabilityCertificate:
    analyses: tuple[str, ...]
    stable_process_core: tuple[str, ...]
    process_union: tuple[str, ...]
    contested_processes: tuple[str, ...]
    exact_process_consensus: bool


def _unique_nonempty(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if not result:
        raise ValueError(f"{name} must be non-empty")
    if any(not value for value in result):
        raise ValueError(f"{name} must not contain empty strings")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def normalize_process_information_registry(
    registry: pd.DataFrame,
    *,
    process_universe: Sequence[str] | None = None,
    predictor_universe: Sequence[str] | None = None,
    predictor_col: str = "predictor",
    process_col: str = "process",
    role_col: str = "role",
    allowed_roles: Sequence[str] = REPRESENTATION_ROLES,
) -> pd.DataFrame:
    """Validate and normalize a many-to-many process-information registry.

    The registry contains one row per predictor x process information link.
    A predictor may therefore appear more than once. This is intentional:
    derived, proxy and composite predictors may carry information about several
    ecological processes.

    If a process or predictor universe is supplied, the function fails closed
    when the registry references objects outside it or leaves declared
    ecological predictors/processes unrepresented.
    """

    required = {predictor_col, process_col, role_col}
    missing = sorted(required - set(registry.columns))
    if missing:
        raise KeyError(f"process-information registry missing columns: {missing}")

    roles = _unique_nonempty(tuple(allowed_roles), name="allowed_roles")
    data = registry.copy()
    for column in (predictor_col, process_col, role_col):
        data[column] = data[column].astype(str).str.strip()
        if data[column].eq("").any():
            raise ValueError(f"{column} must not contain empty strings")

    unknown_roles = sorted(set(data[role_col]) - set(roles))
    if unknown_roles:
        raise ValueError(
            "process-information registry contains unknown roles: "
            + ", ".join(unknown_roles)
        )

    link_columns = [predictor_col, process_col]
    if data.duplicated(link_columns).any():
        duplicated = (
            data.loc[data.duplicated(link_columns, keep=False), link_columns]
            .drop_duplicates()
            .astype(str)
            .agg(" -> ".join, axis=1)
            .tolist()
        )
        raise ValueError(
            "predictor-process links must be unique: " + ", ".join(duplicated)
        )

    if process_universe is not None:
        processes = _unique_nonempty(process_universe, name="process_universe")
        unknown = sorted(set(data[process_col]) - set(processes))
        if unknown:
            raise ValueError(
                "registry maps outside process_universe: " + ", ".join(unknown)
            )
        empty = [process for process in processes if process not in set(data[process_col])]
        if empty:
            raise ValueError(
                "every declared process requires at least one representation: "
                + ", ".join(empty)
            )

    if predictor_universe is not None:
        predictors = _unique_nonempty(predictor_universe, name="predictor_universe")
        unknown = sorted(set(data[predictor_col]) - set(predictors))
        if unknown:
            raise ValueError(
                "registry references predictors outside predictor_universe: "
                + ", ".join(unknown)
            )
        uncovered = [
            predictor for predictor in predictors if predictor not in set(data[predictor_col])
        ]
        if uncovered:
            raise ValueError(
                "every declared ecological predictor requires at least one "
                "process-information link: "
                + ", ".join(uncovered)
            )

    role_order = {role: index for index, role in enumerate(roles)}
    data["_role_order"] = data[role_col].map(role_order).astype(int)
    return (
        data.sort_values(
            [process_col, "_role_order", predictor_col],
            kind="mergesort",
        )
        .drop(columns="_role_order")
        .reset_index(drop=True)
    )


def process_information_closure(
    registry: pd.DataFrame,
    process: str,
    *,
    predictor_col: str = "predictor",
    process_col: str = "process",
    role_col: str = "role",
) -> tuple[str, ...]:
    """Return every declared representation carrying one process's information."""

    process_name = str(process).strip()
    if not process_name:
        raise ValueError("process must be non-empty")
    data = normalize_process_information_registry(
        registry,
        predictor_col=predictor_col,
        process_col=process_col,
        role_col=role_col,
    )
    closure = tuple(
        dict.fromkeys(
            data.loc[data[process_col].eq(process_name), predictor_col].astype(str)
        )
    )
    if not closure:
        raise KeyError(f"process not represented in registry: {process_name}")
    return closure


def summarize_process_information_closures(
    registry: pd.DataFrame,
    *,
    process_universe: Sequence[str] | None = None,
    predictor_col: str = "predictor",
    process_col: str = "process",
    role_col: str = "role",
) -> pd.DataFrame:
    """Return one auditable row per process and its declared information closure."""

    data = normalize_process_information_registry(
        registry,
        process_universe=process_universe,
        predictor_col=predictor_col,
        process_col=process_col,
        role_col=role_col,
    )
    processes = (
        tuple(process_universe)
        if process_universe is not None
        else tuple(dict.fromkeys(data[process_col].astype(str)))
    )
    rows: list[dict[str, object]] = []
    for process in processes:
        group = data.loc[data[process_col].eq(str(process))]
        closure = tuple(dict.fromkeys(group[predictor_col].astype(str)))
        row: dict[str, object] = {
            "process": str(process),
            "closure_predictors": ",".join(closure),
            "n_closure_predictors": len(closure),
        }
        for role in REPRESENTATION_ROLES:
            predictors = tuple(
                dict.fromkeys(
                    group.loc[group[role_col].eq(role), predictor_col].astype(str)
                )
            )
            row[f"{role}_predictors"] = ",".join(predictors)
            row[f"n_{role}_predictors"] = len(predictors)
        rows.append(row)
    return pd.DataFrame(rows)


def freeze_process_information_knockout_registry(
    *,
    base_candidates: Sequence[str],
    ecological_predictors: Sequence[str],
    process_registry: pd.DataFrame,
    process_universe: Sequence[str],
    observation_predictors: Sequence[str] = (),
    predictor_col: str = "predictor",
    process_col: str = "process",
    role_col: str = "role",
) -> pd.DataFrame:
    """Freeze a base-candidate x process registry using many-to-many closure.

    All ecological predictors registered as carrying the excluded process are
    removed. Predictors linked to multiple processes are therefore removed in
    every relevant knockout. Observation predictors are retained but are not
    part of the ecological process registry.
    """

    bases = _unique_nonempty(base_candidates, name="base_candidates")
    ecological = _unique_nonempty(
        ecological_predictors, name="ecological_predictors"
    )
    processes = _unique_nonempty(process_universe, name="process_universe")
    observation = tuple(dict.fromkeys(str(x).strip() for x in observation_predictors))
    if any(not value for value in observation):
        raise ValueError("observation_predictors must not contain empty strings")
    overlap = sorted(set(ecological) & set(observation))
    if overlap:
        raise ValueError(
            "predictors cannot be both ecological and observational: "
            + ", ".join(overlap)
        )

    registry = normalize_process_information_registry(
        process_registry,
        process_universe=processes,
        predictor_universe=ecological,
        predictor_col=predictor_col,
        process_col=process_col,
        role_col=role_col,
    )
    closures = {
        process: process_information_closure(
            registry,
            process,
            predictor_col=predictor_col,
            process_col=process_col,
            role_col=role_col,
        )
        for process in processes
    }

    rows: list[dict[str, object]] = []
    for base in bases:
        for process in processes:
            excluded = closures[process]
            excluded_set = set(excluded)
            retained = tuple(
                predictor for predictor in ecological if predictor not in excluded_set
            )
            if not retained:
                raise ValueError(
                    f"excluding process {process!r} leaves no ecological predictor"
                )
            role_counts = (
                registry.loc[registry[process_col].eq(process), role_col]
                .value_counts()
                .to_dict()
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
                    "n_direct_excluded": int(role_counts.get("direct", 0)),
                    "n_derived_excluded": int(role_counts.get("derived", 0)),
                    "n_proxy_excluded": int(role_counts.get("proxy", 0)),
                    "n_composite_excluded": int(role_counts.get("composite", 0)),
                }
            )

    result = pd.DataFrame(rows)
    expected = len(bases) * len(processes)
    if len(result) != expected or result["candidate"].nunique() != expected:
        raise AssertionError("knockout registry is not a complete unique Cartesian product")
    return result


def classify_process_necessity(
    evidence: pd.DataFrame,
    knockout_registry: pd.DataFrame,
    *,
    expected_contexts: Sequence[str],
    candidate_col: str = "candidate",
    context_col: str = "context",
    complete_col: str = "complete",
    adequate_col: str = "adequate",
) -> pd.DataFrame:
    """Classify process necessity from frozen knockout-route evidence.

    A process is ``refuted_as_necessary`` when at least one declared knockout
    route is complete and adequate in every expected context. It is
    ``required_by_evidence_contract`` only when every declared route is complete
    and no route is an adequate witness. Otherwise it is ``unresolved``.

    The required state is explicitly evidence-contract-relative; this function
    does not establish causal, physiological or fundamental-niche necessity.
    """

    contexts = _unique_nonempty(expected_contexts, name="expected_contexts")
    registry_required = {"candidate", "excluded_process", "base_candidate"}
    missing_registry = sorted(registry_required - set(knockout_registry.columns))
    if missing_registry:
        raise KeyError(f"knockout registry missing columns: {missing_registry}")
    if knockout_registry["candidate"].astype(str).duplicated().any():
        raise ValueError("knockout registry candidate labels must be unique")

    required = {candidate_col, context_col, complete_col, adequate_col}
    missing = sorted(required - set(evidence.columns))
    if missing:
        raise KeyError(f"necessity evidence missing columns: {missing}")

    data = evidence.copy()
    data[candidate_col] = data[candidate_col].astype(str)
    data[context_col] = data[context_col].astype(str)
    data[complete_col] = data[complete_col].astype(bool)
    data[adequate_col] = data[adequate_col].astype(bool)

    expected_context_set = set(contexts)
    registry = knockout_registry.copy()
    registry["candidate"] = registry["candidate"].astype(str)
    registry["excluded_process"] = registry["excluded_process"].astype(str)

    rows: list[dict[str, object]] = []
    for process, group in registry.groupby("excluded_process", sort=True):
        route_ids = tuple(group["candidate"].astype(str))
        complete_routes: list[str] = []
        adequate_witnesses: list[str] = []
        incomplete_routes: list[str] = []

        for route in route_ids:
            subset = data.loc[data[candidate_col].eq(route)]
            observed_contexts = set(subset[context_col].astype(str))
            route_complete = (
                observed_contexts == expected_context_set
                and len(subset) == len(contexts)
                and bool(subset[complete_col].all())
            )
            if route_complete:
                complete_routes.append(route)
                if bool(subset[adequate_col].all()):
                    adequate_witnesses.append(route)
            else:
                incomplete_routes.append(route)

        if adequate_witnesses:
            status = "refuted_as_necessary"
        elif len(complete_routes) == len(route_ids):
            status = "required_by_evidence_contract"
        else:
            status = "unresolved"

        rows.append(
            {
                "process": str(process),
                "status": status,
                "n_declared_routes": len(route_ids),
                "n_complete_routes": len(complete_routes),
                "n_adequate_witness_routes": len(adequate_witnesses),
                "all_declared_routes_complete": len(complete_routes) == len(route_ids),
                "adequate_witness_routes": ",".join(sorted(adequate_witnesses)),
                "incomplete_routes": ",".join(sorted(incomplete_routes)),
            }
        )

    result = pd.DataFrame(rows)
    if not set(result["status"]).issubset(NECESSITY_STATES):
        raise AssertionError("unexpected necessity state")
    return result


def build_process_stability_certificate(
    process_sets: Mapping[str, Iterable[str]],
) -> ProcessStabilityCertificate:
    """Summarize process agreement across independently defined analyses.

    This is a stability certificate, not a necessity certificate.
    """

    if not process_sets:
        raise ValueError("process_sets must be non-empty")

    normalized: dict[str, tuple[str, ...]] = {}
    for analysis, processes in process_sets.items():
        analysis_name = str(analysis).strip()
        if not analysis_name:
            raise ValueError("analysis names must be non-empty")
        process_tuple = tuple(dict.fromkeys(str(p).strip() for p in processes))
        if any(not process for process in process_tuple):
            raise ValueError("process sets must not contain empty process names")
        normalized[analysis_name] = process_tuple

    analyses = tuple(normalized)
    process_sets_as_sets = [set(normalized[name]) for name in analyses]
    stable = set.intersection(*process_sets_as_sets)
    union = set.union(*process_sets_as_sets)
    contested = union - stable
    exact = all(process_sets_as_sets[0] == values for values in process_sets_as_sets[1:])

    return ProcessStabilityCertificate(
        analyses=analyses,
        stable_process_core=tuple(sorted(stable)),
        process_union=tuple(sorted(union)),
        contested_processes=tuple(sorted(contested)),
        exact_process_consensus=exact,
    )
