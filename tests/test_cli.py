from pathlib import Path
import pytest

from sdmr.cli import _read_method_choice


def test_method_choice_requires_explicit_valid_winner(tmp_path: Path):
    good = tmp_path / "method_choice.txt"
    good.write_text("winning_strategy=predictive\nspatial_test_fraction=0.2\n", encoding="utf-8")
    assert _read_method_choice(str(good)) == "predictive"

    bad = tmp_path / "bad.txt"
    bad.write_text("winning_strategy=whatever\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _read_method_choice(str(bad))
