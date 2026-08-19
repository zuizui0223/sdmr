"""Model-pool-only predictor admissibility for Product-A v2.1.

This gate is deliberately evaluated before candidate model fitting and before any
sealed outcome is opened.  A raw predictor is eligible for procedure search only
when its non-missing coverage reaches the already-declared empirical audit
coverage threshold in both model-pool presences and model-pool background for
every required perturbation/M condition.

The gate does not rank predictors, inspect model scores, or change ecological
process labels.  It only removes structurally sparse raw predictors from the
candidate universe.  Failure to retain enough predictors/processes should lead
to abstention upstream rather than post-hoc threshold relaxation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PredictorAdmissibilityResult:
    predictors: tuple[str, ...]
    ledger: pd.DataFrame
    minimum_coverage: float


def model_pool_predictor_coverage_ledger(
    perturbations: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    predictors: Sequence[str],
    *,
    minimum_coverage: float = 0.95,
) -> pd.DataFrame:
    """Return predictor × perturbation coverage using model-pool rows only.

    ``perturbations`` maps a predeclared perturbation/M label to
    ``(model_presence, model_background)``.  Callers are responsible for passing
    model-pool frames; sealed rows are neither accepted nor inferred here.
    """

    threshold = float(minimum_coverage)
    if not 0.0 < threshold <= 1.0:
        raise ValueError("minimum_coverage must be in (0, 1]")
    labels = tuple(str(x) for x in perturbations)
    if not labels:
        raise ValueError("at least one perturbation is required")
    predictors = tuple(dict.fromkeys(str(x) for x in predictors))
    if not predictors:
        raise ValueError("at least one predictor is required")

    rows: list[dict[str, object]] = []
    for label in labels:
        presence, background = perturbations[label]
        for frame_name, frame in (("presence", presence), ("background", background)):
            missing = sorted(set(predictors) - set(frame.columns))
            if missing:
                raise KeyError(f"{label} {frame_name} lacks predictors: {missing}")
        n_presence = int(len(presence))
        n_background = int(len(background))
        for predictor in predictors:
            presence_coverage = (
                float(pd.to_numeric(presence[predictor], errors="coerce").notna().mean())
                if n_presence
                else 0.0
            )
            background_coverage = (
                float(pd.to_numeric(background[predictor], errors="coerce").notna().mean())
                if n_background
                else 0.0
            )
            cell_minimum = min(presence_coverage, background_coverage)
            rows.append(
                {
                    "predictor": predictor,
                    "perturbation": label,
                    "n_model_presence": n_presence,
                    "n_model_background": n_background,
                    "presence_coverage": presence_coverage,
                    "background_coverage": background_coverage,
                    "minimum_cell_coverage": cell_minimum,
                    "eligible_cell": cell_minimum >= threshold,
                }
            )
    ledger = pd.DataFrame(rows)
    summary = (
        ledger.groupby("predictor", as_index=False)
        .agg(
            minimum_model_pool_coverage=("minimum_cell_coverage", "min"),
            n_required_perturbations=("perturbation", "nunique"),
            n_passing_perturbations=("eligible_cell", "sum"),
        )
    )
    summary["eligible_all_perturbations"] = (
        summary["n_passing_perturbations"] == summary["n_required_perturbations"]
    )
    return ledger.merge(summary, on="predictor", how="left", validate="many_to_one")


def select_model_pool_admissible_predictors(
    perturbations: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    predictors: Sequence[str],
    *,
    minimum_coverage: float = 0.95,
) -> PredictorAdmissibilityResult:
    """Select only raw predictors with adequate model-pool coverage everywhere."""

    ledger = model_pool_predictor_coverage_ledger(
        perturbations,
        predictors,
        minimum_coverage=minimum_coverage,
    )
    eligible = (
        ledger.loc[ledger["eligible_all_perturbations"].astype(bool), "predictor"]
        .drop_duplicates()
        .astype(str)
    )
    order = {str(predictor): index for index, predictor in enumerate(predictors)}
    selected = tuple(sorted(eligible, key=lambda predictor: order[predictor]))
    return PredictorAdmissibilityResult(
        predictors=selected,
        ledger=ledger,
        minimum_coverage=float(minimum_coverage),
    )
