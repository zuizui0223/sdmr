import json

import numpy as np
import pandas as pd

from sdmr.ecological_identification_workflow import (
    EcologicalIdentificationConfig,
    prepare_ecological_identification_study,
    quick_fit_ecological_identification,
)
from sdmr.model import ModelSpec


def _tables(seed: int = 12):
    rng = np.random.default_rng(seed)
    n = 160
    occurrence = pd.DataFrame(
        {
            "occurrence_id": [f"o{i:03d}" for i in range(n)],
            "longitude": 130.0 + (np.arange(n) % 20) * 0.12,
            "latitude": 30.0 + (np.arange(n) // 20) * 0.18,
            "x_thermal": rng.normal(2.0, 0.40, n),
            "x_water": rng.normal(0.0, 1.0, n),
        }
    )
    background = pd.DataFrame(
        {
            "longitude": 130.02 + (np.arange(n) % 20) * 0.12,
            "latitude": 30.03 + (np.arange(n) // 20) * 0.18,
            "x_thermal": rng.normal(-2.0, 0.40, n),
            "x_water": rng.normal(0.0, 1.0, n),
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "x_thermal", "process": "thermal", "role": "direct"},
            {"predictor": "x_water", "process": "water", "role": "direct"},
        ]
    )
    config = EcologicalIdentificationConfig(
        answer_check_fraction=0.25,
        outer_random_state=19,
        inner_n_blocks=8,
        inner_n_splits=4,
        inner_random_state=23,
        minimum_margin=0.05,
        model_specs=(
            ModelSpec(C=0.1, degree=1, random_state=0),
            ModelSpec(C=1.0, degree=1, random_state=0),
        ),
    )
    return occurrence, background, registry, config


def test_two_stage_workflow_learns_process_certificate() -> None:
    occurrence, background, registry, config = _tables()
    study = prepare_ecological_identification_study(
        occurrence[["occurrence_id", "longitude", "latitude"]],
        registry,
        config=config,
    )

    assert set(study.model_pool_ids).isdisjoint(set(study.answer_check_ids))
    fit = study.fit(occurrence, background)
    status = fit.process_summary.set_index("process")["status"].to_dict()
    assert status["thermal"] == "required_by_evidence_contract"
    assert status["water"] == "refuted_as_necessary"
    assert len(fit.learner.admissible_model_labels) >= 1
    assert fit.selection_receipt


def test_answer_check_values_cannot_change_the_learned_object() -> None:
    occurrence, background, registry, config = _tables()
    study = prepare_ecological_identification_study(
        occurrence[["occurrence_id", "longitude", "latitude"]],
        registry,
        config=config,
    )
    fit_a = study.fit(occurrence, background)

    altered = occurrence.copy()
    sealed = altered["occurrence_id"].isin(study.answer_check_ids)
    altered.loc[sealed, "x_thermal"] = -9999.0
    altered.loc[sealed, "x_water"] = 9999.0
    fit_b = study.fit(altered, background)

    assert fit_a.selection_receipt == fit_b.selection_receipt
    pd.testing.assert_frame_equal(fit_a.baseline_summary, fit_b.baseline_summary)
    pd.testing.assert_frame_equal(fit_a.process_summary, fit_b.process_summary)

    answer_a = fit_a.evaluate_answer_check(occurrence, background.iloc[:80].copy())
    answer_b = fit_b.evaluate_answer_check(altered, background.iloc[:80].copy())
    assert answer_a["selection_receipt"] == answer_b["selection_receipt"]
    assert answer_a["presence_rank"] != answer_b["presence_rank"]


def test_quick_fit_and_audit_bundle_are_usable(tmp_path) -> None:
    occurrence, background, registry, config = _tables()
    fit = quick_fit_ecological_identification(
        occurrence,
        background,
        registry,
        config=config,
    )

    manifest_path = fit.export_audit_bundle(tmp_path / "audit")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["selection_receipt"] == fit.selection_receipt
    assert manifest["occurrence_split_digest"] == fit.prepared.occurrence_split.split_digest
    assert set(manifest["files_sha256"]) == {
        "occurrence_split.csv",
        "registry_proposal.csv",
        "process_registry.csv",
        "inner_groups.csv",
        "baseline_summary.csv",
        "process_summary.csv",
        "fold_evidence.csv",
    }
    for name in manifest["files_sha256"]:
        assert (tmp_path / "audit" / name).exists()
