"""Pre-outcome, rule-based proposals for process-information registries.

The proposal layer reduces manual predictor-by-predictor classification without
learning process labels from ecological outcomes. Users predeclare a process
taxonomy and auditable metadata/name rules. The software expands those rules to
all predictors and fails closed on unmatched or conflicting assignments.

This module deliberately produces *proposals*, not ecological truth. A frozen
process-information registry should only be created after the rule set and any
flagged cases have been reviewed before outcome inspection.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

import pandas as pd

from .process_information_closure import (
    REPRESENTATION_ROLES,
    normalize_process_information_registry,
)


RULE_COLUMNS = (
    "rule_id",
    "process",
    "role",
    "predictor_exact",
    "predictor_pattern",
    "source_family",
    "units_pattern",
)


def _clean_optional(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalize_process_classification_rules(
    rules: pd.DataFrame,
    *,
    allowed_roles: Sequence[str] = REPRESENTATION_ROLES,
) -> pd.DataFrame:
    """Validate deterministic process-classification rules.

    Each rule must define ``rule_id``, ``process`` and ``role`` plus at least one
    matcher among ``predictor_exact``, ``predictor_pattern``, ``source_family``
    and ``units_pattern``. Multiple rules may intentionally map a predictor to
    multiple processes. Conflicting roles for the same predictor-process pair
    are detected later by :func:`propose_process_information_registry`.
    """

    required = {"rule_id", "process", "role"}
    missing = sorted(required - set(rules.columns))
    if missing:
        raise KeyError(f"classification rules missing columns: {missing}")

    data = rules.copy()
    for column in RULE_COLUMNS:
        if column not in data.columns:
            data[column] = ""
        data[column] = data[column].map(_clean_optional)

    for column in ("rule_id", "process", "role"):
        if data[column].eq("").any():
            raise ValueError(f"classification rule {column} must be non-empty")

    if data["rule_id"].duplicated().any():
        duplicated = sorted(data.loc[data["rule_id"].duplicated(False), "rule_id"].unique())
        raise ValueError("classification rule_id values must be unique: " + ", ".join(duplicated))

    roles = {str(role).strip() for role in allowed_roles}
    unknown_roles = sorted(set(data["role"]) - roles)
    if unknown_roles:
        raise ValueError("classification rules contain unknown roles: " + ", ".join(unknown_roles))

    matcher_cols = ("predictor_exact", "predictor_pattern", "source_family", "units_pattern")
    missing_matcher = data[list(matcher_cols)].eq("").all(axis=1)
    if missing_matcher.any():
        ids = ", ".join(data.loc[missing_matcher, "rule_id"])
        raise ValueError(f"every classification rule requires at least one matcher: {ids}")

    for column in ("predictor_pattern", "units_pattern"):
        for row in data.loc[data[column].ne(""), ["rule_id", column]].itertuples(index=False):
            try:
                re.compile(getattr(row, column))
            except re.error as exc:
                raise ValueError(
                    f"invalid regex in rule {row.rule_id!r} column {column!r}: {exc}"
                ) from exc

    return data.loc[:, list(RULE_COLUMNS)].reset_index(drop=True)


def _rule_matches(
    predictor: str,
    source_family: str,
    units: str,
    rule: pd.Series,
) -> tuple[bool, tuple[str, ...]]:
    checks: list[bool] = []
    basis: list[str] = []

    exact = str(rule["predictor_exact"])
    if exact:
        checks.append(predictor == exact)
        basis.append("predictor_exact")

    pattern = str(rule["predictor_pattern"])
    if pattern:
        checks.append(re.search(pattern, predictor) is not None)
        basis.append("predictor_pattern")

    source = str(rule["source_family"])
    if source:
        checks.append(source_family == source)
        basis.append("source_family")

    units_pattern = str(rule["units_pattern"])
    if units_pattern:
        checks.append(re.search(units_pattern, units) is not None)
        basis.append("units_pattern")

    return bool(checks) and all(checks), tuple(basis)


def propose_process_information_registry(
    predictors: pd.DataFrame,
    rules: pd.DataFrame,
    *,
    predictor_col: str = "predictor",
    source_col: str = "source_family",
    units_col: str = "units",
) -> pd.DataFrame:
    """Apply predeclared metadata/name rules to all predictors.

    The returned table is auditable and contains one row per proposed
    predictor-process link. Unmatched predictors are retained with
    ``status='unmatched'``. If different matching rules assign conflicting
    representation roles to the same predictor-process pair, the row is marked
    ``status='conflict'`` and cannot be frozen.

    Multiple *processes* for one predictor are allowed and are the intended way
    to express shared composites/proxies.
    """

    if predictor_col not in predictors.columns:
        raise KeyError(f"predictor metadata missing column: {predictor_col}")

    metadata = predictors.copy()
    metadata[predictor_col] = metadata[predictor_col].astype(str).str.strip()
    if metadata[predictor_col].eq("").any():
        raise ValueError("predictor names must be non-empty")
    if metadata[predictor_col].duplicated().any():
        duplicated = sorted(metadata.loc[metadata[predictor_col].duplicated(False), predictor_col].unique())
        raise ValueError("predictor metadata must contain one row per predictor: " + ", ".join(duplicated))

    for column in (source_col, units_col):
        if column not in metadata.columns:
            metadata[column] = ""
        metadata[column] = metadata[column].map(_clean_optional)

    normalized_rules = normalize_process_classification_rules(rules)
    raw_rows: list[dict[str, object]] = []

    for meta in metadata.to_dict(orient="records"):
        predictor = str(meta[predictor_col])
        source_family = str(meta[source_col])
        units = str(meta[units_col])
        matched = False
        for _, rule in normalized_rules.iterrows():
            is_match, basis = _rule_matches(predictor, source_family, units, rule)
            if not is_match:
                continue
            matched = True
            raw_rows.append(
                {
                    "predictor": predictor,
                    "process": str(rule["process"]),
                    "role": str(rule["role"]),
                    "rule_id": str(rule["rule_id"]),
                    "match_basis": ",".join(basis),
                    "source_family": source_family,
                    "units": units,
                }
            )
        if not matched:
            raw_rows.append(
                {
                    "predictor": predictor,
                    "process": "",
                    "role": "",
                    "rule_id": "",
                    "match_basis": "",
                    "source_family": source_family,
                    "units": units,
                }
            )

    raw = pd.DataFrame(raw_rows)
    proposed_rows: list[dict[str, object]] = []
    for predictor, group in raw.groupby("predictor", sort=False):
        unmatched = group["process"].eq("")
        if unmatched.all():
            row = group.iloc[0]
            proposed_rows.append(
                {
                    "predictor": predictor,
                    "process": "",
                    "role": "",
                    "rule_ids": "",
                    "match_basis": "",
                    "source_family": row["source_family"],
                    "units": row["units"],
                    "status": "unmatched",
                    "review_required": True,
                }
            )
            continue

        matched_group = group.loc[~unmatched]
        for process, process_group in matched_group.groupby("process", sort=False):
            roles = tuple(dict.fromkeys(process_group["role"].astype(str)))
            status = "proposed" if len(roles) == 1 else "conflict"
            proposed_rows.append(
                {
                    "predictor": predictor,
                    "process": process,
                    "role": roles[0] if len(roles) == 1 else "|".join(sorted(roles)),
                    "rule_ids": ",".join(dict.fromkeys(process_group["rule_id"].astype(str))),
                    "match_basis": ",".join(
                        dict.fromkeys(
                            part
                            for cell in process_group["match_basis"].astype(str)
                            for part in cell.split(",")
                            if part
                        )
                    ),
                    "source_family": process_group.iloc[0]["source_family"],
                    "units": process_group.iloc[0]["units"],
                    "status": status,
                    "review_required": status != "proposed",
                }
            )

    return pd.DataFrame(proposed_rows).sort_values(
        ["predictor", "process"], kind="mergesort"
    ).reset_index(drop=True)


def freeze_process_registry_proposal(
    proposal: pd.DataFrame,
    *,
    expected_predictors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Freeze a reviewed proposal as the many-to-many process registry.

    This function fails closed if any predictor is unmatched, any assignment is
    conflicting, or any ``review_required`` flag remains true. The returned
    table contains only ``predictor``, ``process`` and ``role`` and is validated
    by the generic process-information-closure registry validator.

    The scientific review unit is therefore the *rule set plus flagged cases*,
    not every individual predictor row.
    """

    required = {"predictor", "process", "role", "status", "review_required"}
    missing = sorted(required - set(proposal.columns))
    if missing:
        raise KeyError(f"process registry proposal missing columns: {missing}")

    data = proposal.copy()
    if data["review_required"].isna().any():
        raise ValueError("review_required contains missing values")
    if not data["review_required"].map(lambda value: isinstance(value, bool)).all():
        raise ValueError("review_required must contain literal booleans")

    unresolved = data.loc[
        data["review_required"] | ~data["status"].eq("proposed"),
        ["predictor", "status"],
    ]
    if not unresolved.empty:
        details = ", ".join(
            f"{row.predictor}:{row.status}" for row in unresolved.itertuples(index=False)
        )
        raise ValueError("proposal still requires review: " + details)

    frozen = data[["predictor", "process", "role"]].copy()
    predictor_universe = tuple(expected_predictors) if expected_predictors is not None else tuple(
        dict.fromkeys(frozen["predictor"].astype(str))
    )
    return normalize_process_information_registry(
        frozen,
        predictor_universe=predictor_universe,
    )
