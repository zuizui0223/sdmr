import json
from pathlib import Path

import pandas as pd

from sdmr.evaluation_contrast_aggregate import aggregate_selector_contrasts


def _write_part(root: Path, seed: int, fraction: float, auc_delta: float, boyce_delta: float, same_auc: bool):
    part = root / f"part-{seed}-{fraction}"
    part.mkdir(parents=True)
    (part / "part_metadata.json").write_text(
        json.dumps({"seed": seed, "sealed_fraction": fraction}), encoding="utf-8"
    )
    pd.DataFrame(
        [
            {"selector": "sdmr_m_robust", "universe": "u0", "strategy": "predictive", "same_method_as_sdmr": True},
            {"selector": "canonical_m_auc", "universe": "u0" if same_auc else "u1", "strategy": "predictive" if same_auc else "all", "same_method_as_sdmr": same_auc},
            {"selector": "canonical_m_boyce", "universe": "u2", "strategy": "vif", "same_method_as_sdmr": False},
        ]
    ).to_csv(part / "selector_contrast_choices.csv", index=False)
    pd.DataFrame(
        [
            {"selector": "sdmr_m_robust", "mean_presence_rank": 0.8},
            {"selector": "canonical_m_auc", "mean_presence_rank": 0.8 - auc_delta},
            {"selector": "canonical_m_boyce", "mean_presence_rank": 0.8 - boyce_delta},
        ]
    ).to_csv(part / "selector_contrast_transfer_summary.csv", index=False)
    rows = []
    for species in ("a", "b"):
        rows.append({"data_specification": "buffer_300km", "species": species, "reference_selector": "sdmr_m_robust", "comparator": "canonical_m_auc", "delta_presence_rank": auc_delta})
        rows.append({"data_specification": "buffer_300km", "species": species, "reference_selector": "sdmr_m_robust", "comparator": "canonical_m_boyce", "delta_presence_rank": boyce_delta})
    pd.DataFrame(rows).to_csv(part / "selector_contrast_paired_deltas.csv", index=False)


def test_aggregate_selector_contrasts_summarizes_runs_and_pairs(tmp_path):
    _write_part(tmp_path, 11, 0.2, 0.03, 0.02, False)
    _write_part(tmp_path, 22, 0.3, 0.01, -0.01, True)
    tables = aggregate_selector_contrasts(tmp_path)

    comp = tables["selector_contrast_comparator_summary"].set_index("comparator")
    assert comp.loc["canonical_m_auc", "n_runs"] == 2
    assert comp.loc["canonical_m_auc", "n_pairs"] == 4
    assert comp.loc["canonical_m_auc", "mean_delta_presence_rank"] == 0.02
    assert comp.loc["canonical_m_auc", "positive_run_fraction"] == 1.0
    assert comp.loc["canonical_m_boyce", "positive_run_fraction"] == 0.5

    choices = tables["selector_contrast_choice_summary"].set_index("selector")
    assert choices.loc["canonical_m_auc", "same_method_as_sdmr_fraction"] == 0.5
    assert choices.loc["canonical_m_boyce", "same_method_as_sdmr_fraction"] == 0.0
