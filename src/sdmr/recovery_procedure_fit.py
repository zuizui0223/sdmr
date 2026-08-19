"""Final fitting of a frozen Product-A v2 recovery procedure.

Outer model-pool CV selects a *procedure*.  After that procedure is frozen, it is
rerun one last time on the complete model pool to choose its ecological predictor
subset and fit the final relative-suitability model.  Authoritative outer-sealed
rows are not accepted by this API and can only be scored downstream.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .model import fit_relative_suitability_model
from .niche_recovery_procedure import RecoveryProcedure, _select_fold_predictors


@dataclass(frozen=True)
class FittedRecoveryProcedure:
    procedure: RecoveryProcedure
    selected_predictors: tuple[str, ...]
    selected_ecological_predictors: tuple[str, ...]
    selection_trace: pd.DataFrame
    model: object


def fit_recovery_procedure(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    ecological_predictors: Sequence[str],
    audit_predictors: Sequence[str],
    procedure: RecoveryProcedure,
    *,
    observation_correction_active: bool = False,
    observation_weight_truncation_quantile: float = 0.99,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> FittedRecoveryProcedure:
    """Apply a frozen recovery procedure to the complete model pool and fit it."""

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("spatial group arrays must align with model-pool rows")
    if len(np.unique(p_groups)) < 2:
        raise ValueError("final procedure fitting requires at least two model-pool spatial blocks")

    selected, trace = _select_fold_predictors(
        presence,
        background,
        p_groups,
        b_groups,
        ecological_predictors,
        audit_predictors,
        procedure,
        observation_correction_active=observation_correction_active,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
    )
    model = fit_relative_suitability_model(
        presence,
        background,
        selected,
        model_spec=procedure.model_spec,
    )
    observation = set(procedure.observation_predictors)
    ecological = tuple(p for p in selected if p not in observation)
    return FittedRecoveryProcedure(
        procedure=procedure,
        selected_predictors=tuple(selected),
        selected_ecological_predictors=ecological,
        selection_trace=trace,
        model=model,
    )
