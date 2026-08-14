from argparse import ArgumentParser, Namespace
from pathlib import Path
import pytest

from sdmr.cli import _candidate_fingerprint, _read_method_choice, _resolve_frozen_choice


def test_method_choice_requires_explicit_valid_winner(tmp_path: Path):
    good = tmp_path / "method_choice.txt"
    good.write_text("winning_strategy=predictive\nspatial_test_fraction=0.2\n", encoding="utf-8")
    assert _read_method_choice(str(good)) == "predictive"

    bad = tmp_path / "bad.txt"
    bad.write_text("winning_strategy=whatever\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _read_method_choice(str(bad))


def test_method_choice_freezes_predictor_universe_and_fingerprint(tmp_path: Path):
    choice = tmp_path / "method_choice.txt"
    predictors = ["bio1", "bio12", "gdd5"]
    choice.write_text(
        "winning_strategy=predictive\n"
        "winning_universe=chelsa_bioclim\n"
        f"winning_universe_sha256={_candidate_fingerprint(predictors)}\n"
        "winning_predictors=bio1,bio12,gdd5\n",
        encoding="utf-8",
    )
    args = Namespace(method_choice=str(choice), strategy=None)
    strategy, frozen, values = _resolve_frozen_choice(
        args,
        ArgumentParser(add_help=False),
        ["bio1", "bio12", "gdd5", "vpd"],
    )
    assert strategy == "predictive"
    assert frozen == predictors
    assert values["winning_universe"] == "chelsa_bioclim"


def test_method_choice_rejects_changed_predictor_fingerprint(tmp_path: Path):
    choice = tmp_path / "method_choice.txt"
    choice.write_text(
        "winning_strategy=vif\n"
        "winning_universe=bioclim19\n"
        "winning_universe_sha256=not-the-real-hash\n"
        "winning_predictors=bio1,bio12\n",
        encoding="utf-8",
    )
    args = Namespace(method_choice=str(choice), strategy=None)
    with pytest.raises(SystemExit):
        _resolve_frozen_choice(
            args,
            ArgumentParser(add_help=False),
            ["bio1", "bio12", "vpd"],
        )


def test_universality_mode_inherits_frozen_strategy_and_writes_outputs(tmp_path, monkeypatch):
    import pandas as pd
    from types import SimpleNamespace
    import sdmr.cli as cli

    occ = tmp_path / "occ.csv"
    bg = tmp_path / "bg.csv"
    manifest = tmp_path / "manifest.csv"
    choice = tmp_path / "method_choice.txt"
    out = tmp_path / "out"
    pd.DataFrame({"species": ["a"], "longitude": [0.0], "latitude": [0.0], "x": [1.0]}).to_csv(occ, index=False)
    pd.DataFrame({"species": ["a"], "longitude": [1.0], "latitude": [1.0], "x": [0.0]}).to_csv(bg, index=False)
    pd.DataFrame({
        "predictor": ["x"], "source": ["synthetic"], "version": ["1"],
        "candidate_class": ["core"], "process": ["signal"], "mechanism": ["x"],
    }).to_csv(manifest, index=False)
    choice.write_text("winning_strategy=predictive\n", encoding="utf-8")

    captured = {}

    def fake_benchmark(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            splits=pd.DataFrame({"process": ["signal"], "seed": [7]}),
            process_stability=pd.DataFrame({"process": ["signal"], "core_stability": [1.0]}),
            validation_comparison=pd.DataFrame({"species": ["z"], "core_presence_rank": [0.8]}),
        )

    monkeypatch.setattr(cli, "benchmark_repeated_process_core_splits", fake_benchmark)
    rc = cli.main([
        "--mode", "universality",
        "--occurrences", str(occ),
        "--background", str(bg),
        "--predictors", str(manifest),
        "--method-choice", str(choice),
        "--universality-repeats", "3",
        "--seed", "7",
        "--output-dir", str(out),
    ])
    assert rc == 0
    assert captured["strategy"] == "predictive"
    assert captured["seeds"] == (7, 1016, 2025)
    assert (out / "universality_process_stability.csv").exists()
    text = (out / "universality_strategy.txt").read_text(encoding="utf-8")
    assert "strategy=predictive" in text
    assert "predictors=x" in text
