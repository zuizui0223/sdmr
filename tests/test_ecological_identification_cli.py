import json

import numpy as np
import pandas as pd

from sdmr.ecological_identification_cli import main
from sdmr.ecological_identification_io import load_prepared_ecological_identification_study


def _write_inputs(tmp_path):
    rng = np.random.default_rng(31)
    n = 96
    occurrence = pd.DataFrame(
        {
            "occurrence_id": [f"o{i:03d}" for i in range(n)],
            "longitude": 132.0 + (np.arange(n) % 12) * 0.15,
            "latitude": 31.0 + (np.arange(n) // 12) * 0.20,
            "x_thermal": rng.normal(2.0, 0.45, n),
            "x_water": rng.normal(0.0, 1.0, n),
        }
    )
    background = pd.DataFrame(
        {
            "longitude": 132.03 + (np.arange(n) % 12) * 0.15,
            "latitude": 31.04 + (np.arange(n) // 12) * 0.20,
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
    occurrence_path = tmp_path / "occurrence.csv"
    background_path = tmp_path / "background.csv"
    registry_path = tmp_path / "registry.csv"
    occurrence.to_csv(occurrence_path, index=False)
    background.to_csv(background_path, index=False)
    registry.to_csv(registry_path, index=False)
    return occurrence_path, background_path, registry_path


def test_prepare_and_fit_cli_roundtrip(tmp_path) -> None:
    occurrence_path, background_path, registry_path = _write_inputs(tmp_path)
    prepared = tmp_path / "prepared"
    code = main(
        [
            "prepare",
            "--occurrences",
            str(occurrence_path),
            "--predictor-metadata",
            str(registry_path),
            "--output-dir",
            str(prepared),
            "--outer-blocks",
            "6",
            "--answer-fraction",
            "0.25",
            "--inner-blocks",
            "6",
            "--inner-splits",
            "3",
            "--minimum-margin",
            "0.05",
        ]
    )
    assert code == 0
    assert (prepared / "study_manifest.json").exists()
    assert (prepared / "model_pool_ids.txt").exists()
    study = load_prepared_ecological_identification_study(prepared)
    assert set(study.model_pool_ids).isdisjoint(set(study.answer_check_ids))

    results = tmp_path / "results"
    code = main(
        [
            "fit",
            "--prepared-dir",
            str(prepared),
            "--occurrence-features",
            str(occurrence_path),
            "--background-features",
            str(background_path),
            "--answer-background",
            str(background_path),
            "--output-dir",
            str(results),
        ]
    )
    assert code == 0
    manifest = json.loads((results / "manifest.json").read_text(encoding="utf-8"))
    answer = json.loads((results / "answer_check.json").read_text(encoding="utf-8"))
    process = pd.read_csv(results / "process_summary.csv").set_index("process")
    assert manifest["selection_receipt"] == answer["selection_receipt"]
    assert process.loc["thermal", "status"] == "required_by_evidence_contract"
    assert process.loc["water", "status"] == "refuted_as_necessary"
