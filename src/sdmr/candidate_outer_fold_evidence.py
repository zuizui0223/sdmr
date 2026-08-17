"""Complete outer-fold evidence gates for Product-A v2.1 selectors.

A candidate procedure must not win a cross-taxon or perturbation selector because
one predeclared outer fold failed and disappeared from the metrics table.  This
module checks candidate evidence coverage before any ranking/selection score is
computed.  Missing/non-finite folds are explicit evidence insufficiency.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CandidateOuterEvidenceResult:
    eligible_candidates: tuple[str, ...]
    cell_ledger: pd.DataFrame
    candidate_summary: pd.DataFrame
    expected_outer_folds: int


def require_complete_outer_fold_evidence(
    metrics: pd.DataFrame,
    *,
    discovery_taxa: Sequence[str],
    perturbations: Sequence[str],
    required_columns: Sequence[str],
    expected_outer_folds: int,
    candidate_col: str = "candidate",
    species_col: str = "species",
    perturbation_col: str = "perturbation",
    fold_col: str = "fold",
) -> CandidateOuterEvidenceResult:
    """Return candidates with every required finite outer-fold datum.

    Eligibility requires each candidate to contain exactly the expected fold IDs
    ``0..expected_outer_folds-1`` for every predeclared discovery taxon ×
    perturbation cell and to have finite values for every required evidence
    column in every one of those folds.
    """

    expected_outer_folds = int(expected_outer_folds)
    if expected_outer_folds < 2:
        raise ValueError("expected_outer_folds must be >=2")
    required_columns = tuple(dict.fromkeys(str(x) for x in required_columns))
    if not required_columns:
        raise ValueError("at least one required evidence column is needed")
    discovery_taxa = tuple(dict.fromkeys(str(x) for x in discovery_taxa))
    perturbations = tuple(dict.fromkeys(str(x) for x in perturbations))
    if not discovery_taxa or not perturbations:
        raise ValueError("discovery_taxa and perturbations must be non-empty")

    required_table_columns = {
        candidate_col,
        species_col,
        perturbation_col,
        fold_col,
        *required_columns,
    }
    missing = sorted(required_table_columns - set(metrics.columns))
    if missing:
        raise KeyError(f"metrics table lacks required columns: {missing}")

    data = metrics.copy()
    data[candidate_col] = data[candidate_col].astype(str)
    data[species_col] = data[species_col].astype(str)
    data[perturbation_col] = data[perturbation_col].astype(str)
    expected_fold_ids = set(range(expected_outer_folds))
    candidates = tuple(sorted(data[candidate_col].dropna().astype(str).unique()))

    rows: list[dict[str, object]] = []
    for candidate in candidates:
        candidate_rows = data.loc[data[candidate_col].eq(candidate)]
        for species in discovery_taxa:
            for perturbation in perturbations:
                cell = candidate_rows.loc[
                    candidate_rows[species_col].eq(species)
                    & candidate_rows[perturbation_col].eq(perturbation)
                ]
                observed_fold_ids = set(
                    pd.to_numeric(cell[fold_col], errors="coerce")
                    .dropna()
                    .astype(int)
                    .tolist()
                )
                folds_complete = observed_fold_ids == expected_fold_ids
                finite_by_column: dict[str, bool] = {}
                for column in required_columns:
                    values_by_fold = {}
                    for fold in expected_fold_ids:
                        fold_values = pd.to_numeric(
                            cell.loc[
                                pd.to_numeric(cell[fold_col], errors="coerce").eq(fold),
                                column,
                            ],
                            errors="coerce",
                        ).to_numpy(float)
                        values_by_fold[fold] = bool(np.isfinite(fold_values).any())
                    finite_by_column[column] = all(values_by_fold.values())
                evidence_complete = folds_complete and all(finite_by_column.values())
                rows.append(
                    {
                        "candidate": candidate,
                        "species": species,
                        "perturbation": perturbation,
                        "expected_outer_folds": expected_outer_folds,
                        "observed_fold_ids": ",".join(
                            str(x) for x in sorted(observed_fold_ids)
                        ),
                        "n_observed_outer_folds": len(observed_fold_ids),
                        "fold_ids_complete": folds_complete,
                        "finite_required_columns": all(finite_by_column.values()),
                        "evidence_complete": evidence_complete,
                        "missing_or_nonfinite_columns": ",".join(
                            column
                            for column, complete in finite_by_column.items()
                            if not complete
                        ),
                    }
                )
    cell_ledger = pd.DataFrame(rows)
    expected_cells = len(discovery_taxa) * len(perturbations)
    summary = (
        cell_ledger.groupby("candidate", as_index=False)
        .agg(
            n_required_cells=("evidence_complete", "size"),
            n_complete_cells=("evidence_complete", "sum"),
            n_cells_with_complete_fold_ids=("fold_ids_complete", "sum"),
            n_cells_with_finite_required_columns=("finite_required_columns", "sum"),
        )
    )
    summary["eligible_complete_outer_evidence"] = (
        (summary["n_required_cells"] == expected_cells)
        & (summary["n_complete_cells"] == expected_cells)
    )
    eligible = tuple(
        summary.loc[
            summary["eligible_complete_outer_evidence"].astype(bool), "candidate"
        ].astype(str)
    )
    return CandidateOuterEvidenceResult(
        eligible_candidates=eligible,
        cell_ledger=cell_ledger,
        candidate_summary=summary,
        expected_outer_folds=expected_outer_folds,
    )
