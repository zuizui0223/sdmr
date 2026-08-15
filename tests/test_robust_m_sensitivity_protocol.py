import pandas as pd

from sdmr.robust_protocol import (
    paired_validation_deltas_across_specs,
    summarize_discovery_robust_across_specs,
)
from sdmr.universe import CandidateUniverse


def test_robust_summary_ranks_methods_within_each_species_and_M_case():
    rows = []
    # Absolute score scales differ strongly between M specs, but predictive is
    # consistently the better method inside the matched comparison case.
    for spec, offset in [("M150", 0.35), ("M500", 0.0)]:
        for species, jitter in [("a", 0.01), ("b", -0.01)]:
            rows.extend(
                [
                    {
                        "data_specification": spec,
                        "species": species,
                        "universe": "u",
                        "strategy": "predictive",
                        "presence_rank": 0.60 + offset + jitter,
                        "n_predictors": 2,
                    },
                    {
                        "data_specification": spec,
                        "species": species,
                        "universe": "u",
                        "strategy": "all",
                        "presence_rank": 0.55 + offset + jitter,
                        "n_predictors": 4,
                    },
                ]
            )
    summary = summarize_discovery_robust_across_specs(
        pd.DataFrame(rows),
        {"u": CandidateUniverse("u", ("bio1", "bio12", "bio15", "vpd"))},
    )
    top = summary.iloc[0]
    assert top["strategy"] == "predictive"
    assert top["mean_case_rank_score"] == 1.0
    assert top["spec_win_fraction"] == 1.0
    assert top["n_specs"] == 2


def test_validation_deltas_are_paired_within_same_taxon_and_M_spec():
    metrics = pd.DataFrame(
        {
            "data_specification": ["M150", "M150", "M500", "M500"],
            "species": ["x", "x", "x", "x"],
            "strategy": ["predictive", "all", "predictive", "all"],
            "presence_rank": [0.72, 0.70, 0.58, 0.57],
        }
    )
    paired = paired_validation_deltas_across_specs(metrics, "predictive")
    assert len(paired) == 2
    assert set(paired["data_specification"]) == {"M150", "M500"}
    assert paired["delta_presence_rank"].round(6).tolist() == [0.02, 0.01]
