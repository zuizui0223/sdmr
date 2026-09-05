import numpy as np
import pandas as pd
import pytest

from sdmr.ecological_identification_learner import fit_ecological_identification_learner
from sdmr.model import ModelSpec
from sdmr.sealed_occurrence_contract import freeze_occurrence_answer_check_split


def _synthetic_tables(seed: int = 4):
    rng = np.random.default_rng(seed)
    n = 160
    groups = np.tile(np.arange(8), n // 8)
    p = pd.DataFrame(
        {
            "x_thermal": rng.normal(2.0, 0.45, n),
            "x_water": rng.normal(0.0, 1.0, n),
        }
    )
    b = pd.DataFrame(
        {
            "x_thermal": rng.normal(-2.0, 0.45, n),
            "x_water": rng.normal(0.0, 1.0, n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "x_thermal", "process": "thermal", "role": "direct"},
            {"predictor": "x_water", "process": "water", "role": "direct"},
        ]
    )
    return p, b, groups.copy(), groups.copy(), registry


def test_learner_returns_set_valued_prediction_and_process_certificate() -> None:
    p, b, pg, bg, registry = _synthetic_tables()
    fit = fit_ecological_identification_learner(
        p,
        b,
        pg,
        bg,
        predictors=("x_thermal", "x_water"),
        process_registry=registry,
        process_universe=("thermal", "water"),
        model_specs=(
            ModelSpec(C=0.1, degree=1, random_state=0),
            ModelSpec(C=1.0, degree=1, random_state=0),
        ),
        n_splits=4,
        minimum_margin=0.05,
    )

    assert len(fit.admissible_model_labels) >= 1
    status = fit.process_summary.set_index("process")["status"].to_dict()
    assert status["thermal"] == "required_by_evidence_contract"
    assert status["water"] == "refuted_as_necessary"
    prediction = fit.predict_relative_suitability(p.iloc[:10])
    assert prediction.shape == (10,)
    assert np.isfinite(prediction).all()
    assert fit.selection_receipt


def test_outer_answer_check_cannot_leak_into_learner_fit() -> None:
    p, b, pg, bg, registry = _synthetic_tables()
    occurrence_features = p.copy()
    occurrence_features["occurrence_id"] = [f"o{i:03d}" for i in range(len(p))]
    occurrence_features["longitude"] = 130.0 + np.arange(len(p)) * 0.01
    occurrence_features["latitude"] = 30.0 + (np.arange(len(p)) % 20) * 0.02
    split = freeze_occurrence_answer_check_split(
        occurrence_features,
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=9,
    )

    with pytest.raises(RuntimeError, match="leakage"):
        fit_ecological_identification_learner(
            occurrence_features,
            b,
            pg,
            bg,
            predictors=("x_thermal", "x_water"),
            process_registry=registry,
            process_universe=("thermal", "water"),
            model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
            n_splits=4,
            occurrence_split=split,
            occurrence_id_col="occurrence_id",
        )


def test_answer_check_opens_only_after_selection_receipt() -> None:
    p, b, _, _, registry = _synthetic_tables()
    full = p.copy()
    full["occurrence_id"] = [f"o{i:03d}" for i in range(len(p))]
    full["longitude"] = 130.0 + np.arange(len(p)) * 0.01
    full["latitude"] = 30.0 + (np.arange(len(p)) % 20) * 0.02
    split = freeze_occurrence_answer_check_split(
        full,
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=13,
    )
    model_pool = split.model_pool(full)
    pg = np.tile(np.arange(8), len(model_pool) // 8 + 1)[: len(model_pool)]
    bg = np.tile(np.arange(8), len(b) // 8 + 1)[: len(b)]

    fit = fit_ecological_identification_learner(
        model_pool,
        b,
        pg,
        bg,
        predictors=("x_thermal", "x_water"),
        process_registry=registry,
        process_universe=("thermal", "water"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        occurrence_split=split,
        occurrence_id_col="occurrence_id",
    )
    audit = fit.evaluate_answer_check(full, b.iloc[:80].copy(), split)
    assert audit["selection_receipt"] == fit.selection_receipt
    assert audit["n_answer_check_presence"] == len(split.answer_check_ids)
    assert np.isfinite(audit["presence_rank"])
