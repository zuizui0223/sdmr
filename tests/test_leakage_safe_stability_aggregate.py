import json
from pathlib import Path

import pandas as pd

from sdmr.stability_aggregate import aggregate_leakage_safe_stability


def test_aggregate_leakage_safe_stability_parts(tmp_path: Path):
    parts = tmp_path / "parts"
    seeds = [11, 22, 33, 44, 55]
    fractions = [0.15, 0.20, 0.30]
    i = 0
    for fraction in fractions:
        for seed in seeds:
            root = parts / f"artifact-{seed}-{fraction}" / "part_result"
            root.mkdir(parents=True)
            (root / "part_metadata.json").write_text(
                json.dumps(
                    {
                        "seed": seed,
                        "sealed_fraction": fraction,
                        "taxon_validation_fraction": 0.25,
                        "M_background_rebuilt_from_model_pool": True,
                    }
                ),
                encoding="utf-8",
            )
            (root / "pilot_grid_specification.json").write_text(
                json.dumps(
                    {
                        "outer_sealed_before_M": True,
                        "focal_thin_cell_size_degrees": 0.05,
                        "m_grid_as_sensitivity": True,
                    }
                ),
                encoding="utf-8",
            )
            strategy = "predictive" if i < 11 else "vif"
            (root / "product_a_protocol_choice.txt").write_text(
                "winning_data_specification=all_predeclared_M_sensitivity_specs\n"
                "winning_universe=active_all\n"
                f"winning_strategy={strategy}\n"
                "winning_universe_sha256=universe-sha\n"
                "winning_predictors=bio1,bio12\n"
                "occurrence_sha256=occurrence-sha\n"
                "occurrence_feature_sha256=feature-sha\n"
                "discovery_species=a,b,c\n"
                "validation_species=d,e\n",
                encoding="utf-8",
            )
            pd.DataFrame(
                {
                    "data_specification": ["all_predeclared_M_sensitivity_specs", "all_predeclared_M_sensitivity_specs"],
                    "universe": ["active_all", "active_all"],
                    "strategy": [strategy, "all"],
                    "mean_case_rank_score": [0.9, 0.7],
                    "spec_win_fraction": [1.0 if i < 12 else 2 / 3, 0.0],
                }
            ).to_csv(root / "protocol_discovery_summary.csv", index=False)
            pd.DataFrame(
                {
                    "data_specification": ["M150", "M150", "M500", "M500"],
                    "species": ["d", "e", "d", "e"],
                    "strategy": [strategy, strategy, strategy, strategy],
                    "presence_rank": [0.7, 0.75, 0.68, 0.73],
                    "n_predictors": [2, 2, 2, 2],
                    "selected_by_discovery": [True, True, True, True],
                }
            ).to_csv(root / "protocol_validation_metrics.csv", index=False)
            pd.DataFrame(
                {
                    "data_specification": ["M150", "M150", "M500", "M500"],
                    "species": ["d", "e", "d", "e"],
                    "winning_strategy": [strategy] * 4,
                    "comparator": ["all"] * 4,
                    "delta_presence_rank": [0.05, 0.05, 0.03, 0.03],
                }
            ).to_csv(root / "protocol_validation_paired_deltas.csv", index=False)
            i += 1

    output = tmp_path / "out"
    aggregate_leakage_safe_stability(parts, output)
    runs = pd.read_csv(output / "protocol_stability_runs.csv")
    choice = pd.read_csv(output / "protocol_choice_stability.csv")
    deltas = pd.read_csv(output / "protocol_validation_delta_summary.csv")
    assert len(runs) == 15
    assert runs[["seed", "sealed_fraction"]].drop_duplicates().shape[0] == 15
    assert runs["winning_data_specification"].nunique() == 1
    top = choice.iloc[0]
    assert top["winning_strategy"] == "predictive"
    assert top["runs_selected"] == 11
    assert top["selection_fraction"] == 11 / 15
    assert top["min_m_spec_win_fraction"] >= 2 / 3
    assert deltas.loc[deltas["comparator"] == "all", "n_pairs"].iloc[0] == 60
