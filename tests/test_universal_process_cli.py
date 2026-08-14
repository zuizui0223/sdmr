from pathlib import Path

import pandas as pd
import pytest

from sdmr.cli import _candidate_fingerprint
from sdmr.universal_process_cli import _resolve_promoted_predictors


def _promoted_choice(path: Path, predictors: list[str]) -> None:
    path.write_text(
        "winning_data_specification=buffer300\n"
        "winning_universe=active_all\n"
        "winning_strategy=predictive\n"
        f"winning_universe_sha256={_candidate_fingerprint(predictors)}\n"
        "winning_predictors=" + ",".join(predictors) + "\n"
        "promotion_min_protocol_selection_fraction=0.7\n"
        "promotion_min_runs_selected=6\n"
        "promotion_min_mean_delta_presence_rank=0.01\n"
        "promotion_min_positive_pair_fraction=0.6\n"
        "promotion_min_pairs_per_comparator=20\n"
        "promotion_required_comparators=all,vif\n",
        encoding="utf-8",
    )


def test_universal_process_runner_inherits_promoted_predictor_universe(tmp_path: Path):
    choice = tmp_path / "promoted.txt"
    predictors = ["bio1", "bio12", "vpd"]
    _promoted_choice(choice, predictors)
    manifest = pd.DataFrame({"predictor": predictors + ["gdd5"]})
    values, frozen = _resolve_promoted_predictors(str(choice), "buffer300", manifest)
    assert values["winning_strategy"] == "predictive"
    assert frozen == predictors


def test_universal_process_runner_rejects_changed_manifest(tmp_path: Path):
    choice = tmp_path / "promoted.txt"
    predictors = ["bio1", "bio12", "vpd"]
    _promoted_choice(choice, predictors)
    manifest = pd.DataFrame({"predictor": ["bio1", "bio12"]})
    with pytest.raises(ValueError, match="missing from manifest"):
        _resolve_promoted_predictors(str(choice), "buffer300", manifest)
