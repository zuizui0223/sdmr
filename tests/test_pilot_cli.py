from argparse import Namespace
from types import SimpleNamespace

import pandas as pd

from sdmr.pilot_cli import _write_method_outputs


def test_pilot_method_outputs_freeze_universe_and_predictors(tmp_path):
    validation = pd.DataFrame({
        "species": ["z"],
        "presence_rank": [0.82],
        "n_predictors": [3],
    })
    result = SimpleNamespace(
        discovery_metrics=pd.DataFrame({"species": ["a"], "presence_rank": [0.8]}),
        discovery_summary=pd.DataFrame({"universe": ["chelsa_bioclim"], "strategy": ["predictive"]}),
        validation_metrics=validation,
        winning_strategy="predictive",
        winning_universe="chelsa_bioclim",
        winning_universe_sha256="abc123",
        winning_predictors=["bio1", "bio12", "gdd5"],
        discovery_species=["a", "b", "c"],
        validation_species=["z"],
    )
    args = Namespace(spatial_test_fraction=0.2, taxon_validation_fraction=0.25)
    _write_method_outputs(result, tmp_path, args=args, predictors=["bio1", "bio12", "gdd5", "vpd"])
    text = (tmp_path / "method_choice.txt").read_text(encoding="utf-8")
    assert "winning_strategy=predictive" in text
    assert "winning_universe=chelsa_bioclim" in text
    assert "winning_universe_sha256=abc123" in text
    assert "winning_predictors=bio1,bio12,gdd5" in text
    summary = pd.read_csv(tmp_path / "method_validation_summary.csv")
    assert summary.loc[0, "universe"] == "chelsa_bioclim"
    assert summary.loc[0, "mean_presence_rank"] == 0.82
