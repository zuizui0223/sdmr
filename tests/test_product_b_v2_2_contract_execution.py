from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.model import ModelSpec
from sdmr.niche_recovery_procedure import RecoveryProcedure
from sdmr.product_b_v2_2_frozen_ablation import frozen_representation_process_ablation
from sdmr.product_b_v2_2_known_truth_contract import (
    BASE_EXECUTION_CONTRACT,
    load_product_b_v2_2_known_truth_contract,
)

CONFIG = Path("configs/product_b_v2_2_known_truth_contract.json")


def test_base_procedure_execution_is_explicitly_frozen():
    contract = load_product_b_v2_2_known_truth_contract(CONFIG)
    assert contract["base_procedure_execution_contract"] == BASE_EXECUTION_CONTRACT
    assert BASE_EXECUTION_CONTRACT == {
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "observation_correction_active": False,
        "observation_weight_truncation_quantile": 0.99,
    }


def test_observation_only_remainder_is_explicit_null_ecological_representation():
    rng = np.random.default_rng(8)
    presence_groups = np.repeat(np.arange(4), 8)
    background_groups = np.repeat(np.arange(4), 16)
    presence = pd.DataFrame({
        "temperature": rng.normal(1.0, 0.5, len(presence_groups)),
        "recording_bias": rng.normal(0.0, 1.0, len(presence_groups)),
    })
    background = pd.DataFrame({
        "temperature": rng.normal(0.0, 1.0, len(background_groups)),
        "recording_bias": rng.normal(0.0, 1.0, len(background_groups)),
    })
    procedure = RecoveryProcedure(
        "all",
        ModelSpec(C=1.0, degree=1, penalty="l2"),
        inner_folds=2,
        max_predictors=2,
        predictive_min_gain=0.0,
        observation_predictors=("recording_bias",),
    )
    base = pd.DataFrame([
        {
            "fold": 0,
            "candidate": procedure.label,
            "selected_predictors": "temperature,recording_bias",
        },
        {
            "fold": 1,
            "candidate": procedure.label,
            "selected_predictors": "temperature,recording_bias",
        },
    ])
    result = frozen_representation_process_ablation(
        presence,
        background,
        presence_groups,
        background_groups,
        base,
        ("temperature",),
        procedure,
        ("temperature",),
        {"temperature": "temperature", "recording_bias": "observation_process"},
        outer_folds=2,
    )
    assert len(result) == 2
    assert result["selected_predictors"].eq("recording_bias").all()
    assert result["n_ecological_predictors"].eq(0).all()
    assert result["null_model_representation_after_drop"].eq(False).all()
    assert result["null_ecological_representation_after_drop"].eq(True).all()
    assert result["predictor_reselection_after_process_drop"].eq(False).all()
