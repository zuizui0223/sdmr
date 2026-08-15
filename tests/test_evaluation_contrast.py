from types import SimpleNamespace

import pandas as pd

import sdmr.evaluation_contrast as contrast


def test_freeze_selector_choices_uses_canonical_auc_and_boyce_only():
    rows = []
    for species in ("sp1", "sp2"):
        rows.extend(
            [
                {
                    "species": species,
                    "data_specification": "buffer_300km",
                    "universe": "u_auc",
                    "strategy": "all",
                    "presence_rank": 0.90,
                    "boyce": 0.20,
                    "n_predictors": 4,
                },
                {
                    "species": species,
                    "data_specification": "buffer_300km",
                    "universe": "u_boyce",
                    "strategy": "vif",
                    "presence_rank": 0.75,
                    "boyce": 0.85,
                    "n_predictors": 3,
                },
                {
                    "species": species,
                    "data_specification": "buffer_150km",
                    "universe": "u_boyce",
                    "strategy": "vif",
                    "presence_rank": 0.99,
                    "boyce": 0.99,
                    "n_predictors": 3,
                },
            ]
        )
    choices = contrast.freeze_selector_choices(
        pd.DataFrame(rows),
        canonical_specification="buffer_300km",
        sdmr_universe="u_robust",
        sdmr_strategy="predictive",
    ).set_index("selector")

    assert choices.loc["canonical_m_auc", "universe"] == "u_auc"
    assert choices.loc["canonical_m_auc", "strategy"] == "all"
    assert choices.loc["canonical_m_boyce", "universe"] == "u_boyce"
    assert choices.loc["canonical_m_boyce", "strategy"] == "vif"
    assert choices.loc["sdmr_m_robust", "universe"] == "u_robust"


def test_evaluate_selector_transfer_pairs_identical_unseen_cases(monkeypatch):
    def fake_benchmark(occurrences, background, candidate_predictors, *, species_name, **kwargs):
        universe_marker = candidate_predictors[0]
        base = {"robust_x": 0.80, "auc_x": 0.72, "boyce_x": 0.70}[universe_marker]
        return SimpleNamespace(
            sealed_metrics=pd.DataFrame(
                [
                    {"species": species_name, "strategy": "all", "presence_rank": base, "boyce": base - 0.1, "n_predictors": 1},
                    {"species": species_name, "strategy": "vif", "presence_rank": base - 0.02, "boyce": base, "n_predictors": 1},
                    {"species": species_name, "strategy": "predictive", "presence_rank": base + 0.01, "boyce": base + 0.02, "n_predictors": 1},
                ]
            )
        )

    monkeypatch.setattr(contrast, "benchmark_species_methods", fake_benchmark)
    choices = pd.DataFrame(
        [
            {"selector": "sdmr_m_robust", "universe": "robust", "strategy": "predictive"},
            {"selector": "canonical_m_auc", "universe": "auc", "strategy": "all"},
            {"selector": "canonical_m_boyce", "universe": "boyce", "strategy": "vif"},
        ]
    )
    empty = pd.DataFrame()
    result = contrast.evaluate_selector_transfer(
        {"buffer_150km": (empty, empty), "buffer_300km": (empty, empty)},
        {"robust": ["robust_x"], "auc": ["auc_x"], "boyce": ["boyce_x"]},
        choices,
        ["heldout_sp"],
    )

    assert len(result.transfer_metrics) == 6
    assert set(result.transfer_summary["selector"]) == {
        "sdmr_m_robust",
        "canonical_m_auc",
        "canonical_m_boyce",
    }
    assert len(result.paired_deltas) == 4
    assert (result.paired_deltas["delta_presence_rank"] > 0).all()
