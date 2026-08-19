from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest

from sdmr.cli import _candidate_fingerprint
from sdmr.universal_process_cli import (
    _resolve_promoted_predictors,
    _restrict_manifest_to_promoted_predictors,
    _universality_contract,
    _universality_run_sha256,
)


def _promoted_choice(path: Path, predictors: list[str]) -> None:
    path.write_text(
        "winning_data_specification=buffer300\n"
        "winning_universe=active_all\n"
        "winning_strategy=predictive\n"
        f"winning_universe_sha256={_candidate_fingerprint(predictors)}\n"
        "winning_predictors=" + ",".join(predictors) + "\n"
        "occurrence_sha256=" + "b" * 64 + "\n"
        "occurrence_feature_sha256=" + "c" * 64 + "\n"
        "promotion_min_protocol_selection_fraction=0.7\n"
        "promotion_min_runs_selected=6\n"
        "promotion_min_mean_delta_presence_rank=0.01\n"
        "promotion_min_positive_pair_fraction=0.6\n"
        "promotion_min_pairs_per_comparator=20\n"
        "promotion_required_comparators=all,vif\n",
        encoding="utf-8",
    )


def test_universal_process_runner_inherits_and_physically_restricts_promoted_universe(tmp_path: Path):
    choice = tmp_path / "promoted.txt"
    predictors = ["bio1", "bio12", "vpd"]
    _promoted_choice(choice, predictors)
    manifest = pd.DataFrame(
        {
            "predictor": predictors + ["unpromoted_water_raster"],
            "process": ["temperature", "water", "drought", "water"],
        }
    )
    values, frozen = _resolve_promoted_predictors(str(choice), "buffer300", manifest)
    restricted = _restrict_manifest_to_promoted_predictors(manifest, frozen)
    assert values["winning_strategy"] == "predictive"
    assert frozen == predictors
    assert restricted["predictor"].tolist() == predictors
    assert "unpromoted_water_raster" not in set(restricted["predictor"])


def test_universal_process_runner_rejects_changed_manifest(tmp_path: Path):
    choice = tmp_path / "promoted.txt"
    predictors = ["bio1", "bio12", "vpd"]
    _promoted_choice(choice, predictors)
    manifest = pd.DataFrame({"predictor": ["bio1", "bio12"]})
    with pytest.raises(ValueError, match="missing from manifest"):
        _resolve_promoted_predictors(str(choice), "buffer300", manifest)


def test_universality_run_fingerprint_changes_when_protocol_parameters_change(tmp_path: Path):
    choice_file = tmp_path / "promoted.txt"
    predictors = ["bio1", "bio12"]
    _promoted_choice(choice_file, predictors)
    manifest = pd.DataFrame({"predictor": predictors})
    choice, frozen = _resolve_promoted_predictors(str(choice_file), "buffer300", manifest)
    args = SimpleNamespace(
        spatial_test_fraction=0.2,
        taxon_validation_fraction=0.2,
        min_process_selection_fraction=0.25,
        process_top_k=4,
        random_process_repeats=10,
        vif_threshold=5.0,
        max_predictors=8,
        equivalence_threshold=0.9,
    )
    c1 = _universality_contract(choice, frozen, (11, 22), args)
    h1 = _universality_run_sha256(c1)
    args.process_top_k = 3
    c2 = _universality_contract(choice, frozen, (11, 22), args)
    h2 = _universality_run_sha256(c2)
    assert h1 != h2
