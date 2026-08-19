"""Extra fail-closed checks for Product-A v2.6 empirical model-pool design."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .v2_6_empirical_contract import load_v2_6_empirical_contract

EXPECTED_STRATEGIES = ("all", "vif", "predictive_forward", "niche_forward")
EXPECTED_MODEL_SPECS = (
    {"C": 0.1, "degree": 1, "penalty": "l2"},
    {"C": 1.0, "degree": 2, "penalty": "l2"},
)


def load_v2_6_empirical_model_contract(path: str | Path) -> dict[str, Any]:
    payload = load_v2_6_empirical_contract(path)
    design = payload["fixed_design"]
    if abs(float(design.get("minimum_model_pool_predictor_coverage", -1)) - 0.95) > 1e-12:
        raise ValueError("model-pool predictor coverage threshold changed")
    library = design.get("procedure_library", {})
    if tuple(library.get("strategies", ())) != EXPECTED_STRATEGIES:
        raise ValueError("empirical procedure strategy order changed")
    if tuple(library.get("model_specs", ())) != EXPECTED_MODEL_SPECS:
        raise ValueError("empirical model-spec library changed")
    expected_scalars = {
        "inner_folds": 3,
        "outer_folds": 4,
        "max_predictors": 8,
    }
    for key, expected in expected_scalars.items():
        if int(library.get(key, -1)) != expected:
            raise ValueError(f"empirical procedure library changed: {key}")
    if abs(float(library.get("vif_threshold", -1)) - 5.0) > 1e-12:
        raise ValueError("empirical VIF threshold changed")
    if abs(float(library.get("predictive_min_gain", -1)) - 0.0) > 1e-12:
        raise ValueError("empirical predictive-forward gain threshold changed")
    if tuple(library.get("observation_predictors", ())) != ():
        raise ValueError("empirical CHELSA run has no fitted observation-process predictor")

    adequacy = design.get("prediction_adequacy", {})
    if abs(float(adequacy.get("chance_auc", -1)) - 0.50) > 1e-12:
        raise ValueError("empirical chance-AUC reference changed")
    if abs(float(adequacy.get("minimum_auc_margin", -1)) - 0.01) > 1e-12:
        raise ValueError("empirical adequacy margin changed")
    if abs(float(adequacy.get("auc_sem_multiplier", -1)) - 1.0) > 1e-12:
        raise ValueError("empirical adequacy SEM rule changed")
    if adequacy.get("complete_outer_fold_evidence_required") is not True:
        raise ValueError("empirical adequacy cannot drop incomplete outer folds")
    return payload
