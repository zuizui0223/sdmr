from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.method import MODEL_ROLE, OUTER_BLOCK_COL, OUTER_ROLE_COL, SEALED_ROLE
from sdmr.prepared_benchmark_cli import main


def _write_prepared_bundle(root: Path):
    rng = np.random.default_rng(515)
    species = ["Plant a", "Plant b", "Plant c", "Plant d"]
    occ = []
    backgrounds = {"buffer_150km": [], "buffer_500km": []}
    for i, sp in enumerate(species):
        p_model, p_sealed = 12, 4
        n = p_model + p_sealed
        occ.append(
            pd.DataFrame(
                {
                    "species": sp,
                    "longitude": np.linspace(-2, 2, n) + i * 10,
                    "latitude": np.linspace(-1, 1, n) + i * 2,
                    "bio1": rng.normal(1.2, 0.25, n),
                    "bio2": rng.normal(0, 1, n),
                    OUTER_ROLE_COL: [MODEL_ROLE] * p_model + [SEALED_ROLE] * p_sealed,
                    OUTER_BLOCK_COL: list(np.arange(p_model) % 6) + [6, 6, 7, 7],
                }
            )
        )
        for j, name in enumerate(backgrounds):
            b_model, b_sealed = 24, 8
            m = b_model + b_sealed
            backgrounds[name].append(
                pd.DataFrame(
                    {
                        "species": sp,
                        "longitude": np.linspace(-2.5, 2.5, m) + i * 10 + j * 0.1,
                        "latitude": np.linspace(-1.2, 1.2, m) + i * 2,
                        "bio1": rng.normal(-1.0, 0.3, m),
                        "bio2": rng.normal(0, 1, m),
                        OUTER_ROLE_COL: [MODEL_ROLE] * b_model + [SEALED_ROLE] * b_sealed,
                        OUTER_BLOCK_COL: list(np.arange(b_model) % 6) + [6] * 4 + [7] * 4,
                    }
                )
            )
    pd.concat(occ, ignore_index=True).to_csv(root / "pilot_occurrences.csv", index=False)
    grid = pd.DataFrame(
        [
            {"name":"buffer_150km","m_strategy":"buffer","bbox_buffer_degrees":np.nan,"occurrence_buffer_km":150,"background_points":2000,"background_cell_size_degrees":0.05},
            {"name":"buffer_500km","m_strategy":"buffer","bbox_buffer_degrees":np.nan,"occurrence_buffer_km":500,"background_points":2000,"background_cell_size_degrees":0.05},
        ]
    )
    grid.to_csv(root / "pilot_grid_frozen.csv", index=False)
    for name, parts in backgrounds.items():
        path = root / "specifications" / name
        path.mkdir(parents=True)
        pd.concat(parts, ignore_index=True).to_csv(path / "background.csv", index=False)


def test_prepared_benchmark_reuses_feature_tables_without_raster_access(tmp_path):
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    _write_prepared_bundle(prepared)
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {"predictor":"bio1","source":"CHELSA-bioclim","version":"2.1","candidate_class":"core_climate","process":"temperature","mechanism":"thermal"},
            {"predictor":"bio2","source":"CHELSA-bioclim","version":"2.1","candidate_class":"extended_climate","process":"temperature","mechanism":"seasonality"},
        ]
    ).to_csv(manifest, index=False)
    output = tmp_path / "result"
    rc = main(
        [
            "--prepared-dir", str(prepared),
            "--manifest", str(manifest),
            "--output-dir", str(output),
            "--model-profile", "linear_l2_c1",
            "--taxon-validation-fraction", "0.25",
            "--spatial-test-fraction", "0.20",
            "--max-predictors", "2",
            "--random-baseline-repeats", "0",
            "--seed", "19",
            "--benchmark-jobs", "2",
            "--model-spec-jobs", "1",
        ]
    )
    assert rc == 0
    assert (output / "product_a_protocol_choice.txt").exists()
    assert (output / "protocol_discovery_summary.csv").exists()
    assert (output / "protocol_validation_metrics.csv").exists()
    contract = (output / "prepared_benchmark_contract.json").read_text(encoding="utf-8")
    assert '"changes_prepared_source_evidence": false' in contract
    choice = (output / "product_a_protocol_choice.txt").read_text(encoding="utf-8")
    assert "winning_universe=" in choice
    assert "winning_strategy=" in choice
