"""Deterministic procedure library for the Product-A v2.7.2 successor.

Historical Product-A contracts omitted an estimator random state. This module is
used only by successor contracts that explicitly freeze ``model_random_state``.
"""
from __future__ import annotations

from .model import ModelSpec
from .niche_recovery_procedure import RecoveryProcedure


def deterministic_procedure_library(contract: dict) -> tuple[RecoveryProcedure, ...]:
    frozen = contract["fixed_design"]["procedure_library"]
    if "model_random_state" not in frozen:
        raise ValueError("deterministic successor requires model_random_state")
    random_state = frozen["model_random_state"]
    if not isinstance(random_state, int):
        raise TypeError("model_random_state must be an integer")

    procedures: list[RecoveryProcedure] = []
    for spec in frozen["model_specs"]:
        model_spec = ModelSpec(
            C=float(spec["C"]),
            degree=int(spec["degree"]),
            penalty=str(spec["penalty"]),
            random_state=int(random_state),
        )
        for strategy in frozen["strategies"]:
            procedures.append(
                RecoveryProcedure(
                    strategy=str(strategy),
                    model_spec=model_spec,
                    inner_folds=int(frozen["inner_folds"]),
                    max_predictors=int(frozen["max_predictors"]),
                    vif_threshold=float(frozen["vif_threshold"]),
                    predictive_min_gain=float(frozen["predictive_min_gain"]),
                    observation_predictors=tuple(frozen["observation_predictors"]),
                )
            )
    if len(procedures) != 8 or len({p.label for p in procedures}) != 8:
        raise ValueError("deterministic Product-A library must contain eight unique procedures")
    return tuple(procedures)
