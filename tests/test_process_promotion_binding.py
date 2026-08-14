from pathlib import Path

import pandas as pd
import pytest

from sdmr.process_promotion_cli import _validate_universality_binding


def _protocol(path: Path, run_sha: str = "r" * 64) -> None:
    path.write_text(
        "universality_run_sha256=" + run_sha + "\n"
        "data_specification=buffer300\n"
        "universe=active_all\n"
        "strategy=predictive\n"
        "universe_sha256=" + "u" * 64 + "\n"
        "predictors=bio1,bio12,vpd\n"
        "product_a_promotion_min_protocol_selection_fraction=0.7\n"
        "product_a_promotion_min_runs_selected=6\n"
        "product_a_promotion_min_mean_delta_presence_rank=0.01\n"
        "product_a_promotion_min_positive_pair_fraction=0.6\n"
        "product_a_promotion_min_pairs_per_comparator=20\n"
        "product_a_promotion_required_comparators=all,vif\n",
        encoding="utf-8",
    )


def _frame(run_sha: str = "r" * 64) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "universality_run_sha256": [run_sha],
            "product_a_data_specification": ["buffer300"],
            "product_a_universe": ["active_all"],
            "product_a_strategy": ["predictive"],
            "product_a_universe_sha256": ["u" * 64],
        }
    )


def test_process_promotion_requires_all_tables_from_same_universality_run(tmp_path: Path):
    protocol = tmp_path / "protocol.txt"
    _protocol(protocol)
    values = _validate_universality_binding(
        str(protocol),
        {"stability": _frame(), "comparison": _frame(), "random": _frame()},
    )
    assert values["universality_run_sha256"] == "r" * 64

    with pytest.raises(ValueError, match="provenance mismatch"):
        _validate_universality_binding(
            str(protocol),
            {"stability": _frame(), "comparison": _frame("x" * 64), "random": _frame()},
        )
