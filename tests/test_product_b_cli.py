from pathlib import Path

import pytest

from sdmr.product_b_cli import _validate_protocol_choice


def _choice(path: Path, data_spec: str = "buffer300", *, promoted: bool = True) -> None:
    text = (
        "winning_data_specification=" + data_spec + "\n"
        "winning_universe=active_all\n"
        "winning_strategy=predictive\n"
        "winning_universe_sha256=" + "a" * 64 + "\n"
        "winning_predictors=bio1,bio12,vpd\n"
        "occurrence_sha256=" + "b" * 64 + "\n"
        "occurrence_feature_sha256=" + "c" * 64 + "\n"
    )
    if promoted:
        text += (
            "promotion_min_protocol_selection_fraction=0.7\n"
            "promotion_min_runs_selected=6\n"
            "promotion_min_mean_delta_presence_rank=0.01\n"
            "promotion_min_positive_pair_fraction=0.6\n"
            "promotion_min_pairs_per_comparator=20\n"
            "promotion_required_comparators=all,vif\n"
        )
    path.write_text(text, encoding="utf-8")


def test_product_b_promoted_protocol_requires_matching_data_specification(tmp_path: Path):
    choice = tmp_path / "promoted.txt"
    _choice(choice)
    values = _validate_protocol_choice(str(choice), "buffer300")
    assert values["winning_strategy"] == "predictive"
    assert values["promotion_required_comparators"] == "all,vif"
    with pytest.raises(ValueError, match="does not match"):
        _validate_protocol_choice(str(choice), "bbox2")


def test_product_b_rejects_unpromoted_full_choice(tmp_path: Path):
    choice = tmp_path / "unpromoted.txt"
    _choice(choice, promoted=False)
    with pytest.raises(ValueError, match="promoted_product_a_protocol"):
        _validate_protocol_choice(str(choice), "buffer300")


def test_product_b_rejects_strategy_only_choice(tmp_path: Path):
    choice = tmp_path / "method_only.txt"
    choice.write_text("winning_strategy=predictive\n", encoding="utf-8")
    with pytest.raises(ValueError, match="promoted_product_a_protocol"):
        _validate_protocol_choice(str(choice), "buffer300")
